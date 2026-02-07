"""Shared test fixtures for equser tests."""

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml


@pytest.fixture
def sample_pmon_parquet(tmp_path):
    """Create a minimal PMon Parquet file (~100 rows)."""
    n = 100
    rng = np.random.default_rng(42)

    # Time: microseconds since epoch, spaced ~1s apart
    base_time = 1719129056_000_000  # ~2024-06-23 07:50:56 UTC
    time_us = np.arange(base_time, base_time + n * 1_000_000, 1_000_000, dtype=np.uint64)

    data = {
        'time_us': pa.array(time_us, type=pa.uint64()),
        'FREQ': pa.array(rng.normal(60.0, 0.01, n).astype(np.float32), type=pa.float32()),
        'AVRMS': pa.array(rng.normal(120.0, 0.5, n).astype(np.float32), type=pa.float32()),
        'BVRMS': pa.array(rng.normal(120.0, 0.5, n).astype(np.float32), type=pa.float32()),
        'CVRMS': pa.array(rng.normal(120.0, 0.5, n).astype(np.float32), type=pa.float32()),
        'AIRMS': pa.array(rng.normal(5.0, 0.1, n).astype(np.float32), type=pa.float32()),
        'BIRMS': pa.array(rng.normal(5.0, 0.1, n).astype(np.float32), type=pa.float32()),
        'CIRMS': pa.array(rng.normal(5.0, 0.1, n).astype(np.float32), type=pa.float32()),
        'NIRMS': pa.array(rng.normal(0.2, 0.01, n).astype(np.float32), type=pa.float32()),
        'AWATT': pa.array(rng.normal(600.0, 10.0, n).astype(np.float32), type=pa.float32()),
        'BWATT': pa.array(rng.normal(600.0, 10.0, n).astype(np.float32), type=pa.float32()),
        'CWATT': pa.array(rng.normal(600.0, 10.0, n).astype(np.float32), type=pa.float32()),
        'AFVRMS': pa.array(rng.normal(119.5, 0.4, n).astype(np.float32), type=pa.float32()),
        'BFVRMS': pa.array(rng.normal(119.5, 0.4, n).astype(np.float32), type=pa.float32()),
        'CFVRMS': pa.array(rng.normal(119.5, 0.4, n).astype(np.float32), type=pa.float32()),
    }

    table = pa.table(data)
    path = tmp_path / '20240623_0750.parquet'
    pq.write_table(table, path)
    return path


@pytest.fixture
def sample_cpow_parquet(tmp_path):
    """Create a CPOW Parquet file with int32 data and scaling metadata (~3200 rows = 100ms at 32kHz)."""
    n = 3200
    rng = np.random.default_rng(42)

    # Simulate int32 ADC counts for 3-phase voltage and current
    vscale = 0.0001
    iscale = 0.000005

    t = np.arange(n) / 32000.0
    freq = 60.0
    phase_offsets = [0, 2 * np.pi / 3, 4 * np.pi / 3]

    data = {}
    for i, ch in enumerate(['VA', 'VB', 'VC']):
        signal = np.sin(2 * np.pi * freq * t + phase_offsets[i]) * (120.0 * np.sqrt(2)) / vscale
        data[ch] = pa.array(signal.astype(np.int32), type=pa.int32())

    for i, ch in enumerate(['IA', 'IB', 'IC']):
        signal = np.sin(2 * np.pi * freq * t + phase_offsets[i] - 0.3) * (5.0 * np.sqrt(2)) / iscale
        data[ch] = pa.array(signal.astype(np.int32), type=pa.int32())

    # Neutral current (smaller)
    data['IN'] = pa.array((rng.normal(0, 0.05, n) / iscale).astype(np.int32), type=pa.int32())

    table = pa.table(data)

    # Write with metadata
    metadata = {
        b'vscale': str(vscale).encode(),
        b'iscale': str(iscale).encode(),
        b'start_time': b'2025-06-23T07:50:56.662282101Z',
    }
    existing_meta = table.schema.metadata or {}
    existing_meta.update(metadata)
    table = table.replace_schema_metadata(existing_meta)

    path = tmp_path / '20250623_075056.parquet'
    pq.write_table(table, path)
    return path


@pytest.fixture
def sample_cpow_float_parquet(tmp_path):
    """Create a CPOW Parquet file with float32 data (legacy format, no scale metadata)."""
    n = 3200
    t = np.arange(n) / 32000.0
    freq = 60.0
    phase_offsets = [0, 2 * np.pi / 3, 4 * np.pi / 3]

    data = {}
    for i, ch in enumerate(['VA', 'VB', 'VC']):
        signal = np.sin(2 * np.pi * freq * t + phase_offsets[i]) * (120.0 * np.sqrt(2))
        data[ch] = pa.array(signal.astype(np.float32), type=pa.float32())

    for i, ch in enumerate(['IA', 'IB', 'IC']):
        signal = np.sin(2 * np.pi * freq * t + phase_offsets[i] - 0.3) * (5.0 * np.sqrt(2))
        data[ch] = pa.array(signal.astype(np.float32), type=pa.float32())

    data['IN'] = pa.array(np.random.default_rng(42).normal(0, 0.05, n).astype(np.float32),
                          type=pa.float32())

    table = pa.table(data)
    path = tmp_path / '20250623_075056_float.parquet'
    pq.write_table(table, path)
    return path


@pytest.fixture
def sample_config_yaml(tmp_path):
    """Create a minimal YAML config file."""
    config = {
        'sensor': {
            'address': '10.0.0.50',
            'port': 1535,
            'phases': 3,
        },
        'pmon': {
            'connection': {
                'port': 1535,
                'retry_delay': 5,
            },
            'parquet': {
                'interval': 3600,
                'compression': {
                    'method': 'ZSTD',
                    'level': 3,
                },
            },
        },
    }
    path = tmp_path / 'equser.yaml'
    with open(path, 'w') as f:
        yaml.dump(config, f)
    return path
