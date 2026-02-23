"""Bundled reference notebooks for EQ Synapse data analysis.

Provides functions to list, locate, copy, and describe the reference notebooks
that ship inside the ``equser`` wheel. Notebooks are organised into two
categories:

- **tutorials/** -- step-by-step introductions to data loading, the REST API,
  and live streaming.
- **analysis/** -- ready-to-use analysis templates (harmonics, power trends,
  delta-configuration).

Example::

    from equser.notebooks import list_notebooks, copy_notebooks, describe_notebooks

    # See what is available
    for nb in list_notebooks():
        print(nb)

    # Rich metadata (title, description) extracted from each notebook
    for info in describe_notebooks():
        print(f"{info['path']}: {info['title']}")

    # Copy all notebooks to a working directory
    copy_notebooks('/var/lib/eq-sight/notebooks')

CLI usage::

    equser notebooks list
    equser notebooks copy --dest /var/lib/eq-sight/notebooks
"""

import json
import shutil
import sys
from pathlib import Path

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


def describe_notebooks(category: str | None = None) -> list[dict]:
    """Return metadata for each bundled notebook.

    Reads each notebook's first markdown cell to extract a title and
    description, so the results stay in sync with the actual notebook
    contents.

    Args:
        category: Optional filter -- ``'tutorials'`` or ``'analysis'``.
            If ``None``, returns all notebooks.

    Returns:
        List of dicts, each with keys:

        - **path** -- relative path (e.g. ``'tutorials/01-parquet-files.ipynb'``)
        - **category** -- directory name (``'tutorials'`` or ``'analysis'``)
        - **title** -- first ``#`` heading from the notebook
        - **description** -- first paragraph after the heading (may be empty)
    """
    root = _package_dir()
    results: list[dict] = []

    for rel in list_notebooks():
        cat = rel.split("/")[0] if "/" in rel else ""
        if category and cat != category:
            continue

        nb_path = root / rel
        title, description = _extract_notebook_metadata(nb_path)

        results.append({
            "path": rel,
            "category": cat,
            "title": title,
            "description": description,
        })

    return results


def _extract_notebook_metadata(nb_path: Path) -> tuple[str, str]:
    """Extract the title and description from a notebook's first markdown cell.

    Returns:
        A ``(title, description)`` tuple.  Falls back to the filename
        (without extension) if no heading is found.
    """
    fallback_title = nb_path.stem.replace("-", " ").replace("_", " ").strip()

    try:
        data = json.loads(nb_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback_title, ""

    for cell in data.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue

        lines = cell.get("source", [])
        if isinstance(lines, str):
            lines = lines.splitlines(True)

        # Find the first '# …' heading
        title = ""
        heading_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped.lstrip("# ").strip()
                heading_idx = i
                break

        if not title:
            return fallback_title, ""

        # Collect the description: non-empty lines after the heading,
        # stopping at the next heading, section marker, or blank line
        # that follows at least one description line.
        desc_lines: list[str] = []
        for line in lines[heading_idx + 1 :]:
            stripped = line.strip()
            if stripped.startswith("#"):
                break
            if stripped.startswith("**") and stripped.endswith("**"):
                # Section list like "**Sections:**" -- stop
                break
            if not stripped:
                if desc_lines:
                    break
                continue  # skip leading blank lines
            desc_lines.append(stripped)

        description = " ".join(desc_lines)
        return title, description

    return fallback_title, ""


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
