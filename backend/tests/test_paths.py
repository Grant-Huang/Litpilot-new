"""Tests for app.config.paths — data_dir / config_dir resolution."""
import os
from pathlib import Path
from unittest.mock import patch


def test_default_data_dir():
    from app.config.paths import data_dir
    os.environ.pop("LITPILOT_DATA_DIR", None)
    result = data_dir()
    assert isinstance(result, Path)
    assert result.name == "data"


def test_default_config_dir():
    from app.config.paths import config_dir
    os.environ.pop("LITPILOT_CONFIG_DIR", None)
    result = config_dir()
    assert isinstance(result, Path)
    assert result.name == "config"


def test_env_override_data_dir(tmp_path):
    from app.config.paths import data_dir
    override = str(tmp_path / "my_data")
    with patch.dict(os.environ, {"LITPILOT_DATA_DIR": override}):
        result = data_dir()
    assert result == Path(override).resolve()


def test_env_override_config_dir(tmp_path):
    from app.config.paths import config_dir
    override = str(tmp_path / "my_config")
    with patch.dict(os.environ, {"LITPILOT_CONFIG_DIR": override}):
        result = config_dir()
    assert result == Path(override).resolve()


def test_ensure_dir_creates(tmp_path):
    from app.config.paths import ensure_dir
    target = tmp_path / "nested" / "sub"
    assert not target.exists()
    ensure_dir(target)
    assert target.is_dir()
    ensure_dir(target)
