"""Tests for the equser.notebooks module."""

import json
from pathlib import Path

import pytest

from equser.notebooks import copy_notebooks, get_notebook_path, list_notebooks


class TestListNotebooks:
    def test_returns_list(self):
        result = list_notebooks()
        assert isinstance(result, list)

    def test_contains_expected_notebooks(self):
        result = list_notebooks()
        expected = [
            "analysis/ai-event-analysis.ipynb",
            "analysis/delta-analysis.ipynb",
            "analysis/harmonic-analysis.ipynb",
            "analysis/power-trends.ipynb",
            "tutorials/01-parquet-files.ipynb",
            "tutorials/02-local-duckdb.ipynb",
            "tutorials/03-backend-api.ipynb",
            "tutorials/04-live-streaming.ipynb",
            "welcome.ipynb",
        ]
        assert result == expected

    def test_returns_sorted(self):
        result = list_notebooks()
        assert result == sorted(result)

    def test_all_are_relative_paths(self):
        for nb in list_notebooks():
            assert not nb.startswith("/")


class TestGetNotebookPath:
    def test_returns_path(self):
        notebooks = list_notebooks()
        assert len(notebooks) > 0
        path = get_notebook_path(notebooks[0])
        assert isinstance(path, Path)
        assert path.is_file()

    def test_valid_json(self):
        """Every bundled notebook should be valid JSON (nbformat)."""
        for nb in list_notebooks():
            path = get_notebook_path(nb)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert "cells" in data
            assert "nbformat" in data

    def test_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            get_notebook_path("nonexistent/notebook.ipynb")


class TestCopyNotebooks:
    def test_copies_all(self, tmp_path):
        dest = tmp_path / "notebooks"
        copied = copy_notebooks(str(dest))
        assert len(copied) == len(list_notebooks())
        for p in copied:
            assert p.is_file()
            assert p.suffix == ".ipynb"

    def test_preserves_structure(self, tmp_path):
        dest = tmp_path / "notebooks"
        copy_notebooks(str(dest))
        assert (dest / "tutorials").is_dir()
        assert (dest / "analysis").is_dir()

    def test_skip_existing(self, tmp_path):
        dest = tmp_path / "notebooks"
        first = copy_notebooks(str(dest))
        second = copy_notebooks(str(dest), overwrite=False)
        assert len(first) > 0
        assert len(second) == 0

    def test_overwrite(self, tmp_path):
        dest = tmp_path / "notebooks"
        first = copy_notebooks(str(dest))
        second = copy_notebooks(str(dest), overwrite=True)
        assert len(second) == len(first)

    def test_category_filter(self, tmp_path):
        dest = tmp_path / "notebooks"
        copied = copy_notebooks(str(dest), category="tutorials")
        assert all("tutorials/" in str(p) for p in copied)
        assert len(copied) == 4

    def test_analysis_category(self, tmp_path):
        dest = tmp_path / "notebooks"
        copied = copy_notebooks(str(dest), category="analysis")
        assert all("analysis/" in str(p) for p in copied)
        assert len(copied) == 4
