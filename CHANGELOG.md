# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-02-06

First public release. Clean, open-source user toolkit for EQ Wave power quality data.

### Modules
- **equser.data** - Load CPOW and PMon Parquet files with automatic scaling, timestamp parsing
- **equser.analysis** - Waveform analysis: zero-crossing detection, AC cycle extraction
- **equser.api** - REST and WebSocket clients for EQ Synapse gateways (requires `[analysis]`)
- **equser.plotting** - Static matplotlib plots for PMon and CPOW data (requires `[analysis]`)
- **equser.pmon** - Live sensor acquisition and Avro-to-Parquet conversion (requires `[daq]`)
- **equser.core** - YAML configuration loading, XDG-compliant path resolution
- **equser.utils** - Logging with optional color, DateTime with floor-division

### Dependency Tiers
- **Base**: numpy, pyarrow, pyyaml (data loading + analysis)
- **[daq]**: avro, fastavro (live sensor acquisition)
- **[analysis]**: matplotlib, requests, websocket-client (plotting + API)
- **[jupyter]**: `[analysis]` + jupyterlab, duckdb, ipywidgets, ipykernel, nbconvert
- **[cli]**: argcomplete; **[color]**: colorlog; **[dev]**: pytest, ruff, mypy
- **[full]**: all of the above (except dev)

### CLI
- `equser pmon acquire` - Start power monitoring from EQ Wave sensor
- `equser pmon convert` - Convert Avro files to Parquet
- `equser plot` - Plot PMon or CPOW data files

[Unreleased]: https://github.com/eq-systems/equser/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/eq-systems/equser/releases/tag/v0.2.0
