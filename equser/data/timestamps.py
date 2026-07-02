"""Timestamp parsing utilities for EQ Wave data files.

Handles ISO 8601 timestamps with nanosecond precision (from CPOW metadata)
and filename-based timestamps (YYYYMMDD_HHMM format).
"""

import re
from datetime import datetime


def parse_start_time(start_time_str: str) -> datetime:
    """Parse an ISO 8601 timestamp into a Python datetime.

    Handles formats like ``2025-06-23T07:50:56.662282101Z``. Python datetime
    only supports microsecond resolution, so nanoseconds are truncated.

    Args:
        start_time_str: ISO 8601 timestamp string, optionally with 'Z' suffix.

    Returns:
        Parsed datetime object (naive, UTC assumed).
    """
    if start_time_str.endswith('Z'):
        start_time_str = start_time_str[:-1]

    # Split at the decimal point to handle nanoseconds
    if '.' in start_time_str:
        date_part, frac_part = start_time_str.split('.')
        # Truncate to 6 digits (microseconds) for Python datetime
        frac_part = frac_part[:6].ljust(6, '0')
        return datetime.strptime(f"{date_part}.{frac_part}", '%Y-%m-%dT%H:%M:%S.%f')

    # No fractional-seconds component (e.g. 2025-06-23T07:50:56)
    return datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S')


_FILENAME_RE = re.compile(r'(\d{8})_(\d{6}|\d{4})')


def parse_filename_timestamp(filename: str) -> datetime | None:
    """Parse a timestamp from a data filename.

    Supports the YYYYMMDD_HHMM format used by PMon files and the
    YYYYMMDD_HHMMSS format used by CPOW files.

    Args:
        filename: Filename or full path (only the stem is examined).

    Returns:
        Parsed datetime, or None if the filename doesn't match.

    Examples::

        >>> parse_filename_timestamp('20250623_0750.parquet')
        datetime.datetime(2025, 6, 23, 7, 50)
        >>> parse_filename_timestamp('20250623_075056.parquet')
        datetime.datetime(2025, 6, 23, 7, 50, 56)
        >>> parse_filename_timestamp('readme.txt') is None
        True
    """
    # Extract just the stem if a full path is given
    from pathlib import Path

    stem = Path(filename).stem

    match = _FILENAME_RE.match(stem)
    if not match:
        return None

    date_part = match.group(1)
    time_part = match.group(2)

    try:
        year = int(date_part[:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
        hour = int(time_part[:2])
        minute = int(time_part[2:4])
        second = int(time_part[4:6]) if len(time_part) >= 6 else 0
        return datetime(year, month, day, hour, minute, second)
    except (ValueError, IndexError):
        return None
