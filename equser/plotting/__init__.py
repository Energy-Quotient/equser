"""
EQ User Tools Plotting Module

Matplotlib-based plotting functions for power quality and waveform data.
These functions can be used from JupyterLab or custom analysis scripts.

Usage:
    import equser as eq

    plotter = eq.plotting.PowerMonitorPlotter()
    plotter.plot_file('pmon_data.parquet')
"""

from .power_quality import (
    PowerMonitorPlotter,
    WaveformPlotter,
    COLOR_SCHEMES,
    VOLTAGE_CHANNELS,
    CURRENT_CHANNELS,
    POWER_CHANNELS,
    FREQ_CHANNELS,
    DEFAULT_VISIBLE_CHANNELS,
)

__all__ = [
    'PowerMonitorPlotter',
    'WaveformPlotter',
    'COLOR_SCHEMES',
    'VOLTAGE_CHANNELS',
    'CURRENT_CHANNELS',
    'POWER_CHANNELS',
    'FREQ_CHANNELS',
    'DEFAULT_VISIBLE_CHANNELS',
]
