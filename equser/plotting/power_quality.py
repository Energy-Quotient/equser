"""
Power Quality and Waveform Plotting

Matplotlib-based plotting functions for power quality monitoring data and waveform visualization.
For use in JupyterLab and custom analysis scripts.

Requires the ``[analysis]`` extra (matplotlib, numpy).
"""

import logging
from pathlib import Path

import matplotlib.dates as mdate
import matplotlib.pyplot as plt
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from equser.data.cpow import NEUTRAL_CT_RATIO

logger = logging.getLogger(__name__)

# Figure dimensions
FIGURE_WIDTH = 800
FIGURE_HEIGHT = 380

# Color schemes for power monitoring channels
COLOR_SCHEMES = {
    'AVRMS': '#000000',  # Black
    'BVRMS': '#FF0000',  # Red
    'CVRMS': '#0000FF',  # Blue
    'AIRMS': '#000000',
    'BIRMS': '#FF0000',
    'CIRMS': '#0000FF',
    'AWATT': '#000000',
    'BWATT': '#FF0000',
    'CWATT': '#0000FF',
    'AFVRMS': '#999999',  # Light gray
    'BFVRMS': '#FFB6B6',  # Light red
    'CFVRMS': '#B6B6FF',  # Light blue
    'AFIRMS': '#999999',
    'BFIRMS': '#FFB6B6',
    'CFIRMS': '#B6B6FF',
    'NIRMS': '#CCCCCC',  # Very light gray
    'AFWATT': '#999999',
    'BFWATT': '#FFB6B6',
    'CFWATT': '#B6B6FF',
    'AFVAR': '#CCCCCC',
    'BFVAR': '#FFD6D6',  # Very light red
    'CFVAR': '#D6D6FF',  # Very light blue
    'FREQ': '#000000',  # Frequency - special color
    # Waveform colors
    'VA': '#000000',
    'VB': '#FF0000',
    'VC': '#0000FF',
    'IA': '#000000',
    'IB': '#FF0000',
    'IC': '#0000FF',
    'IN': '#999999',
}

# Channel groupings for power monitoring
VOLTAGE_CHANNELS = ['AVRMS', 'BVRMS', 'CVRMS', 'AFVRMS', 'BFVRMS', 'CFVRMS']

CURRENT_CHANNELS = ['AIRMS', 'BIRMS', 'CIRMS', 'NIRMS', 'AFIRMS', 'BFIRMS', 'CFIRMS']

POWER_CHANNELS = [
    'AWATT',
    'BWATT',
    'CWATT',
    'AFWATT',
    'BFWATT',
    'CFWATT',
    'AFVAR',
    'BFVAR',
    'CFVAR',
]

FREQ_CHANNELS = ['FREQ']

DEFAULT_VISIBLE_CHANNELS = {
    'AVRMS',
    'BVRMS',
    'CVRMS',
    'AIRMS',
    'BIRMS',
    'CIRMS',
    'AWATT',
    'BWATT',
    'CWATT',
    'AFVAR',
    'BFVAR',
    'CFVAR',
    'FREQ',
}

# Waveform channel groupings
WAVEFORM_VOLTAGE_CHANNELS = ['VA', 'VB', 'VC']
WAVEFORM_CURRENT_CHANNELS = ['IA', 'IB', 'IC', 'IN']


class PowerMonitorPlotter:
    """Generates static matplotlib plots from power monitoring data"""

    def __init__(
        self,
        visible_channels: set[str] = DEFAULT_VISIBLE_CHANNELS,
        output_dir: Path | None = None,
    ):
        """
        Initialize power monitor plotter.

        Args:
            visible_channels: Set of channel names to plot
            output_dir: Optional directory for output plots (default: same as input file)
        """
        self.visible_channels = visible_channels
        self.output_dir = output_dir

    def plot_file(self, file_path: str) -> bool:
        """
        Generate static plots from a parquet file.

        Args:
            file_path: Path to the parquet file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Generating static plots for {file_path}")

            # Map visible channels to plot flags
            plot_voltage = any(ch in self.visible_channels for ch in VOLTAGE_CHANNELS)
            plot_current = any(ch in self.visible_channels for ch in CURRENT_CHANNELS)
            plot_power = any(ch in self.visible_channels for ch in POWER_CHANNELS)
            plot_frequency = any(ch in self.visible_channels for ch in FREQ_CHANNELS)

            # Call the internal plotting function
            self._plot_data_static(
                file_path=str(file_path),
                plot_voltage=plot_voltage,
                plot_current=plot_current,
                plot_power=plot_power,
                plot_frequency=plot_frequency,
            )

            return True

        except Exception:
            logger.exception(f"Error generating plots for {file_path}")
            return False

    def _plot_data_static(
        self,
        file_path: str,
        plot_frequency: bool = True,
        plot_voltage: bool = True,
        plot_current: bool = True,
        plot_power: bool = True,
    ) -> None:
        """
        Create static visualization plots from power monitoring data.

        Args:
            file_path: Path to parquet file
            plot_frequency: Generate frequency plot
            plot_voltage: Generate voltage plot
            plot_current: Generate current plot
            plot_power: Generate power plot
        """
        logger.info(f"Creating plots for {file_path}")

        # Read table
        table = pq.read_table(file_path)

        # Set output base path once
        if self.output_dir:
            file_base = str(self.output_dir / Path(file_path).stem)
        else:
            file_base = file_path.rsplit('.', maxsplit=1)[0]

        # Handle datetime conversion
        time = np.array(table['time_us'])
        time = np.array(time / 1000000, dtype='datetime64[s]')

        date_fmt = '%Y-%m-%d %H:%M'
        date_formatter = mdate.DateFormatter(date_fmt)

        # Only create plots that are enabled
        try:
            if plot_frequency and 'FREQ' in table.column_names:
                # Frequency
                fig, ax = plt.subplots()
                ax.set_title("Frequency")
                ax.set_ylabel("Frequency [Hz]")
                ax.plot(time, table['FREQ'], color=COLOR_SCHEMES['FREQ'])
                ax.xaxis.set_major_formatter(date_formatter)
                fig.autofmt_xdate()
                fig.savefig(file_base + "_frequency.svg")
                plt.close(fig)

            if plot_voltage:
                # Voltage
                fig, ax = plt.subplots()
                ax.set_title("Voltage")
                ax.set_ylabel("RMS voltage [V]")
                for x in ['AVRMS', 'BVRMS', 'CVRMS', 'AFVRMS', 'BFVRMS', 'CFVRMS']:
                    if x in table.column_names:
                        ax.plot(time, table[x], label=x, color=COLOR_SCHEMES.get(x))
                ax.xaxis.set_major_formatter(date_formatter)
                fig.autofmt_xdate()
                ax.legend(loc='best', ncol=2)
                fig.savefig(file_base + "_voltage.svg")
                plt.close(fig)

            if plot_current:
                # Current
                fig, ax = plt.subplots()
                ax.set_title("Current")
                ax.set_ylabel("RMS current [A]")
                for x in ['AIRMS', 'BIRMS', 'CIRMS', 'NIRMS', 'AFIRMS', 'BFIRMS', 'CFIRMS']:
                    if x in table.column_names:
                        ax.plot(time, table[x], label=x, color=COLOR_SCHEMES.get(x))
                ax.xaxis.set_major_formatter(date_formatter)
                fig.autofmt_xdate()
                ax.legend(loc='best', ncol=2)
                fig.savefig(file_base + "_current.svg")
                plt.close(fig)

            if plot_power:
                # Power
                fig, ax = plt.subplots()
                ax.set_title("Power")
                ax.set_ylabel("Active power [W]")
                for x in ['AWATT', 'BWATT', 'CWATT', 'AFWATT', 'BFWATT', 'CFWATT']:
                    if x in table.column_names:
                        ax.plot(time, table[x], label=x, color=COLOR_SCHEMES.get(x))
                ax2 = ax.twinx()
                ax2.set_ylabel("Reactive power [var]")
                for x in ['AFVAR', 'BFVAR', 'CFVAR']:
                    if x in table.column_names:
                        ax2.plot(time, table[x], label=x, color=COLOR_SCHEMES.get(x))
                ax.xaxis.set_major_formatter(date_formatter)
                fig.autofmt_xdate()
                ax.legend(loc='center left', ncol=2)
                ax2.legend(loc='center right')
                plt.subplots_adjust(right=0.88)
                fig.savefig(file_base + "_power.svg")
                plt.close(fig)

        except Exception as e:
            logger.error(f"Error: Matplotlib plotting failed: {e}")
            raise RuntimeError(f"Plotting failed: {e}") from e


class WaveformPlotter:
    """Generates static matplotlib plots from waveform data"""

    SAMPLE_RATE = 32_000
    SAMPLES_PER_CYCLE = 533  # ~32000 Hz / 60 Hz

    def __init__(self, output_dir: Path | None = None):
        """
        Initialize waveform plotter.

        Args:
            output_dir: Optional directory for output plots (default: same as input file)
        """
        self.output_dir = output_dir

    def plot_file(self, file_path: str, start_sec: float = 0.0, duration_ms: float = 100.0) -> bool:
        """
        Generate static waveform plots from a parquet file.

        Args:
            file_path: Path to the parquet file
            start_sec: Start time in seconds
            duration_ms: Duration in milliseconds

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Generating static waveform plots for {file_path}")

            # Call the internal plotting function
            self._plot_waveform_static(
                file_path=str(file_path),
                start_sec=start_sec,
                duration_ms=duration_ms,
                plot_waveform=True,
            )

            return True

        except Exception:
            logger.exception(f"Error generating waveform plots for {file_path}")
            return False

    def _plot_waveform_static(
        self,
        file_path: str,
        start_sec: float = 0.0,
        duration_ms: float = 100.0,
        plot_waveform: bool = True,
    ) -> None:
        """
        Create static waveform plots from parquet data.

        Args:
            file_path: Path to parquet file
            start_sec: Start time in seconds
            duration_ms: Duration to plot in milliseconds
            plot_waveform: Whether to generate waveform plot
        """
        logger.info(f"Creating waveform plots for {file_path}")

        # Read the parquet file
        table = pq.read_table(file_path)

        # Get metadata for scaling
        parquet_file = pq.ParquetFile(file_path)
        file_metadata = parquet_file.metadata
        user_metadata = file_metadata.metadata

        # Check if we need scaling (i.e., if data is I32)
        is_i32 = pa.types.is_integer(table['VA'].type)

        # Only parse scaling factors if we're dealing with I32 data
        if is_i32 and user_metadata:
            vscale_raw = user_metadata.get(b'vscale')
            iscale_raw = user_metadata.get(b'iscale')
            vscale = float(vscale_raw.decode()) if vscale_raw else 1.0
            iscale = float(iscale_raw.decode()) if iscale_raw else 1.0
        else:
            vscale = 1.0
            iscale = 1.0

        # Helper functions to apply scaling if needed
        if is_i32:
            scale_voltage = lambda data: data.to_numpy() * vscale
            scale_current = lambda data: data.to_numpy() * iscale
            scale_neutral_current = lambda data: data.to_numpy() * (iscale / NEUTRAL_CT_RATIO)
        else:
            scale_voltage = lambda data: data.to_numpy()
            scale_current = lambda data: data.to_numpy()
            scale_neutral_current = lambda data: data.to_numpy()

        # Calculate sample slice
        start_sample = int(start_sec * self.SAMPLE_RATE)
        num_samples = int(duration_ms * self.SAMPLE_RATE / 1000)
        SLICE = slice(start_sample, start_sample + num_samples)

        # Set output base path
        if self.output_dir:
            file_base = str(self.output_dir / Path(file_path).stem)
        else:
            file_base = file_path.rsplit('.', maxsplit=1)[0]

        try:
            if plot_waveform:
                fig, (ax1, ax2) = plt.subplots(2)
                fig.subplots_adjust(left=0.15, right=0.95, top=0.83)
                rate_khz = self.SAMPLE_RATE / 1000
                fig.suptitle(
                    f"AC Waveforms @ {rate_khz:.0f} kHz (~{self.SAMPLES_PER_CYCLE:.1f} pts/cycle)"
                )

                # Voltage subplot
                ax1.set_title("Voltage")
                ax1.xaxis.set_tick_params(labelbottom=False)
                ax1.set_xticks([])
                ax1.set_ylabel("Voltage [V]")
                x = np.arange(0, len(table['VA'][SLICE]) / self.SAMPLE_RATE, 1 / self.SAMPLE_RATE)
                for ch in WAVEFORM_VOLTAGE_CHANNELS:
                    ax1.plot(
                        x, scale_voltage(table[ch][SLICE]), label=ch, color=COLOR_SCHEMES.get(ch)
                    )
                ax1.legend()

                # Current subplot
                ax2.set_title("Current")
                ax2.set_xlabel("Elapsed time [s]")
                ax2.set_ylabel("Current [A]")
                for ch in ['IA', 'IB', 'IC']:
                    ax2.plot(
                        x, scale_current(table[ch][SLICE]), label=ch, color=COLOR_SCHEMES.get(ch)
                    )
                ax2.plot(
                    x,
                    scale_neutral_current(table['IN'][SLICE]),
                    label='IN',
                    color=COLOR_SCHEMES.get('IN'),
                )
                ax2.legend()

                fig.savefig(file_base + "_waveform.svg")
                plt.close(fig)

        except Exception as e:
            logger.error(f"Error: Matplotlib plotting failed: {e}")
            raise RuntimeError(f"Plotting failed: {e}") from e
