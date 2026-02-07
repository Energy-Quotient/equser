"""EQ User Tools - Power Quality Data Toolkit for EQ Wave Sensors

A Python library for loading, analyzing, and visualizing power quality data
from EQ Wave continuous waveform sensors.

Modules (always available):
    data: Load CPOW and PMon Parquet files, parse timestamps
    analysis: Waveform analysis (zero crossings, cycle extraction)
    pmon: Power monitoring errors, schema, field descriptions
    core: Configuration and path utilities
    utils: Logging and datetime utilities

Modules (always available, continued):
    notebooks: Bundled reference notebooks (list, copy, path helpers)

Modules (require extras):
    plotting: Visualization tools (requires ``[analysis]`` extra)
    api: Gateway REST and WebSocket clients (requires ``[analysis]`` extra)
    widgets: Interactive Jupyter widgets (requires ``[jupyter]`` extra)

Quick start::

    from equser.data import load_cpow_scaled, load_pmon
    result = load_cpow_scaled('cpow_data.parquet')

    from equser.analysis import find_zero_crossings
    crossings, indices = find_zero_crossings(result['VA'], time_array)
"""

from equser._version import __version__, __version_info__

# Core modules always available
from equser import core
from equser import utils
from equser import pmon
from equser import data
from equser import analysis
from equser import notebooks

# Plotting requires [analysis] extra (matplotlib)
try:
    from equser import plotting
    _has_plotting = True
except ImportError:
    _has_plotting = False

# API client requires [analysis] extra (requests, websocket-client)
try:
    from equser import api
    _has_api = True
except ImportError:
    _has_api = False

__all__ = ['core', 'utils', 'pmon', 'data', 'analysis', 'notebooks',
           '__version__', '__version_info__']

if _has_plotting:
    __all__.append('plotting')
if _has_api:
    __all__.append('api')
