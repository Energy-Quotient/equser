"""CPOW (Continuous Point-on-Wave) data loading.

Loads high-resolution waveform data from Parquet files produced by EQ Wave
sensors. Handles both v3 int32 (raw ADC counts with scaling metadata) and
legacy float32 (pre-scaled) formats automatically.
"""

from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from equser.data.timestamps import parse_start_time

SAMPLE_RATE_HZ = 32_000
"""Sample rate in Hz for CPOW data."""

CHANNELS = ['VA', 'VB', 'VC', 'IA', 'IB', 'IC', 'IN']
"""Standard CPOW channel names: three-phase voltage, current, and neutral."""

CYCLE_START_CHANNELS = ['cycle_start_a', 'cycle_start_b', 'cycle_start_c']
"""Optional v3 cycle-boundary marker columns (one per phase)."""

NEUTRAL_CT_RATIO = 30
"""Neutral CT is 30x more sensitive than phase CTs in recent installations."""


def load_cpow(file_path: str | Path) -> pa.Table:
    """Load a CPOW Parquet file as a raw PyArrow Table.

    No scaling is applied. For scaled voltage/current arrays, use
    :func:`load_cpow_scaled` instead.

    Args:
        file_path: Path to a CPOW Parquet file.

    Returns:
        PyArrow Table. v3 files include columns VA, VB, VC, IA, IB, IC, IN
        (INT32 raw ADC counts) and optionally cycle_start_a/b/c (nullable
        INT64 nanosecond timestamps marking phase cycle boundaries).
    """
    return pq.read_table(file_path)


def load_cpow_scaled(file_path: str | Path) -> dict[str, Any]:
    """Load a CPOW Parquet file and return scaled voltage/current arrays.

    Handles both data formats:

    - **v3 int32** (current): raw ADC counts scaled by ``vscale``/``iscale``
      from the Parquet schema metadata. Topology and neutral-connection status
      are read from metadata to indicate which channels carry live data.
    - **float** (legacy pre-scaled): values are already in V/A; no scaling
      metadata is present.

    Args:
        file_path: Path to a CPOW Parquet file.

    Returns:
        dict with keys:

        - ``table``: the raw PyArrow Table
        - ``VA``, ``VB``, ``VC``: scaled voltage arrays (numpy float64)
        - ``IA``, ``IB``, ``IC``, ``IN``: scaled current arrays (numpy float64)
        - ``vscale``, ``iscale``: scaling factors applied (1.0 for float files)
        - ``start_time``: parsed datetime from metadata, or None
        - ``sample_rate``: sample rate in Hz (SAMPLE_RATE_HZ constant)
        - ``schema_version``: integer schema version (3 for current files), or None
        - ``topology``: one of ``"three_phase"``, ``"split_phase"``,
          ``"single_phase"``, or None if not in metadata. Indicates which
          voltage channels carry live waveform data vs. reconstructed/zero-filled
          values.
        - ``neutral_connected``: True if the neutral CT is installed and IN
          contains live current data; False if IN is zero-filled; None if
          not recorded in metadata.
        - ``cycle_start_a``, ``cycle_start_b``, ``cycle_start_c``: numpy
          int64 arrays marking phase-locked cycle boundaries (nanoseconds since
          epoch). Present only when the file contains these columns. Zero means
          no cycle boundary at that sample; non-zero values are the ns-epoch
          timestamp of the detected boundary.
    """
    pf = pq.ParquetFile(file_path)
    table = pf.read()
    meta = pf.metadata.metadata or {}

    # Determine if scaling is needed by checking column dtype
    is_int = pa.types.is_integer(table['VA'].type)

    if is_int:
        vscale = float(meta[b'vscale'].decode()) if b'vscale' in meta else 1.0
        iscale = float(meta[b'iscale'].decode()) if b'iscale' in meta else 1.0
    else:
        vscale = 1.0
        iscale = 1.0

    # v3 schema metadata
    schema_version: int | None = None
    if b'schema_version' in meta:
        try:
            schema_version = int(meta[b'schema_version'].decode())
        except ValueError:
            pass

    topology: str | None = None
    if b'topology' in meta:
        topology = meta[b'topology'].decode()

    neutral_connected: bool | None = None
    if b'neutral_connected' in meta:
        neutral_connected = meta[b'neutral_connected'].decode().lower() == 'true'

    result: dict[str, Any] = {
        'table': table,
        'VA': table['VA'].to_numpy(zero_copy_only=False).astype(np.float64) * vscale,
        'VB': table['VB'].to_numpy(zero_copy_only=False).astype(np.float64) * vscale,
        'VC': table['VC'].to_numpy(zero_copy_only=False).astype(np.float64) * vscale,
        'IA': table['IA'].to_numpy(zero_copy_only=False).astype(np.float64) * iscale,
        'IB': table['IB'].to_numpy(zero_copy_only=False).astype(np.float64) * iscale,
        'IC': table['IC'].to_numpy(zero_copy_only=False).astype(np.float64) * iscale,
        'IN': table['IN'].to_numpy(zero_copy_only=False).astype(np.float64) * iscale,
        'vscale': vscale,
        'iscale': iscale,
        'sample_rate': SAMPLE_RATE_HZ,
        'schema_version': schema_version,
        'topology': topology,
        'neutral_connected': neutral_connected,
    }

    # Parse start_time from metadata if present
    if b'start_time' in meta:
        result['start_time'] = parse_start_time(meta[b'start_time'].decode('utf-8'))
    else:
        result['start_time'] = None

    # v3 optional cycle-boundary marker columns
    for col in CYCLE_START_CHANNELS:
        if col in table.column_names:
            pa_col = table[col]
            result[col] = pa_col.fill_null(0).to_numpy(zero_copy_only=False)

    return result
