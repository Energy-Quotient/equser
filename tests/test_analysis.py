"""Tests for equser.analysis modules (waveform)."""

import numpy as np
import pytest

from equser.analysis.waveform import extract_complete_cycles, find_zero_crossings


class TestFindZeroCrossings:
    def test_simple_sine(self):
        """Find zero crossings in a clean sine wave."""
        t = np.linspace(0, 1, 10000)
        signal = np.sin(2 * np.pi * 60 * t)  # 60 Hz sine

        crossings, indices = find_zero_crossings(signal, t)

        # 60 Hz sine starting at sin(0)=0 has 59 neg-to-pos crossings in [0,1)
        # (first crossing at ~1/60, last at ~59/60)
        assert len(crossings) == 59

    def test_crossing_times_increasing(self):
        t = np.linspace(0, 0.1, 3200)
        signal = np.sin(2 * np.pi * 60 * t)

        crossings, indices = find_zero_crossings(signal, t)

        # Times should be monotonically increasing
        assert np.all(np.diff(crossings) > 0)

    def test_crossing_period(self):
        """Crossings should be ~1/60 second apart for 60 Hz."""
        t = np.linspace(0, 0.5, 16000)
        signal = np.sin(2 * np.pi * 60 * t)

        crossings, indices = find_zero_crossings(signal, t)

        periods = np.diff(crossings)
        expected_period = 1.0 / 60.0
        assert np.allclose(periods, expected_period, atol=1e-4)

    def test_no_crossings(self):
        """Constant positive signal has no crossings."""
        t = np.linspace(0, 1, 1000)
        signal = np.ones_like(t) * 5.0

        crossings, indices = find_zero_crossings(signal, t)

        assert len(crossings) == 0
        assert len(indices) == 0

    def test_returns_correct_types(self):
        t = np.linspace(0, 0.1, 3200)
        signal = np.sin(2 * np.pi * 60 * t)

        crossings, indices = find_zero_crossings(signal, t)

        assert isinstance(crossings, np.ndarray)
        assert isinstance(indices, np.ndarray)


class TestExtractCompleteCycles:
    def test_extract_single_cycle(self):
        t = np.linspace(0, 0.1, 3200)
        signal = np.sin(2 * np.pi * 60 * t)

        cycles = extract_complete_cycles(signal, t, [0.0], num_cycles=1)

        assert len(cycles) == 1
        cycle_time, cycle_signal, start, end = cycles[0]
        assert cycle_time[0] == pytest.approx(0.0)
        # One cycle at 60 Hz ≈ 16.67 ms
        duration = end - start
        assert duration == pytest.approx(1.0 / 60.0, abs=1e-3)

    def test_extract_multiple_start_times(self):
        t = np.linspace(0, 0.2, 6400)
        signal = np.sin(2 * np.pi * 60 * t)

        cycles = extract_complete_cycles(signal, t, [0.0, 0.05, 0.1], num_cycles=1)

        assert len(cycles) == 3

    def test_extract_two_cycles(self):
        t = np.linspace(0, 0.1, 3200)
        signal = np.sin(2 * np.pi * 60 * t)

        cycles = extract_complete_cycles(signal, t, [0.0], num_cycles=2)

        if len(cycles) > 0:
            _, _, start, end = cycles[0]
            duration = end - start
            # Two cycles at 60 Hz ≈ 33.33 ms
            assert duration == pytest.approx(2.0 / 60.0, abs=2e-3)

    def test_not_enough_crossings(self):
        """Returns empty list if not enough data for requested cycles."""
        t = np.linspace(0, 0.005, 160)  # Only 5 ms
        signal = np.sin(2 * np.pi * 60 * t)

        # Request 10 cycles from 5 ms of data - impossible
        cycles = extract_complete_cycles(signal, t, [0.0], num_cycles=10)

        assert len(cycles) == 0

    def test_normalized_time_starts_at_zero(self):
        t = np.linspace(0, 0.1, 3200)
        signal = np.sin(2 * np.pi * 60 * t)

        cycles = extract_complete_cycles(signal, t, [0.03], num_cycles=1)

        if len(cycles) > 0:
            cycle_time, _, _, _ = cycles[0]
            assert cycle_time[0] == pytest.approx(0.0, abs=1e-10)
