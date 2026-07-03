"""Tests for equser CLI."""

import importlib.util

import pytest

from equser.cli import main

HAS_MPL = importlib.util.find_spec("matplotlib") is not None


class TestCli:
    def test_help_exits_zero(self):
        """Running with no args prints help and returns 0."""
        result = main([])
        assert result == 0

    def test_plot_missing_file(self, tmp_path):
        result = main(['plot', str(tmp_path / 'nonexistent.parquet')])
        assert result == 1

    def test_pmon_help(self, capsys):
        """pmon with no subcommand prints help."""
        main(['pmon'])
        captured = capsys.readouterr()
        assert 'acquire' in captured.out or 'convert' in captured.out


@pytest.mark.skipif(not HAS_MPL, reason="matplotlib not installed (requires [analysis] extra)")
class TestPlotCommand:
    def test_plot_cpow_writes_svg(self, sample_cpow_parquet, tmp_path):
        out_dir = tmp_path / 'plots'
        result = main(['plot', str(sample_cpow_parquet), '--cpow', '-o', str(out_dir)])
        assert result == 0
        assert list(out_dir.glob('*.svg'))

    def test_plot_pmon_writes_svg(self, sample_pmon_parquet, tmp_path):
        out_dir = tmp_path / 'plots'
        result = main(['plot', str(sample_pmon_parquet), '--pmon', '-o', str(out_dir)])
        assert result == 0
        assert list(out_dir.glob('*.svg'))

    def test_plot_autodetects_cpow(self, sample_cpow_parquet):
        # No --cpow/--pmon flag: type is inferred from the schema.
        assert main(['plot', str(sample_cpow_parquet)]) == 0


class TestPmonPassthrough:
    def test_forwards_option_flags(self, monkeypatch):
        """Option flags after `pmon` must reach the pmon subcommand, not error out."""
        received = {}

        def fake_pmon_main(args):
            received['args'] = list(args)
            return 0

        monkeypatch.setattr('equser.pmon.main', fake_pmon_main)
        result = main(['pmon', 'acquire', '-c', 'config.yaml', '--remove'])
        assert result == 0
        assert received['args'] == ['acquire', '-c', 'config.yaml', '--remove']
