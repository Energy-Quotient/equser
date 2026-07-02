"""Waveform analysis utilities for CPOW data.

Functions for zero-crossing detection, cycle extraction, and cycle plotting.
Core analysis functions require only numpy (base dependency). The
:func:`plot_extracted_cycles` function requires matplotlib (``[analysis]`` extra).
"""

from typing import Any

import numpy as np
from numpy.typing import NDArray


def find_zero_crossings(
    signal: NDArray[np.floating],
    time_array: NDArray[np.floating],
) -> tuple[NDArray[np.float64], NDArray[np.intp]]:
    """Find negative-to-positive zero crossings in a signal.

    Uses linear interpolation between adjacent samples to estimate the
    exact crossing time.

    Args:
        signal: Voltage or current waveform array.
        time_array: Corresponding time array (same length as signal).

    Returns:
        Tuple of (crossing_times, crossing_indices) where:

        - ``crossing_times``: interpolated times of zero crossings
        - ``crossing_indices``: integer indices of the sample just before each crossing
    """
    s = np.asarray(signal)
    t = np.asarray(time_array)

    # Negative-to-positive crossings: sample i is < 0 and sample i+1 is >= 0.
    idx = np.nonzero((s[:-1] < 0) & (s[1:] >= 0))[0]
    if idx.size == 0:
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.intp)

    s0 = s[idx].astype(np.float64)
    s1 = s[idx + 1].astype(np.float64)
    t0 = t[idx].astype(np.float64)
    t1 = t[idx + 1].astype(np.float64)

    # Linear interpolation to the crossing time. Because s0 < 0 <= s1, the
    # denominator (s1 - s0) is strictly positive, so no divide-by-zero guard
    # is needed.
    crossing_times = t0 + (t1 - t0) * (-s0) / (s1 - s0)

    return crossing_times, idx.astype(np.intp)


def extract_complete_cycles(
    signal: NDArray[np.floating],
    time_array: NDArray[np.floating],
    start_times: list[float],
    num_cycles: int = 1,
) -> list[tuple[NDArray[np.float64], NDArray[np.floating], float, float]]:
    """Extract complete AC cycles starting from specified times.

    For each requested start time, finds the first zero crossing at or after
    that time and extracts ``num_cycles`` complete cycles (zero-crossing to
    zero-crossing).

    Args:
        signal: Voltage or current waveform array.
        time_array: Corresponding time array (same length as signal).
        start_times: List of times (in the same units as time_array) to start
            extracting cycles from.
        num_cycles: Number of complete cycles to extract from each start time.

    Returns:
        List of tuples, one per valid start time:
        ``(cycle_time_normalized, cycle_signal, actual_start_time, actual_end_time)``

        - ``cycle_time_normalized``: time array normalized to start at 0
        - ``cycle_signal``: signal values for the extracted window
        - ``actual_start_time``: time of the first zero crossing
        - ``actual_end_time``: time of the last zero crossing
    """
    crossing_times, crossing_indices = find_zero_crossings(signal, time_array)

    cycles_data = []

    for start_time in start_times:
        valid_crossings = crossing_times[crossing_times >= start_time]

        if len(valid_crossings) < num_cycles + 1:
            continue

        cycle_start_time = valid_crossings[0]
        cycle_end_time = valid_crossings[num_cycles]

        mask = (time_array >= cycle_start_time) & (time_array <= cycle_end_time)
        cycle_time = time_array[mask]
        cycle_signal = signal[mask]

        cycle_time_normalized = cycle_time - cycle_time[0]
        cycles_data.append(
            (cycle_time_normalized, cycle_signal, float(cycle_start_time), float(cycle_end_time))
        )

    return cycles_data


def plot_extracted_cycles(
    signal_dict: dict[str, NDArray[np.floating]] | NDArray[np.floating],
    time_array: NDArray[np.floating],
    start_times: list[float],
    num_cycles: int = 1,
    epoch_start_time: Any | None = None,
) -> tuple[Any, Any, list[tuple[float, float]]]:
    """Plot complete cycles extracted from specified start times for multiple phases.

    Requires matplotlib (``[analysis]`` extra).

    Args:
        signal_dict: Dictionary mapping phase names to signal arrays
            (e.g. ``{'VA': va_array, 'VB': vb_array}``), or a single array
            (treated as ``{'VA': array}``).
        time_array: Corresponding time array.
        start_times: List of times to start extracting cycles from.
        num_cycles: Number of complete cycles per start time.
        epoch_start_time: Optional datetime for timestamp labels.

    Returns:
        Tuple of (fig, axes, window_times) where ``window_times`` is a list
        of (start_sec, end_sec) tuples.

    Raises:
        ImportError: If matplotlib is not installed.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            "plot_extracted_cycles requires matplotlib.\nInstall with: pip install equser[analysis]"
        ) from exc
    from datetime import datetime, timedelta

    if isinstance(signal_dict, (list, np.ndarray)):
        signal_dict = {'VA': signal_dict}

    first_signal = list(signal_dict.values())[0]
    cycles_data = extract_complete_cycles(first_signal, time_array, start_times, num_cycles)

    if not cycles_data:
        return None, None, []

    window_times = [(actual_start, actual_end) for _, _, actual_start, actual_end in cycles_data]

    phase_colors = {
        'VA': 'black',
        'VB': 'red',
        'VC': 'blue',
        'VAB': 'black',
        'VBC': 'red',
        'VCA': 'blue',
    }

    fig, axes = plt.subplots(1, len(cycles_data), figsize=(12, 5), sharey=True)
    fig.suptitle(
        f"Selected Cycle{'s' if num_cycles > 1 or len(cycles_data) > 1 else ''} - All Phases",
        fontsize=14,
    )
    fig.subplots_adjust(wspace=0.05)

    if len(cycles_data) == 1:
        axes = [axes]

    for i, (ax, (cycle_time, _, actual_start, actual_end)) in enumerate(
        zip(axes, cycles_data, strict=False)
    ):
        nominal_period = 1 / 60
        time_pu = cycle_time / nominal_period

        for phase_name, signal in signal_dict.items():
            mask = (time_array >= actual_start) & (time_array <= actual_end)
            phase_voltage = signal[mask]
            color = phase_colors.get(phase_name, 'gray')
            ax.plot(
                time_pu,
                phase_voltage,
                'o',
                color=color,
                alpha=0.8,
                markersize=0.5,
                label=phase_name,
            )

        ax.axhline(0, color='gray', linestyle='--', alpha=0.5)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, num_cycles)

        if i < len(cycles_data) - 1:
            ax.spines.right.set_visible(False)
            ax.yaxis.tick_left()
        if i > 0:
            ax.spines.left.set_visible(False)
            ax.tick_params(left=False, labelleft=False)

    if len(signal_dict) > 1:
        axes[0].legend(loc='upper right', fontsize=10)

    for i, ax in enumerate(axes):
        if i > 0:
            xticks = ax.get_xticks()
            xticklabels = [label.get_text() for label in ax.get_xticklabels()]
            if len(xticklabels) > 0:
                xticklabels[0] = ''
                ax.set_xticks(xticks)
                ax.set_xticklabels(xticklabels)

    if len(axes) > 1:
        d = 0.3
        kwargs = {
            'marker': [(d, -1), (-d, 1)],
            'markersize': 8,
            'linestyle': "none",
            'color': 'k',
            'mec': 'k',
            'mew': 1,
            'clip_on': False,
        }
        for i in range(len(axes) - 1):
            axes[i].plot([1, 1], [0, 1], transform=axes[i].transAxes, **kwargs)
            axes[i + 1].plot([0, 0], [0, 1], transform=axes[i + 1].transAxes, **kwargs)

    fig.text(0.5, 0.02, 'Time Offset [pu cycle, 60 Hz base]', ha='center', fontsize=12)
    axes[0].set_ylabel('Voltage (V)')

    def _seconds_to_timestamp(epoch_start, time_seconds):
        if isinstance(epoch_start, (int, float)):
            start_dt = datetime.fromtimestamp(epoch_start)
        else:
            start_dt = epoch_start
        target = start_dt + timedelta(seconds=time_seconds)
        return target.strftime('%H:%M:%S.%f')[:-3]

    for ax, (_, _, actual_start, _) in zip(axes, cycles_data, strict=False):
        if epoch_start_time:
            start_ts = _seconds_to_timestamp(epoch_start_time, actual_start)
            label_text = f'Window @\n{start_ts}'
        else:
            label_text = f'Window @\n{actual_start:.6f}s'

        ax.text(
            0.75,
            0.95,
            label_text,
            transform=ax.transAxes,
            ha='center',
            va='top',
            fontsize=10,
            bbox={'boxstyle': 'round,pad=0.3', 'facecolor': 'lightblue'},
        )

    return fig, axes, window_times
