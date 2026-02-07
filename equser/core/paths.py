"""Path configuration for equser.

Provides configurable paths via environment variables with sensible defaults.
Follows XDG Base Directory Specification where applicable.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


def get_xdg_config_home() -> Path:
    """Get XDG config home directory."""
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))


def get_xdg_data_home() -> Path:
    """Get XDG data home directory."""
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))


def get_config_path() -> Path:
    """Get the configuration file path.

    Resolution order:
    1. EQUSER_CONFIG environment variable (explicit path)
    2. ./equser.yaml (current directory)
    3. ~/.config/equser/config.yaml (XDG user config)
    4. /etc/equser/config.yaml (system config)

    Returns:
        Path to the first existing config file, or XDG path if none exist
    """
    # 1. Explicit environment variable
    if config_env := os.environ.get('EQUSER_CONFIG'):
        return Path(config_env)

    # 2. Current directory
    local_config = Path('./equser.yaml')
    if local_config.exists():
        return local_config

    # 3. XDG user config
    xdg_config = get_xdg_config_home() / 'equser' / 'config.yaml'
    if xdg_config.exists():
        return xdg_config

    # 4. System config
    system_config = Path('/etc/equser/config.yaml')
    if system_config.exists():
        return system_config

    # Default to XDG location (may not exist yet)
    return xdg_config


def get_data_dir() -> Path:
    """Get the data directory.

    Resolution order:
    1. EQUSER_DATA_DIR environment variable
    2. /var/lib/eq-synapse/data (system deployment, if exists)
    3. ~/.local/share/equser (XDG data home)

    Returns:
        Path to the data directory
    """
    if data_env := os.environ.get('EQUSER_DATA_DIR'):
        return Path(data_env)

    # System deployment path (used by eq-synapse service)
    system_data = Path('/var/lib/eq-synapse/data')
    if system_data.exists():
        return system_data

    return get_xdg_data_home() / 'equser'


@dataclass
class EquserPaths:
    """Paths configuration for equser.

    Attributes:
        data: Base data directory
        pmon_data: Power monitor data directory
        cpow_data: Continuous point-on-wave data directory
        config_file: Path to configuration file
    """

    data: Path = field(default_factory=get_data_dir)
    config_file: Path = field(default_factory=get_config_path)

    def __post_init__(self):
        """Initialize derived paths."""
        self._pmon_data: Path | None = None
        self._cpow_data: Path | None = None

    @property
    def pmon_data(self) -> Path:
        """Power monitor data directory."""
        if self._pmon_data is None:
            self._pmon_data = self.data / 'pmon'
        return self._pmon_data

    @property
    def cpow_data(self) -> Path:
        """Continuous point-on-wave data directory."""
        if self._cpow_data is None:
            self._cpow_data = self.data / 'cpow'
        return self._cpow_data

    def ensure_data_dirs(self) -> None:
        """Create data directories if they don't exist."""
        self.data.mkdir(parents=True, exist_ok=True)
        self.pmon_data.mkdir(parents=True, exist_ok=True)
        self.cpow_data.mkdir(parents=True, exist_ok=True)


# Default paths instance
PATHS = EquserPaths()
