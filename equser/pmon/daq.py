#!/usr/bin/env python3

# Copyright 2024 Energy Quotient (EQ Systems Inc.)
# Originally developed by Renewable Edge LLC

"""Power monitoring data acquisition from EQ Wave sensors.

Requires the ``[daq]`` extra::

    pip install equser[daq]
"""

import signal
import socket

from datetime import timedelta
from multiprocessing import Process
from pathlib import Path
from struct import Struct
from time import sleep, time_ns
from typing import Optional, Any, Dict

try:
    from avro.datafile import DataFileWriter
    from avro.io import DatumWriter
except ImportError:
    _has_avro = False
else:
    _has_avro = True

from equser.core.paths import PATHS
from equser.core.config import load_config, get_sensor_address
from equser.core.system import format_oserror
from equser.pmon.dataops import convert_avro_to_parquet
from equser.pmon.schema import create_schema
from equser.pmon.errors import ConfigurationError, ConnectionError
from equser.utils.datetime import DateTime
from equser.utils.logging import get_logger

logger = get_logger(__name__)

MAX_READ_ATTEMPTS = 3  # Data packets can be fragmented across this many reads


def _check_avro():
    """Raise ImportError with helpful message if avro is not installed."""
    if not _has_avro:
        raise ImportError(
            "Live data acquisition requires the [daq] extra.\n"
            "Install with: pip install equser[daq]"
        )


class PowerMonitor(object):
    """Client for retrieving and saving data from the EQ Wave's power monitor.

    This class handles:
    - TCP connection management with retry logic
    - Real-time data acquisition
    - Data buffering and file management
    - Automatic file rotation
    - Avro to Parquet conversion

    Initialization args:
        ip_address: IP address of the sensor
        connection: Connection settings dictionary with:
            - port: Port number for the sensor's power monitor server (default: 1535)
            - retry_delay: Time in seconds between retries (default: 3)
            - num_retries: Number of connection retries, -1 for infinite (default: -1)
            - connect_timeout: Connection timeout in seconds (default: 5)
            - data_timeout: Data reception timeout in seconds (default: 0.6)
        parquet: Parquet file settings dictionary with:
            - dest: Directory for saving files (default: "/mnt/eqdata/pmon")
            - interval: Interval for new files in seconds (default: 86400)
            - flush_every: Number of rows before buffer flush (default: -1 meaning disabled)
            - compression: Dict with method and level (default: {"method": "ZSTD", "level": 4})
        data_dir: Optional override for data directory
        convert_files_on_startup: Whether to convert existing Avro files on startup (default: True)

    Raises:
        ConfigurationError: If configuration parameters are invalid
        ConnectionError: If connection to sensor fails
        ImportError: If avro package is not installed (install equser[daq])
        OSError: If file system operations fail
    """

    # TODO: To properly support flush, we need to do the writing in another thread.
    # Otherwise any disk/network delay will cause a delay in retrieving data from
    # the socket, and thus a risk of data buffer overrun, affecting both pmon and wave.

    def __init__(self, ip_address: str,
                 connection: Dict[str, int] = dict(
                     port=1535,
                     retry_delay=3,
                     num_retries=-1,
                     connect_timeout=5,
                     data_timeout=0.6),
                 parquet: Dict[str, Any] = dict(
                     interval=86400,
                     flush_every=-1,
                     compression=dict(method='ZSTD', level=4)
                 ),
                 data_dir: Optional[Path] = None,
                 convert_files_on_startup: bool = True) -> None:
        _check_avro()

        # Use provided data directory or fall back to PATHS
        self.dest = Path(data_dir) if data_dir else PATHS.pmon_data
        if not self.dest.exists():
            logger.info(f"Creating folder for power monitor data at {self.dest.absolute()}")
            self.dest.mkdir(parents=True, exist_ok=True)

        self.file_conversion_kwargs = dict(compression=parquet['compression']['method'],
                                           compression_level=parquet['compression']['level'],
                                           remove=True)

        # Convert any existing Avro files
        if convert_files_on_startup:
            avro_files = list(self.dest.glob("*.avro"))
            if avro_files:
                logger.info(f"Converting {len(avro_files)} existing Avro files to Parquet")
                for avro_file in avro_files:
                    try:
                        Process(
                            name=f"pmon convert {avro_file.name}",
                            target=convert_avro_to_parquet,
                            args=(avro_file,),
                            kwargs=self.file_conversion_kwargs
                        ).start()
                    except Exception as e:
                        logger.warning(f"Failed to convert {avro_file}: {e}")

        # Rest of initialization
        self.ip_address = ip_address
        self.port = connection['port']
        self.retry_delay = connection['retry_delay']
        self.num_retries = connection['num_retries']
        self.connect_timeout = connection['connect_timeout']
        self.data_timeout = connection['data_timeout']
        self.interval = timedelta(seconds=parquet['interval'])
        self.flush_every = parquet['flush_every']
        self.sock = None
        self.writer = None
        self.file_path = None

        signal.signal(signal.SIGTERM, self._sigterm_handler)
        signal.signal(signal.SIGINT, self._sigint_handler)

    def run(self) -> None:
        """Run the power monitor data acquisition process.

        This method:
        1. Establishes TCP connection with retry logic
        2. Sends start command to the sensor
        3. Receives configuration and creates schema
        4. Continuously receives and processes data
        5. Saves data to Avro files and converts to Parquet
        """

        # Create a TCP/IP socket and connect to the EQ Wave's power monitor.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Reuse the socket like the sensor does
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
        self.sock.settimeout(self.connect_timeout)
        logger.info(f"Connecting to power monitor at {self.ip_address} port {self.port}...")

        # Initialize tracking variables
        last_error_type = None
        last_errno = None
        retry_count = 0

        while True:  # Loop until we connect or hit retry limit
            try:
                self.sock.connect((self.ip_address, self.port))
                if retry_count == 0:
                    logger.info("Connected on first try")
                else:
                    logger.info(f"Connected after {retry_count + 1} tries")
                break
            except OSError as e:
                if self.num_retries != -1 and retry_count >= self.num_retries:
                    raise ConnectionError(f"Could not connect after {retry_count + 1} tries; got {format_oserror(e)}")

                # Only log if error type or number changes
                current_error_type = type(e).__name__
                current_errno = getattr(e, 'errno', None)

                if current_error_type != last_error_type or current_errno != last_errno:
                    logger.warning(f"Connection attempt {retry_count + 1} failed: {format_oserror(e)} (future warnings of same type will be silenced)")
                    last_error_type = current_error_type
                    last_errno = current_errno

                retry_count += 1
                # Add longer delay after timeout to allow socket cleanup on sensor
                if isinstance(e, TimeoutError):
                    sleep(self.retry_delay * 3)  # Triple delay for timeouts
                else:
                    sleep(self.retry_delay)

        # After successful connection, set shorter timeout for data acquisition
        self.sock.settimeout(self.data_timeout)

        # Send the start command.
        logger.info("Sending start command")
        sleep(0.1)
        try:
            self.sock.sendall(b'\x01')
        except OSError as e:
            logger.error(f"Error while sending start command: {format_oserror(e)}")
            raise

        # Start the file timer.
        start_time = DateTime.now()
        next_time = start_time // self.interval + self.interval
        self.file_path = self.dest / start_time.strftime("%Y%m%d_%H%M.avro")

        # Receive the configuration/status word and prepare for the data.
        try:
            rxbuf = self.sock.recv(4) # 4 bytes for config word
        except OSError as e:
            logger.error(f"Error receiving the configuration word: {format_oserror(e)}")
            raise
        num_bytes = len(rxbuf)
        if num_bytes != 4:
            logger.error(f"Expected configuration word of 4 bytes, got {num_bytes}")
            raise ConnectionError()
        num_phases = Struct('<I').unpack(rxbuf)[0]
        schema, time_name, var_names = create_schema(num_phases)
        self.writer = DataFileWriter(open(self.file_path, "wb"), DatumWriter(), schema)
        row_size = (num_phases*7 + 3)*4  # + 3 for config/status word, FREQ, and IRMS
        data_buffer = bytearray(row_size)
        unpack = Struct('<%uf' % (num_phases*7 + 2)).unpack # + 2 for FREQ and INRMS (we'll drop subsequent config/status words)
        data_dict = dict.fromkeys(var_names)

        # Receive the rest of the first packet of data.
        logger.info(f"Receiving data")
        try:
            view = memoryview(data_buffer)[4:]
            received = self.sock.recv_into(view)
            remaining = row_size - received - 4
            if remaining > 0:
                attempts = 0
                while remaining and attempts < MAX_READ_ATTEMPTS:
                    view = view[received:]
                    received = self.sock.recv_into(view)
                    if not received:
                        logger.error("Connection closed by remote host")
                        raise ConnectionError()
                    remaining -= received
                    attempts += 1
                if remaining:
                    logger.error(f"Incomplete data after {MAX_READ_ATTEMPTS} attempts")
                    raise ConnectionError()

            # Update time index and values in data dictionary
            data_dict[time_name] = time_ns() // 1000
            values = list(unpack(data_buffer[4:]))  # Drop the config/status word
            for i, key in enumerate(var_names):
                data_dict[key] = values[i]

            self.writer.append(data_dict)

            counts_until_flush = self.flush_every

        except OSError as e:
            logger.error(f"Error while receiving first packet of data: {format_oserror(e)}")
            raise

        while True:  # Continuous operation across file intervals
            while DateTime.now() < next_time:
                try:
                    received = self.sock.recv_into(data_buffer)
                    remaining = row_size - received
                    if remaining > 0:
                        view = memoryview(data_buffer)[received:]
                        attempts = 0
                        while remaining and attempts < MAX_READ_ATTEMPTS:
                            received = self.sock.recv_into(view)
                            if not received:
                                logger.error("Connection closed by remote host")
                                raise ConnectionError()
                            view = view[received:]
                            remaining -= received
                            attempts += 1
                        if remaining:
                            logger.error(f"Incomplete data after {MAX_READ_ATTEMPTS} attempts")
                            raise ConnectionError()

                    # Update time index and values in data dictionary
                    data_dict[time_name] = time_ns() // 1000
                    values = list(unpack(data_buffer[4:]))  # Drop the config/status word
                    for i, key in enumerate(var_names):
                        data_dict[key] = values[i]

                    self.writer.append(data_dict)
                    if counts_until_flush == 1:
                        self.writer.flush()
                        counts_until_flush = self.flush_every
                    else:
                        counts_until_flush -= 1

                except OSError as e:
                    logger.error(f"Data reception error: {format_oserror(e)}")
                    raise

            # Close the file and convert to Parquet if writing files
            try:
                self.writer.close()
                Process(name="pmon convert",
                        target=convert_avro_to_parquet,
                        args=(self.file_path,),
                        kwargs=self.file_conversion_kwargs).start()

                # Prepare the next data file
                self.file_path = self.dest / next_time.strftime("%Y%m%d_%H%M.avro")
                self.writer = DataFileWriter(open(self.file_path, "wb"),
                                             DatumWriter(), schema)
            except Exception as e:
                logger.error(f"Error during file rotation: {e}")
                raise  # Let the main loop handle cleanup and retry

            next_time += self.interval

    def close(self) -> None:
        """Clean up resources and close connections.

        This method:
        1. Closes the TCP socket connection
        2. Closes any open data files
        3. Converts final Avro file to Parquet if needed
        """
        if self.sock:
            self.sock.close()
        if self.writer:
            self.writer.close()
        if self.file_path:
            convert_avro_to_parquet(self.file_path, **self.file_conversion_kwargs)

    def __enter__(self) -> 'PowerMonitor':
        """Context manager entry method.

        Returns:
            PowerMonitor: The PowerMonitor instance
        """
        return self

    def __exit__(self, exc_type: Optional[type],
                 exc_val: Optional[Exception],
                 traceback: Optional[Any]) -> None:
        """Context manager exit method.

        Args:
            exc_type: Type of the exception that occurred, if any
            exc_val: Value of the exception that occurred, if any
            traceback: Traceback of the exception that occurred, if any
        """
        self.close()

    def _sigterm_handler(self, signum: int, frame: Any) -> None:
        """Handle SIGTERM signal.

        Args:
            signum (int): Signal number
            frame: Current stack frame

        Raises:
            SystemExit: Always raised to initiate graceful shutdown
        """
        logger.info("Stopped by the system (via SIGTERM signal)")
        raise(SystemExit)

    def _sigint_handler(self, signum: int, frame: Any) -> None:
        """Handle SIGINT (Ctrl+C) signal.

        Args:
            signum (int): Signal number
            frame: Current stack frame

        Raises:
            KeyboardInterrupt: Always raised to initiate graceful shutdown
        """
        logger.info("Stopped by the user (via keyboard interrupt)")
        raise(KeyboardInterrupt)

    def _cleanup_on_error(self) -> None:
        """Cleanup resources when an error occurs.

        This method:
        1. Closes socket connection if open
        2. Properly closes any open file writers
        3. Converts partial Avro file to Parquet if needed
        """
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.warning(f"Error closing socket: {e}")
            self.sock = None

        if self.writer:
            try:
                self.writer.close()
                if self.file_path and self.file_path.exists():
                    convert_avro_to_parquet(self.file_path, **self.file_conversion_kwargs)
            except Exception as e:
                logger.warning(f"Error cleaning up files: {e}")
            self.writer = None
            self.file_path = None


def acquire(config_path: Optional[str] = None) -> None:
    """Acquire power quality data from the DAQ.

    Args:
        config_path: Optional path to configuration file. If not provided,
                     uses default config resolution (env var, XDG paths, etc.)
    """
    _check_avro()

    # Uncomment for gateway deployment (sets process name in ps/top):
    # import ctypes
    # try:
    #     libc = ctypes.CDLL(None)
    #     libc.prctl(15, b"pmon acquire", 0, 0, 0)
    # except (OSError, AttributeError):
    #     pass

    config = load_config(config_path)
    ip_address = get_sensor_address(config)

    # Connect to the power monitor and save data.
    with PowerMonitor(ip_address, **config.get('pmon', {})) as sensor:
        while True:
            try:
                sensor.run()
            except (ConnectionError, OSError):
                sensor._cleanup_on_error()
                logger.info("Waiting before retry...")
                sleep(sensor.retry_delay)
            except ConfigurationError as e:
                sensor._cleanup_on_error()
                logger.error(f"Configuration error: {e}")
                break
            except (SystemExit, KeyboardInterrupt):
                logger.info("Shutting down gracefully")
                break
            except Exception as exc:
                sensor._cleanup_on_error()
                logger.exception(f"Unexpected error: {type(exc).__name__}: {exc}")
                break
