class DataAcquisitionError(RuntimeError):
    """Base class for data acquisition errors."""
    pass

class ConnectionError(DataAcquisitionError, OSError):
    """Connection-related errors."""
    pass

class ConfigurationError(DataAcquisitionError, ValueError):
    """Configuration-related errors."""
    pass
