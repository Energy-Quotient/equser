"""Tests for equser.plotting modules.

Requires matplotlib (``[analysis]`` extra).
"""

import pytest

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for testing
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

pytestmark = pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")


class TestPlottingImports:
    def test_module_imports(self):
        from equser.plotting import (
            COLOR_SCHEMES,
            VOLTAGE_CHANNELS,
            PowerMonitorPlotter,
            WaveformPlotter,
        )
        assert PowerMonitorPlotter is not None
        assert WaveformPlotter is not None
        assert isinstance(COLOR_SCHEMES, dict)
        assert len(VOLTAGE_CHANNELS) > 0

    def test_color_schemes_has_waveform_keys(self):
        from equser.plotting import COLOR_SCHEMES
        for ch in ['VA', 'VB', 'VC', 'IA', 'IB', 'IC', 'IN']:
            assert ch in COLOR_SCHEMES


class TestPowerMonitorPlotter:
    def test_plot_pmon_file(self, sample_pmon_parquet, tmp_path):
        from equser.plotting import PowerMonitorPlotter
        plotter = PowerMonitorPlotter(output_dir=tmp_path)
        result = plotter.plot_file(str(sample_pmon_parquet))
        assert result is True

        # Check at least one SVG was created
        svgs = list(tmp_path.glob('*.svg'))
        assert len(svgs) > 0


class TestWaveformPlotter:
    def test_plot_cpow_file(self, sample_cpow_parquet, tmp_path):
        from equser.plotting import WaveformPlotter
        plotter = WaveformPlotter(output_dir=tmp_path)
        result = plotter.plot_file(str(sample_cpow_parquet))
        assert result is True

        svgs = list(tmp_path.glob('*.svg'))
        assert len(svgs) > 0

    def test_plot_float_cpow(self, sample_cpow_float_parquet, tmp_path):
        from equser.plotting import WaveformPlotter
        plotter = WaveformPlotter(output_dir=tmp_path)
        result = plotter.plot_file(str(sample_cpow_float_parquet))
        assert result is True
