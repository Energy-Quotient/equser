# equser

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

User toolkit for power quality data from EQ Wave sensors.

## Overview

equser is a Python library for loading, analyzing, and visualizing continuous
waveform (CPOW) and power monitoring (PMon) data from EQ Wave hardware. It
provides:

- **Data loading** (`data`): Load CPOW and PMon Parquet files with automatic scaling
- **Waveform analysis** (`analysis`): Zero-crossing detection, cycle extraction
- **Visualization** (`plotting`): Static plots for power quality data (requires `[analysis]`)
- **API client** (`api`): REST and WebSocket clients for EQ gateways (requires `[analysis]`)
- **Live acquisition** (`pmon`): Real-time sensor data acquisition (requires `[daq]`)
- **CLI tools**: Command-line interface for monitoring and conversion

## Installation

### Base installation (data loading + analysis)

```bash
pip install equser
```

### With plotting and API support

```bash
pip install equser[analysis]
```

### With JupyterLab notebook environment

```bash
pip install equser[jupyter]
```

### With live sensor acquisition

```bash
pip install equser[daq]
```

### Full installation (all features)

```bash
pip install equser[full]
```

## Quick Start

### Load and explore CPOW data

```python
from equser.data import load_cpow_scaled

result = load_cpow_scaled('20250623_075056.parquet')
print(f"Voltage A peak: {result['VA'].max():.1f} V")
print(f"Start time: {result['start_time']}")
print(f"Sample rate: {result['sample_rate']} Hz")
```

### Load PMon summary data

```python
from equser.data import load_pmon

table = load_pmon('20250623_0750.parquet')
print(table.column_names)
```

### Analyze waveform zero crossings

```python
import numpy as np
from equser.data import load_cpow_scaled, SAMPLE_RATE_HZ
from equser.analysis import find_zero_crossings

result = load_cpow_scaled('cpow_data.parquet')
time = np.arange(len(result['VA'])) / SAMPLE_RATE_HZ
crossings, indices = find_zero_crossings(result['VA'], time)
print(f"Found {len(crossings)} zero crossings")
```

### Plot data (requires `[analysis]`)

```python
from equser.plotting import PowerMonitorPlotter, WaveformPlotter

# Plot power monitor data
plotter = PowerMonitorPlotter()
plotter.plot_file('pmon_data.parquet')

# Plot waveform data
wf_plotter = WaveformPlotter()
wf_plotter.plot_file('cpow_data.parquet')
```

### Query a gateway (requires `[analysis]`)

```python
from equser.api import GatewayClient

client = GatewayClient('http://gateway')
devices = client.list_devices()
table = client.get_pmon_data(devices[0]['id'])
```

### Command Line

```bash
# Start power monitoring (requires EQ Wave sensor + [daq])
equser pmon acquire -c config.yaml

# Convert Avro files to Parquet (requires [daq])
equser pmon convert data/*.avro --remove

# Plot data file (requires [analysis])
equser plot data.parquet
```

## Reference notebooks

equser bundles a set of tutorial and analysis notebooks inside the installed
package, so they travel with `pip install` (no separate download). Because they
live under `site-packages`, use the CLI rather than hunting for the path:

```bash
# One step: copy the notebooks into ./equser-notebooks and open JupyterLab there
equser notebooks launch

# Or copy them into a directory of your choice (then open however you like)
equser notebooks copy --dest ~/eq-notebooks

# See what's bundled, or print where they live
equser notebooks list
equser notebooks path                                  # the bundled directory
equser notebooks path tutorials/03-backend-api.ipynb   # a specific notebook
```

`launch` requires the JupyterLab environment (`pip install equser[jupyter]`).

From inside an already-running JupyterLab, you can pull a writable copy into the
current folder in one cell:

```python
from equser.notebooks import copy_notebooks, get_notebooks_dir
copy_notebooks('.')          # writes tutorials/ and analysis/ here
print(get_notebooks_dir())   # or just locate the read-only originals
```

Bundled notebooks:

| Notebook | What it covers |
|----------|----------------|
| `tutorials/01-parquet-files.ipynb` | Load and plot CPOW/PMon data from parquet files |
| `tutorials/02-local-duckdb.ipynb` | Query parquet files with SQL via DuckDB |
| `tutorials/03-backend-api.ipynb` | Query a gateway over the REST API |
| `tutorials/04-live-streaming.ipynb` | Live CPOW and spectral WebSocket streaming |
| `analysis/harmonic-analysis.ipynb` | FFT-based harmonic analysis (IEEE 519) |
| `analysis/power-trends.ipynb` | Long-term voltage, frequency, and power trends |
| `analysis/delta-analysis.ipynb` | Delta-configuration analysis |
| `analysis/ai-event-analysis.ipynb` | AI event analysis via the RAG API (needs demo access) |

## Configuration

equser looks for configuration in the following locations (in order):

1. `EQUSER_CONFIG` environment variable
2. `./equser.yaml` (current directory)
3. `~/.config/equser/config.yaml` (XDG config)
4. `/etc/equser/config.yaml` (system-wide)

Example configuration:

```yaml
sensor:
  address: "192.168.10.10"
  port: 1535

pmon:
  connection:
    retry_delay: 3
  parquet:
    interval: 86400
    compression:
      method: ZSTD
      level: 4
```

## Dependency Tiers

| Extra | Description | Key Packages |
|-------|-------------|--------------|
| *(base)* | Data loading, analysis, CLI | numpy, pyarrow, pyyaml, argcomplete, colorlog |
| `[daq]` | Live sensor acquisition | avro, fastavro |
| `[analysis]` | Plotting + API client | matplotlib, requests, websocket-client |
| `[jupyter]` | Full notebook environment | `[analysis]` + jupyterlab, duckdb, ipywidgets |
| `[dev]` | Development tools | pytest, ruff, mypy |
| `[full]` | All of the above (except dev) | - |

## Requirements

- Python 3.10 or later
- Linux (for hardware integration features)

## Documentation

- [API Documentation](https://equser.eq.systems)
- [Changelog](CHANGELOG.md)

## License

MIT License — © 2026 EQ Systems Inc.

## About

equser is developed by [Energy Quotient](https://eq.systems) for continuous waveform intelligence in power systems. It provides Python access to data from EQ gateways running EQ Coherence™ software.
