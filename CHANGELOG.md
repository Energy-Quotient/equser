# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.4] - 2026-05-02

### Changed
- Renamed `SynapseClient` to `GatewayClient`. The class addresses one EQ gateway over REST; the new name matches the addressing model (the gateway is the unit you connect to). (A future `DatalakeClient` will be added as a sibling for cross-site queries against the server-side aggregated datalake.)
- Updated docstrings and brand text throughout (`equser.api`, `equser.api.streaming`, `equser.snapshot`, `equser.notebooks`, README, CHANGELOG note for v0.0.1) to use "EQ gateway" for the hardware and reference EQ Coherence™ where the gateway-internal software is meant.

### Deprecated
- `SynapseClient` is now a deprecated module-level alias for `GatewayClient`. Importing it (from `equser.api` or `equser.api.client`) still resolves to `GatewayClient` so existing user code keeps working, but emits a `DeprecationWarning` so users see the migration signal. The alias and its `__getattr__` hooks will be removed in a future release; migrate to `from equser.api import GatewayClient`.

### Fixed
- `connect_cpow_stream` now strips the 11-byte cycle header before Arrow IPC parse (commit `e3879fe`). Resolves a parse error on real CPOW WebSocket streams that include the cycle header prefix.

## [0.0.3] - 2026-04-23

### Added
- `RELEASE.md` documenting the PyPI release procedure.

### Fixed
- `load_cpow_scaled()` now reads scaling metadata (`iscale`, `vscale`,
  `schema_version`, `topology`, `neutral_connected`, `start_time`) from the
  Arrow schema. Production CPOW files carry these on the schema only; the
  previous implementation read the Parquet footer key-value map and silently
  returned `iscale=1.0` on those files.
- `scripts/bump-version.py` and `scripts/release.sh` now look for
  `equser/_version.py` in the correct location; previously both scripts
  referenced a non-existent repo-root path.

## [0.0.2] - 2026-04-11

### Changed
- `load_cpow_scaled()` now reads v3 schema metadata and returns additional keys:
  `schema_version`, `topology`, and `neutral_connected`.
- CPOW channel arrays are now explicitly promoted to float64 before applying
  the scale factor, preserving the full 24-bit ADC dynamic range for v3 int32
  files.

### Added
- `CYCLE_START_CHANNELS` constant listing the optional v3 phase cycle-boundary
  columns (`cycle_start_a`, `cycle_start_b`, `cycle_start_c`).
- `load_cpow_scaled()` returns `cycle_start_a`, `cycle_start_b`, and
  `cycle_start_c` as numpy int64 arrays when those columns are present in the
  file. Values are nanoseconds since epoch; zero means no boundary at that
  sample.

## [0.0.1] - 2026-02-06

Initial public release. User toolkit for EQ Wave power quality data.

### Modules
- **equser.data** - Load CPOW and PMon Parquet files with automatic scaling, timestamp parsing
- **equser.analysis** - Waveform analysis: zero-crossing detection, AC cycle extraction
- **equser.api** - REST and WebSocket clients for EQ gateways (requires `[analysis]`; class was originally named `SynapseClient`, renamed to `GatewayClient` in [Unreleased]; `SynapseClient` preserved as a deprecated backward-compat alias)
- **equser.plotting** - Static matplotlib plots for PMon and CPOW data (requires `[analysis]`)
- **equser.pmon** - Live sensor acquisition and Avro-to-Parquet conversion (requires `[daq]`)
- **equser.core** - YAML configuration loading, XDG-compliant path resolution
- **equser.utils** - Logging with optional color, DateTime with floor-division
- **equser.notebooks** - Bundled reference notebooks with list/copy API
- **equser.widgets** - Interactive file selector for JupyterLab (requires `[jupyter]`)
- **equser.snapshot** - Waveform capture via gateway WebSocket

### Dependency Tiers
- **Base**: numpy, pyarrow, pyyaml, argcomplete, colorlog (data loading, analysis, CLI)
- **[daq]**: avro, fastavro (live sensor acquisition)
- **[analysis]**: matplotlib, requests, websocket-client (plotting + API)
- **[jupyter]**: `[analysis]` + jupyterlab, duckdb, ipywidgets, ipykernel, nbconvert
- **[full]**: all of the above

### CLI
- `equser pmon acquire` - Start power monitoring from EQ Wave sensor
- `equser pmon convert` - Convert Avro files to Parquet
- `equser plot` - Plot PMon or CPOW data files
- `equser notebooks list` - List bundled reference notebooks
- `equser notebooks copy` - Copy reference notebooks to a directory
- `equser snapshot` - Capture live waveform data to a Parquet file

[Unreleased]: https://github.com/Energy-Quotient/equser/compare/v0.0.2...HEAD
[0.0.2]: https://github.com/Energy-Quotient/equser/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/Energy-Quotient/equser/releases/tag/v0.0.1
