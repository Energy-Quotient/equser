#!/usr/bin/env python3

# Copyright 2024 Energy Quotient (EQ Systems Inc.)
# Originally developed by Renewable Edge LLC

"""Data operations for power monitoring data - Avro to Parquet conversion.

The ``convert`` CLI function requires the ``[daq]`` extra::

    pip install equser[daq]
"""

import os
import logging

from collections import defaultdict
from glob import glob
from pathlib import Path
from typing import Dict, List, Optional, Union

try:
    import fastavro
except ImportError:
    fastavro = None

import pyarrow as pa

from pyarrow.parquet import write_table

from equser.core.config import load_config
from equser.utils.logging import get_logger

logger = get_logger(__name__)

FIELD_DESCRIPTIONS: Dict[str, str] = {
    "time_us": "Epoch time [us]",
    "FREQ":    "Frequency [Hz]",
    "AVRMS":   "Line A RMS voltage [V]",
    "BVRMS":   "Line B RMS voltage [V]",
    "CVRMS":   "Line C RMS voltage [V]",
    "AIRMS":   "Line A RMS current [A]",
    "BIRMS":   "Line B RMS current [A]",
    "CIRMS":   "Line C RMS current [A]",
    "NIRMS":   "Neutral RMS current [A]",
    "AWATT":   "Line A active power [W]",
    "BWATT":   "Line B active power [W]",
    "CWATT":   "Line C active power [W]",
    "AFVRMS":  "Line A fundamental RMS voltage [V]",
    "BFVRMS":  "Line B fundamental RMS voltage [V]",
    "CFVRMS":  "Line C fundamental RMS voltage [V]",
    "AFIRMS":  "Line A fundamental RMS current [A]",
    "BFIRMS":  "Line B fundamental RMS current [A]",
    "CFIRMS":  "Line C fundamental RMS current [A]",
    "AFWATT":  "Line A fundamental active power [W]",
    "BFWATT":  "Line B fundamental active power [W]",
    "CFWATT":  "Line C fundamental active power [W]",
    "AFVAR":   "Line A fundamental reactive power [var]",
    "BFVAR":   "Line B fundamental reactive power [var]",
    "CFVAR":   "Line C fundamental reactive power [var]",
}

COLUMN_ENCODING = {field:
                   'DELTA_BINARY_PACKED' if field == "time_us" else
                   'BYTE_STREAM_SPLIT' for field in FIELD_DESCRIPTIONS.keys()}


def convert_avro_to_parquet(
    avro_path: Union[str, Path],
    compression: str = 'ZSTD',
    compression_level: int = 4,
    remove: bool = False
) -> Optional[Path]:
    """Convert Avro file to Parquet format.

    Handles:
    - Schema conversion from Avro to Arrow
    - Data type mapping
    - Compression configuration
    - Optional source file cleanup
    - Graceful handling of corrupted files

    Requires the ``[daq]`` extra (fastavro).

    Args:
        avro_path: Path to the Avro file
        compression: Name of the compression algorithm to use (default: 'ZSTD')
        compression_level: Compression level (default: 4)
        remove: If True, remove the Avro file after conversion (default: False)

    Returns:
        Path to the created Parquet file, or None if conversion failed

    Raises:
        ImportError: If fastavro is not installed
        FileNotFoundError: If source file doesn't exist
        ValueError: If compression method is invalid
        OSError: If file operations fail
    """
    if fastavro is None:
        raise ImportError(
            "Avro to Parquet conversion requires the [daq] extra.\n"
            "Install with: pip install equser[daq]"
        )

    avro_path = Path(avro_path)

    # Check if file exists and has content
    if not avro_path.exists():
        logger.error(f"File not found: {avro_path}")
        return None

    file_size = avro_path.stat().st_size
    if file_size == 0:
        logger.warning(f"Empty file found, skipping: {avro_path}")
        return None

    # Read the Avro file into a dictionary of lists, where each list is a
    # column of data.
    data = defaultdict(list)
    try:
        with open(avro_path, "rb") as f:
            try:
                reader = fastavro.reader(f)
                for row in reader:
                    for field, value in row.items():
                        data[field].append(value)
            except (EOFError, ValueError) as e:
                logger.warning(f"Corrupted AVRO file {avro_path}: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error reading {avro_path}: {str(e)}")
                return None
    except OSError as e:
        logger.error(f"Failed to open {avro_path}: {str(e)}")
        return None

    # Check if we got any data
    if not data:
        logger.warning(f"No data found in {avro_path}")
        return None

    try:
        # Replace the lists in the dictionary with pyarrow arrays of the correct
        # datatype. Also generate the Parquet metadata.
        metadata = {}
        for field, column in data.items():
            data[field] = pa.array(column,
                                type=pa.uint64() if field=="time_us" else pa.float32())
            metadata[field] = FIELD_DESCRIPTIONS.get(field, field)

        # Create the Parquet file.
        table = pa.Table.from_pydict(data, metadata=metadata)
        parquet_path = avro_path.with_suffix('.parquet')
        write_table(table, parquet_path,
                    use_dictionary=False, column_encoding=COLUMN_ENCODING,
                    compression=compression, compression_level=compression_level,
                    write_page_index=True)

        # Only remove the source file if conversion was successful and remove flag is True
        if remove:
            try:
                os.remove(avro_path)
                logger.debug(f"Removed source file: {avro_path}")
            except OSError as e:
                logger.error(f"Failed to remove source file {avro_path}: {str(e)}")

        return parquet_path

    except Exception as e:
        logger.error(f"Failed to convert {avro_path} to Parquet: {str(e)}")
        # If Parquet file was partially created, try to remove it
        parquet_path = avro_path.with_suffix('.parquet')
        if parquet_path.exists():
            try:
                os.remove(parquet_path)
            except OSError:
                pass
        return None


def convert(
    file_paths: List[str],
    remove: bool = False,
    config_path: Optional[str] = None
) -> None:
    """Convert Avro file(s) to Parquet format.

    Requires the ``[daq]`` extra (fastavro).

    Args:
        file_paths: List of paths to Avro files (glob patterns accepted)
        remove: If True, remove the Avro files after conversion
        config_path: Optional path to configuration file for compression settings
    """
    if fastavro is None:
        raise ImportError(
            "Avro to Parquet conversion requires the [daq] extra.\n"
            "Install with: pip install equser[daq]"
        )

    # Load configuration for compression settings
    config = load_config(config_path)
    pmon_config = config.get('pmon', {})
    parquet_config = pmon_config.get('parquet', {})
    compression_config = parquet_config.get('compression', {})
    compression_method = compression_config.get('method', 'ZSTD')
    compression_level = compression_config.get('level', 4)

    # Convert the file(s)
    for file_path in file_paths:
        for fpath in glob(file_path):
            print(f"Converting {fpath}...")
            convert_avro_to_parquet(
                fpath,
                compression=compression_method,
                compression_level=compression_level,
                remove=remove
            )
