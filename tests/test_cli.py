"""Tests for equser CLI."""

import pytest

from equser.cli import main


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
