# Copyright (C) 2025 Bevan W.S. Jones
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not,
# see <https://www.gnu.org/licenses/>.

# pylint: disable=redefined-outer-name
from pathlib import Path

import pytest
from fyn_runner.config import (
    Settings,
    State,
    LocalCache,
    APISettings,
    load,
    save,
)


@pytest.fixture
def temp_config_path(tmp_path):
    """Fixture providing a temporary file path."""
    return tmp_path / "config.yaml"


@pytest.fixture
def sample_settings():
    """Fixture providing sample settings."""
    return Settings(
        debug=True,
        state=State.Active,
        local_cache=LocalCache(directory=Path("/tmp/cache")),
        api_settings=APISettings(
            port=8080, runner_id="test-runner", end_points={"status": "/status"}
        ),
    )


def test_default_settings():
    """Test default settings creation."""
    settings = Settings()
    assert settings.debug is False
    assert settings.state == State.Unknown
    assert settings.local_cache.directory is None
    assert settings.api_settings.port == 443


def test_save_and_load(temp_config_path, sample_settings):
    """Test saving and loading settings."""

    save(sample_settings, temp_config_path)
    loaded = load(temp_config_path)

    # Verify all values
    assert loaded.debug == sample_settings.debug
    assert loaded.state == sample_settings.state
    assert loaded.local_cache.directory == sample_settings.local_cache.directory
    assert loaded.api_settings.port == sample_settings.api_settings.port
    assert loaded.api_settings.runner_id == sample_settings.api_settings.runner_id
    assert loaded.api_settings.end_points == sample_settings.api_settings.end_points


def test_load_nonexistent_file(temp_config_path):
    """Test loading from a nonexistent file returns defaults."""
    settings = load(temp_config_path)
    assert settings.debug is False
    assert settings.state == State.Unknown
    assert settings.local_cache.directory is None


def test_load_empty_file(temp_config_path):
    """Test loading from an empty file returns defaults."""
    temp_config_path.write_text("")
    settings = load(temp_config_path)
    assert settings.debug is False
    assert settings.state == State.Unknown


def test_custom_settings(temp_config_path):
    """Test saving and loading with custom values."""
    settings = Settings(
        debug=True,
        state=State.StartUp,
        local_cache=LocalCache(directory=Path("/custom/path")),
        api_settings=APISettings(
            port=9000, runner_id="custom-runner", end_points={"health": "/health"}
        ),
    )

    save(settings, temp_config_path)
    loaded = load(temp_config_path)

    assert loaded.debug
    assert loaded.state == State.StartUp
    assert loaded.local_cache.directory == Path("/custom/path")
    assert loaded.api_settings.port == 9000


def test_partial_settings(temp_config_path):
    """Test loading partial settings preserves defaults for unspecified values."""
    partial_yaml = """
    debug: true
    api_settings:
        port: 9000
    """
    temp_config_path.write_text(partial_yaml)

    settings = load(temp_config_path)
    assert settings.debug
    assert settings.api_settings.port == 9000
    assert settings.state == State.Unknown  # Default preserved
    assert (
        settings.api_settings.base_url == "https:api.fyn-tech.com"
    )  # Default preserved
