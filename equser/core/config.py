"""Configuration loading for equser.

Provides configuration loading from YAML files with sensible defaults.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from equser.core.paths import get_config_path
from equser.utils.logging import get_logger

logger = get_logger(__name__)


# Default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    'sensor': {
        'address': '192.168.10.10',
        'port': 1535,
        'phases': 3,
    },
    'pmon': {
        'connection': {
            'port': 1535,
            'retry_delay': 3,
            'num_retries': -1,
            'connect_timeout': 5,
            'data_timeout': 0.6,
        },
        'parquet': {
            'interval': 86400,
            'flush_every': -1,
            'compression': {
                'method': 'ZSTD',
                'level': 4,
            },
        },
    },
    'data': {
        'directory': None,  # Uses PATHS.data if not specified
        'format': 'parquet',
    },
}


def load_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Load configuration from a YAML file.

    Resolution order:
    1. Specified config_path
    2. Default YAML file resolution (env var, XDG paths, etc.)

    Args:
        config_path: Path to config file. If None, uses default file resolution.

    Returns:
        Configuration dictionary with defaults applied for missing values.

    Raises:
        FileNotFoundError: If specified config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    config = DEFAULT_CONFIG.copy()

    if config_path is None:
        config_path = get_config_path()
    else:
        config_path = Path(config_path)

    if config_path.exists():
        logger.debug(f"Loading configuration from {config_path}")
        with open(config_path, 'r') as f:
            file_config = yaml.safe_load(f) or {}

        # Deep merge file config into defaults
        config = _deep_merge(config, file_config)
    else:
        logger.debug(f"Config file not found at {config_path}, using defaults")

    return config


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries.

    Args:
        base: Base dictionary (modified in place)
        override: Dictionary with values to override

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_sensor_address(config: Optional[Dict[str, Any]] = None) -> str:
    """Get sensor IP address from config.

    Args:
        config: Configuration dictionary. If None, loads from file.

    Returns:
        Sensor IP address string
    """
    if config is None:
        config = load_config()

    # Support both 'address' and legacy 'ip_address' keys
    sensor = config.get('sensor', {})
    return sensor.get('address') or sensor.get('ip_address', '192.168.10.10')
