class DataAcquisitionError(RuntimeError):
    """Base class for data acquisition errors."""


class SensorConnectionError(DataAcquisitionError, OSError):
    """Connection-related errors."""


class ConfigurationError(DataAcquisitionError, ValueError):
    """Configuration-related errors."""
