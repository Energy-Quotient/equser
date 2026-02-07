# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-06

Initial public release. User toolkit for EQ Wave power quality data.

### Modules
- **equser.data** - Load CPOW and PMon Parquet files with automatic scaling, timestamp parsing
- **equser.analysis** - Waveform analysis: zero-crossing detection, AC cycle extraction
- **equser.api** - REST and WebSocket clients for EQ Synapse gateways (requires `[analysis]`)
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

[Unreleased]: https://github.com/Energy-Quotient/equser/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Energy-Quotient/equser/releases/tag/v0.1.0
