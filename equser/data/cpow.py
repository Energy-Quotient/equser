"""CPOW (Continuous Point-on-Wave) data loading.

Loads high-resolution waveform data from Parquet files produced by EQ Wave
sensors. Handles both int32 (raw ADC counts with scaling metadata) and
float32 (legacy pre-scaled) formats automatically.
"""

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from equser.data.timestamps import parse_start_time

SAMPLE_RATE_HZ = 32_000
"""Sample rate in Hz for CPOW data."""

CHANNELS = ['VA', 'VB', 'VC', 'IA', 'IB', 'IC', 'IN']
"""Standard CPOW channel names: three-phase voltage, current, and neutral."""

NEUTRAL_CT_RATIO = 30
"""Neutral CT is 30x more sensitive than phase CTs in recent installations."""


def load_cpow(file_path: str | Path) -> pa.Table:
    """Load a CPOW Parquet file as a raw PyArrow Table.

    No scaling is applied. For scaled voltage/current arrays, use
    :func:`load_cpow_scaled` instead.

    Args:
        file_path: Path to a CPOW Parquet file.

    Returns:
        PyArrow Table with columns VA, VB, VC, IA, IB, IC, IN.
    """
    return pq.read_table(file_path)


def load_cpow_scaled(file_path: str | Path) -> dict[str, Any]:
    """Load a CPOW Parquet file and return scaled voltage/current arrays.

    Handles both data formats:

    - **int32** (current): raw ADC counts scaled by ``vscale``/``iscale``
      from the Parquet user metadata.
    - **float** (legacy pre-scaled): values are already in V/A; no
      scaling metadata is present.

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

    result: dict[str, Any] = {
        'table': table,
        'VA': table['VA'].to_numpy() * vscale,
        'VB': table['VB'].to_numpy() * vscale,
        'VC': table['VC'].to_numpy() * vscale,
        'IA': table['IA'].to_numpy() * iscale,
        'IB': table['IB'].to_numpy() * iscale,
        'IC': table['IC'].to_numpy() * iscale,
        'IN': table['IN'].to_numpy() * iscale,
        'vscale': vscale,
        'iscale': iscale,
        'sample_rate': SAMPLE_RATE_HZ,
    }

    # Parse start_time from metadata if present
    if b'start_time' in meta:
        result['start_time'] = parse_start_time(meta[b'start_time'].decode('utf-8'))
    else:
        result['start_time'] = None

    return result
