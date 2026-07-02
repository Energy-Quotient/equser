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
"""Default neutral-CT sensitivity ratio.

The neutral CT is more sensitive than the phase CTs, so the same current-scale
factor (counts to amps for the phase CTs) over-reads the neutral channel by this
ratio. A file may override it via a ``neutral_ct_ratio`` metadata key (see
:func:`get_cpow_scales`)."""


def get_cpow_scales(
    table: pa.Table, metadata: dict[bytes, bytes] | None
) -> tuple[float, float, float]:
    """Return the voltage, phase-current, and neutral-current scale factors.

    This is the single source of truth for CPOW channel scaling, shared by
    :func:`load_cpow_scaled` and the plotters so both apply identical scaling.

    - **int32 files**: ``vscale``/``iscale`` come from the producer metadata
      (defaulting to 1.0 if absent). The neutral scale is ``iscale`` divided by
      the neutral-CT ratio, which defaults to :data:`NEUTRAL_CT_RATIO` but is
      overridden by a ``neutral_ct_ratio`` metadata key when the file carries one.
    - **float files** (legacy, pre-scaled): all three factors are 1.0.

    Args:
        table: The CPOW PyArrow Table (used to detect int vs. float channels).
        metadata: The Arrow **schema** metadata dict (bytes keys). Producer files
            carry scaling here, not in the Parquet footer.

    Returns:
        ``(vscale, iscale, neutral_iscale)`` as floats.
    """
    if not pa.types.is_integer(table['VA'].type):
        return 1.0, 1.0, 1.0

    meta = metadata or {}
    vscale = float(meta[b'vscale'].decode()) if b'vscale' in meta else 1.0
    iscale = float(meta[b'iscale'].decode()) if b'iscale' in meta else 1.0

    divisor = float(NEUTRAL_CT_RATIO)
    if b'neutral_ct_ratio' in meta:
        try:
            divisor = float(meta[b'neutral_ct_ratio'].decode())
        except (ValueError, AttributeError):
            pass

    return vscale, iscale, iscale / divisor


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
        - ``IA``, ``IB``, ``IC``: scaled phase-current arrays (numpy float64)
        - ``IN``: scaled neutral-current array (numpy float64). The neutral CT is
          more sensitive than the phase CTs, so ``IN`` is scaled by ``iscale``
          divided by the neutral-CT ratio (see :func:`get_cpow_scales`).
        - ``vscale``, ``iscale``: phase scaling factors applied (1.0 for float files)
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
    # Producer metadata is carried on the Arrow schema, not the Parquet footer.
    meta = pf.schema_arrow.metadata or {}

    # Channel scale factors (shared with the plotters via get_cpow_scales).
    vscale, iscale, neutral_iscale = get_cpow_scales(table, meta)

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
        'IN': table['IN'].to_numpy(zero_copy_only=False).astype(np.float64) * neutral_iscale,
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
