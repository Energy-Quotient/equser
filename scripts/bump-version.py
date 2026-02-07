#!/usr/bin/env python3
"""Bump the version number in _version.py.

Usage:
    python scripts/bump-version.py patch    # 0.1.0 -> 0.1.1
    python scripts/bump-version.py minor    # 0.1.0 -> 0.2.0
    python scripts/bump-version.py major    # 0.1.0 -> 1.0.0
    python scripts/bump-version.py 0.2.0    # Set exact version
"""

import re
import sys
from pathlib import Path

VERSION_FILE = Path(__file__).parent.parent / "_version.py"


def read_version() -> str:
    """Read current version from _version.py."""
    content = VERSION_FILE.read_text()
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if not match:
        raise ValueError("Could not find __version__ in _version.py")
    return match.group(1)


def write_version(version: str) -> None:
    """Write new version to _version.py."""
    content = f'''"""Single-source version for equser package.

Update this file when releasing a new version.
Follow semantic versioning: https://semver.org/
"""

__version__ = "{version}"
__version_info__ = tuple(int(x) for x in __version__.split("."))
'''
    VERSION_FILE.write_text(content)


def bump_version(current: str, bump_type: str) -> str:
    """Bump version according to semver."""
    parts = [int(x) for x in current.split(".")]
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {current}")

    major, minor, patch = parts

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        # Assume it's an exact version
        if not re.match(r"^\d+\.\d+\.\d+$", bump_type):
            raise ValueError(f"Invalid version or bump type: {bump_type}")
        return bump_type


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    bump_type = sys.argv[1]
    current = read_version()

    try:
        new_version = bump_version(current, bump_type)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Bumping version: {current} -> {new_version}")
    write_version(new_version)
    print(f"Updated {VERSION_FILE}")
    print()
    print("Next steps:")
    print(f"  1. Update CHANGELOG.md with changes for v{new_version}")
    print(f"  2. Commit: git commit -am 'Bump version to {new_version}'")
    print(f"  3. Release: ./scripts/release.sh")


if __name__ == "__main__":
    main()
