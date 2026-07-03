"""Waveform analysis functions for CPOW data.

Uses only base dependencies (numpy). Plotting helpers that require matplotlib
are guarded and will raise ImportError with a helpful message if matplotlib
is not installed.

Usage::

    from equser.analysis import find_zero_crossings, extract_complete_cycles

    crossings, indices = find_zero_crossings(voltage_array, time_array)
"""

from equser.analysis.waveform import (
    extract_complete_cycles,
    find_zero_crossings,
)

__all__ = [
    'extract_complete_cycles',
    'find_zero_crossings',
]

# plot_extracted_cycles is intentionally not in __all__; import it directly
# if needed: from equser.analysis.waveform import plot_extracted_cycles
