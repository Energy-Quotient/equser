"""Logging configuration for equser.

Provides simple logging without requiring colorlog dependency.
Falls back gracefully if colorlog is not installed.
"""

import logging
import logging.config

_configured = False

# Attach a NullHandler to the top-level package logger so that merely importing
# equser never configures logging or reconfigures the host application's root
# logger. Applications (including the equser CLI) opt in explicitly by calling
# configure_logging().
logging.getLogger("equser").addHandler(logging.NullHandler())


def configure_logging(level: str = 'INFO', use_color: bool = True) -> None:
    """Configure logging with customizable level and optional color support.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_color: Whether to use colored output (requires colorlog)
    """
    global _configured

    # Check if colorlog is available
    has_colorlog = False
    if use_color:
        try:
            import colorlog  # noqa: F401

            has_colorlog = True
        except ImportError:
            pass

    if has_colorlog and use_color:
        formatter_config = {
            'format': '[%(asctime)s] %(log_color)s[%(levelname)s] [%(module)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
            '()': 'colorlog.ColoredFormatter',
            'log_colors': {
                'DEBUG': 'bold_white',
                'INFO': 'white',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            },
        }
    else:
        formatter_config = {
            'format': '[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        }

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'root': {'level': level, 'handlers': ['console']},
        'formatters': {'default': formatter_config},
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': level,
                'formatter': 'default',
                'stream': 'ext://sys.stdout',
            }
        },
        'loggers': {'numexpr': {'level': 'WARNING'}},
    }
    logging.config.dictConfig(logging_config)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    This does not configure logging (that would mutate the host application's
    root logger as a side effect of import). Call :func:`configure_logging`
    from your application entry point to enable console output.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
