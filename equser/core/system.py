"""System utilities for equser."""

import sys

# Common OSError descriptions for network operations
OSERROR_DESCRIPTIONS = {
    113: "No route to host - Check if sensor is powered on",
    111: "Connection refused - Check if sensor service is running",
    110: "Connection timed out",
    103: "Connection aborted by sensor",
    115: "Operation in progress",
    114: "Operation already in progress",
    104: "Connection reset by peer",
    32: "Broken pipe",
}


def format_oserror(e: OSError) -> str:
    """Format an OSError with type, errno, and description.

    Args:
        e: The OSError to format

    Returns:
        Formatted error string including error type, number, and description
    """
    errno = getattr(e, 'errno', None)
    description = OSERROR_DESCRIPTIONS.get(errno, f"OSError {errno}")
    return f"{type(e).__name__} (errno={errno} - {description})"


def exit_with_error(msg: str, code: int = 1) -> None:
    """Exit with an error message.

    Args:
        msg: Error message to write to stderr
        code: Exit code (default 1)
    """
    sys.stderr.write(msg + "\n")
    sys.exit(code)
