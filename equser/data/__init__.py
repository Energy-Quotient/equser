"""Data loading utilities for EQ Wave power quality data.

Provides functions for loading CPOW (continuous point-on-wave) and PMon
(power monitoring) data from Parquet files, plus timestamp parsing helpers.

All functions use only base dependencies (numpy, pyarrow).

Usage::

    from equser.data import load_cpow_scaled, load_pmon

    # Load scaled CPOW waveform data
    result = load_cpow_scaled('20250623_075056.parquet')
    print(result['VA'][:10])  # First 10 voltage samples

    # Load power monitor data
    table = load_pmon('20250623_0750.parquet')
    print(table.column_names)
"""

from equser.data.cpow import (
    CHANNELS,
    NEUTRAL_CT_RATIO,
    SAMPLE_RATE_HZ,
    load_cpow,
    load_cpow_scaled,
)
from equser.data.pmon import (
    FIELD_DESCRIPTIONS,
    load_pmon,
)
from equser.data.timestamps import (
    parse_filename_timestamp,
    parse_start_time,
)

__all__ = [
    'CHANNELS',
    'FIELD_DESCRIPTIONS',
    'NEUTRAL_CT_RATIO',
    'SAMPLE_RATE_HZ',
    'load_cpow',
    'load_cpow_scaled',
    'load_pmon',
    'parse_filename_timestamp',
    'parse_start_time',
]
