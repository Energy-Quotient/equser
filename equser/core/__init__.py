"""Core configuration and paths for equser."""

from equser.core.config import load_config
from equser.core.paths import PATHS, get_config_path, get_data_dir

__all__ = ['PATHS', 'get_data_dir', 'get_config_path', 'load_config']
