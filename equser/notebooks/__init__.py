"""Bundled reference notebooks for EQ Synapse data analysis.

Provides functions to list, locate, and copy the reference notebooks that
ship inside the ``equser`` wheel. Notebooks are organised into two
categories:

- **tutorials/** -- step-by-step introductions to data loading, the REST API,
  and live streaming.
- **analysis/** -- ready-to-use analysis templates (harmonics, power trends,
  delta-configuration).

Example::

    from equser.notebooks import list_notebooks, copy_notebooks

    # See what is available
    for nb in list_notebooks():
        print(nb)

    # Copy all notebooks to a working directory
    copy_notebooks('/var/lib/eq-sight/notebooks')

CLI usage::

    equser notebooks list
    equser notebooks copy --dest /var/lib/eq-sight/notebooks
"""

import shutil
import sys
from pathlib import Path
from typing import List, Optional

if sys.version_info >= (3, 11):
    from importlib.resources import files as _resource_files
else:
    from importlib.resources import files as _resource_files  # backport in 3.9+


def _package_dir() -> Path:
    """Return the on-disk path to the notebooks package directory."""
    ref = _resource_files("equser.notebooks")
    # importlib.resources.files() returns a Traversable; for installed
    # packages this is a Path-like pointing at the real directory.
    return Path(str(ref))


def list_notebooks() -> list[str]:
    """Return a sorted list of notebook paths relative to the package.

    Returns:
        List of strings like ``'tutorials/01-parquet-files.ipynb'``.
    """
    root = _package_dir()
    notebooks = []
    for nb in sorted(root.rglob("*.ipynb")):
        notebooks.append(str(nb.relative_to(root)))
    return notebooks


def get_notebook_path(name: str) -> Path:
    """Return the absolute path to a bundled notebook.

    Args:
        name: Relative path as returned by :func:`list_notebooks`
            (e.g. ``'tutorials/01-parquet-files.ipynb'``).

    Returns:
        Absolute :class:`~pathlib.Path` to the notebook file.

    Raises:
        FileNotFoundError: If the notebook does not exist in the package.
    """
    path = _package_dir() / name
    if not path.is_file():
        raise FileNotFoundError(f"Notebook not found: {name}")
    return path


def copy_notebooks(
    dest: str,
    overwrite: bool = False,
    category: str | None = None,
) -> list[Path]:
    """Copy bundled notebooks to a destination directory.

    Args:
        dest: Target directory. Created if it does not exist.
        overwrite: If ``True``, overwrite existing files. If ``False``
            (default), skip files that already exist.
        category: Optional filter -- ``'tutorials'`` or ``'analysis'``.
            If ``None``, copies all notebooks.

    Returns:
        List of :class:`~pathlib.Path` objects for each file written.
    """
    dest_dir = Path(dest)
    root = _package_dir()
    copied: list[Path] = []

    for rel in list_notebooks():
        if category and not rel.startswith(category + "/"):
            continue

        src = root / rel
        dst = dest_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        if dst.exists() and not overwrite:
            continue

        shutil.copy2(src, dst)
        copied.append(dst)

    return copied
