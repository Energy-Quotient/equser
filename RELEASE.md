# Release Procedure

This document describes how to cut a new release of `equser` and publish it to PyPI.

## Prerequisites

- Commit access to this repository.
- A PyPI account with an API token registered as a maintainer of `equser`.
- `~/.pypirc` configured with the token:

  ```
  [pypi]
  username = __token__
  password = pypi-YOUR-TOKEN

  [testpypi]
  username = __token__
  password = pypi-YOUR-TEST-TOKEN
  ```

- `python3 -m pip install --upgrade build twine` (the release script will do this for you).

## Versioning

`equser` follows semantic versioning. The canonical version lives in `equser/_version.py`
and is exposed via `equser.__version__`. `pyproject.toml` reads from this file via
`hatch.version`.

Bump with `scripts/bump-version.py`:

```bash
python3 scripts/bump-version.py patch   # 0.0.3 -> 0.0.4
python3 scripts/bump-version.py minor   # 0.0.3 -> 0.1.0
python3 scripts/bump-version.py major   # 0.0.3 -> 1.0.0
python3 scripts/bump-version.py 0.0.5   # explicit version
```

## Public-safety guardrail

`equser` is published to PyPI and its repository is public. It is a **client
toolkit only** — it must never ship secrets or internal-only detail. The
following categories belong in the private repos, not here:

- Secrets of any kind (tokens, keys, passwords, connection strings).
- Internal service, host, mount, and deployment names or paths; internal
  env-var names; and internal-only ports presented as gateway internals.
- Internal network topology, internal ticket IDs, retired internal codenames,
  and internal package/crate names.
- Unreleased-product roadmap surfaces (types or endpoints that don't ship yet).

The specific patterns are encoded in `scripts/check-public-safe.py` (see below)
rather than listed here, so this public file is not itself a catalog of them.

`scripts/check-public-safe.py` enforces this. It runs automatically inside
`scripts/release.sh` (fail-closed, against the built artifacts) and in CI
(`.github/workflows/ci.yml`, against both the tree and the built artifacts).
Run it manually any time:

```bash
python3 scripts/check-public-safe.py          # scan the working tree
python3 scripts/check-public-safe.py --dist    # scan built dist/ artifacts
```

Reviewed, intentional matches go in `scripts/public-safe-allow.txt`.

## Release steps

1. **Land the changes.** All fixes and features for the release should be merged into
   the active dev branch.

2. **Update the CHANGELOG.** Move the contents of the `[Unreleased]` section under a
   new `## [X.Y.Z] - YYYY-MM-DD` heading and leave a fresh `[Unreleased]` section
   above it.

3. **Bump the version.**

   ```bash
   python3 scripts/bump-version.py X.Y.Z
   ```

4. **Commit the release.**

   ```bash
   git commit -am "chore(release): vX.Y.Z"
   ```

5. **(Optional) Dry-run via TestPyPI.**

   ```bash
   ./scripts/release.sh --test
   ```

   Then install from TestPyPI in a clean venv and smoke-test:

   ```bash
   pip install --index-url https://test.pypi.org/simple/ \
               --extra-index-url https://pypi.org/simple/ \
               equser==X.Y.Z
   ```

6. **Publish to PyPI.**

   ```bash
   ./scripts/release.sh
   ```

   The script will build the wheel + sdist, run `twine check`, upload to PyPI, and
   create a local `vX.Y.Z` git tag on success.

7. **Push the commit and tag.**

   ```bash
   git push origin <branch> --follow-tags
   ```

## Post-release

Bump the in-tree version to the next development target so later work on the branch
does not share a version number with a published release:

```bash
python3 scripts/bump-version.py <next-dev-version>
git commit -am "chore: start <next-dev-version> dev"
```

## Troubleshooting

- **`scripts/release.sh` refuses to run because the tag already exists.** Bump the
  version in `equser/_version.py` before running the script.
- **`twine upload` rejects the release.** PyPI does not allow re-uploading the same
  version. Bump to the next patch and try again.
- **Wheel missing files.** Check `[tool.hatch.build]` in `pyproject.toml`; notebook
  and data fixtures must be explicitly included.
