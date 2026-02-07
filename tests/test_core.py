"""Tests for equser.core modules (paths, config, system)."""

import os
from pathlib import Path

import pytest
import yaml

from equser.core.paths import get_config_path, get_data_dir, EquserPaths
from equser.core.config import load_config, _deep_merge, get_sensor_address, DEFAULT_CONFIG
from equser.core.system import format_oserror, OSERROR_DESCRIPTIONS


# --- paths ---

class TestGetConfigPath:
    def test_env_var_override(self, tmp_path, monkeypatch):
        config_file = tmp_path / 'custom.yaml'
        config_file.touch()
        monkeypatch.setenv('EQUSER_CONFIG', str(config_file))
        assert get_config_path() == config_file

    def test_local_config(self, tmp_path, monkeypatch):
        monkeypatch.delenv('EQUSER_CONFIG', raising=False)
        monkeypatch.chdir(tmp_path)
        local = tmp_path / 'equser.yaml'
        local.touch()
        assert get_config_path() == Path('./equser.yaml')

    def test_xdg_fallback(self, tmp_path, monkeypatch):
        monkeypatch.delenv('EQUSER_CONFIG', raising=False)
        monkeypatch.chdir(tmp_path)
        xdg = tmp_path / 'xdg_config'
        monkeypatch.setenv('XDG_CONFIG_HOME', str(xdg))
        # No file exists, should return XDG default
        result = get_config_path()
        assert 'equser' in str(result)
        assert 'config.yaml' in str(result)


class TestGetDataDir:
    def test_env_var_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv('EQUSER_DATA_DIR', str(tmp_path))
        assert get_data_dir() == tmp_path

    def test_xdg_fallback(self, tmp_path, monkeypatch):
        monkeypatch.delenv('EQUSER_DATA_DIR', raising=False)
        # System path probably doesn't exist in test env
        xdg = tmp_path / 'xdg_data'
        monkeypatch.setenv('XDG_DATA_HOME', str(xdg))
        result = get_data_dir()
        assert 'equser' in str(result)


class TestEquserPaths:
    def test_pmon_data_subdir(self, tmp_path, monkeypatch):
        monkeypatch.setenv('EQUSER_DATA_DIR', str(tmp_path))
        paths = EquserPaths()
        assert paths.pmon_data == tmp_path / 'pmon'

    def test_cpow_data_subdir(self, tmp_path, monkeypatch):
        monkeypatch.setenv('EQUSER_DATA_DIR', str(tmp_path))
        paths = EquserPaths()
        assert paths.cpow_data == tmp_path / 'cpow'

    def test_ensure_data_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setenv('EQUSER_DATA_DIR', str(tmp_path / 'newdata'))
        paths = EquserPaths()
        paths.ensure_data_dirs()
        assert paths.data.exists()
        assert paths.pmon_data.exists()
        assert paths.cpow_data.exists()


# --- config ---

class TestDeepMerge:
    def test_flat_override(self):
        base = {'a': 1, 'b': 2}
        override = {'b': 3, 'c': 4}
        result = _deep_merge(base, override)
        assert result == {'a': 1, 'b': 3, 'c': 4}

    def test_nested_merge(self):
        base = {'a': {'x': 1, 'y': 2}, 'b': 3}
        override = {'a': {'y': 99, 'z': 100}}
        result = _deep_merge(base, override)
        assert result == {'a': {'x': 1, 'y': 99, 'z': 100}, 'b': 3}

    def test_base_unmodified(self):
        base = {'a': 1}
        override = {'a': 2}
        _deep_merge(base, override)
        assert base == {'a': 1}


class TestLoadConfig:
    def test_load_yaml(self, sample_config_yaml):
        config = load_config(sample_config_yaml)
        assert config['sensor']['address'] == '10.0.0.50'
        # Check deep merge preserved defaults
        assert config['pmon']['connection']['connect_timeout'] == 5

    def test_defaults_when_no_file(self, tmp_path):
        missing = tmp_path / 'nonexistent.yaml'
        config = load_config(missing)
        assert config['sensor']['address'] == '192.168.10.10'

    def test_get_sensor_address(self, sample_config_yaml):
        config = load_config(sample_config_yaml)
        assert get_sensor_address(config) == '10.0.0.50'

    def test_get_sensor_address_default(self):
        assert get_sensor_address({'sensor': {}}) == '192.168.10.10'

    def test_get_sensor_address_legacy(self):
        assert get_sensor_address({'sensor': {'ip_address': '1.2.3.4'}}) == '1.2.3.4'


# --- system ---

class TestFormatOserror:
    def test_known_errno(self):
        e = OSError(111, "Connection refused")
        e.errno = 111
        result = format_oserror(e)
        assert '111' in result
        assert 'Connection refused' in result

    def test_unknown_errno(self):
        e = OSError(999, "Unknown error")
        e.errno = 999
        result = format_oserror(e)
        assert '999' in result

    def test_no_errno(self):
        e = OSError("generic")
        result = format_oserror(e)
        assert 'None' in result
