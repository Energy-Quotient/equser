"""Extended datetime class with division operations.

Based on https://gist.github.com/treyhunner/6218526
"""

import datetime as dt


class DateTime(dt.datetime):
    """Extended datetime class with additional division operations.

    This class extends the standard datetime.datetime to add support for
    division operations, which are useful for time-based calculations and
    file rotation logic.

    Example:
        >>> from datetime import timedelta
        >>> now = DateTime.now()
        >>> interval = timedelta(hours=1)
        >>> aligned = now // interval  # Floor to nearest hour
    """

    def __divmod__(self, delta: dt.timedelta) -> tuple[dt.datetime, dt.timedelta]:
        """Implement divmod operation for datetime division.

        Args:
            delta: The timedelta to divide by

        Returns:
            tuple: (quotient datetime, remainder timedelta)
        """
        seconds = int((self - dt.datetime.min).total_seconds())
        remainder = dt.timedelta(
            seconds=seconds % delta.total_seconds(),
            microseconds=self.microsecond,
        )
        quotient = self - remainder
        return quotient, remainder

    def __floordiv__(self, delta: dt.timedelta) -> dt.datetime:
        """Implement floor division for datetime.

        Args:
            delta: The timedelta to divide by

        Returns:
            DateTime: The floor division result
        """
        return divmod(self, delta)[0]

    def __mod__(self, delta: dt.timedelta) -> dt.timedelta:
        """Implement modulo operation for datetime.

        Args:
            delta: The timedelta to divide by

        Returns:
            timedelta: The remainder
        """
        return divmod(self, delta)[1]
