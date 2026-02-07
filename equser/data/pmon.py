"""Power monitor (PMon) data loading.

Loads RMS power quality summary data from Parquet files produced by the
EQ Wave sensor's power monitor subsystem.
"""

from pathlib import Path
from typing import Dict, Union

import pyarrow as pa
import pyarrow.parquet as pq

# Re-export from dataops so users can access via equser.data
from equser.pmon.dataops import FIELD_DESCRIPTIONS

__all__ = ['FIELD_DESCRIPTIONS', 'load_pmon']


def load_pmon(file_path: Union[str, Path]) -> pa.Table:
    """Load a PMon Parquet file as a PyArrow Table.

    PMon files contain 10/12-cycle RMS measurements: voltage, current, power,
    frequency, and fundamental components for each phase.  The measurement
    interval is 10 cycles for 50 Hz grids and 12 cycles for 60 Hz grids
    (~200 ms).

    Args:
        file_path: Path to a PMon Parquet file.

    Returns:
        PyArrow Table with columns like time_us, FREQ, AVRMS, AIRMS, etc.
    """
    return pq.read_table(file_path)
