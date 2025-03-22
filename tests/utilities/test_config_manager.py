# Copyright (C) 2025 Fyn-Runner Authors
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
#  see <https://www.gnu.org/licenses/>.

# pylint: disable=protected-access,pointless-statement,unspecified-encoding

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from pydantic import BaseModel, Field

from fyn_runner.utilities.config_manager import ConfigManager


# Test model for configuration
class ConfigModel(BaseModel):
    """Simple pydantic config."""
    test_string: str = "default_value"
    test_int: int = 42
    test_list: list = Field(default_factory=list)
    nested: dict = Field(default_factory=dict)


class TestConfigManager:
    """Test suite for ConfigManager utility."""

    @pytest.fixture
    def valid_config_file(self):
        """Fixture that creates a temporary valid config file."""
        config_data = {
            "test_string": "test_value",
            "test_int": 100,
            "test_list": [1, 2, 3],
            "nested": {"key": "value"}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            yaml.dump(config_data, temp_file)
            temp_path = temp_file.name

        yield temp_path

        os.unlink(temp_path)

    @pytest.fixture
    def invalid_yaml_file(self):
        """Fixture that creates a temporary invalid YAML file."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_file.write(b"invalid: yaml: content: [")
            temp_path = temp_file.name

        yield temp_path

        os.unlink(temp_path)

    @pytest.fixture
    def config_manager(self, valid_config_file):
        """Fixture that creates a ConfigManager with a valid config file."""
        return ConfigManager(valid_config_file, ConfigModel)

    def test_load_valid_config(self, config_manager):
        """Test loading a valid configuration file."""
        config = config_manager.load()

        assert config.test_string == "test_value"
        assert config.test_int == 100
        assert config.test_list == [1, 2, 3]
        assert config.nested == {"key": "value"}
        assert config_manager._config is not None
        assert config_manager.test_string == "test_value"

    def test_load_missing_file(self):
        """Test loading a non-existent configuration file."""
        non_existent_path = Path("/non/existent/path/config.yaml")
        config_manager = ConfigManager(non_existent_path, ConfigModel)

        with pytest.raises(FileNotFoundError):
            config_manager.load()

    def test_load_invalid_yaml(self, invalid_yaml_file):
        """Test loading an invalid YAML file."""
        config_manager = ConfigManager(invalid_yaml_file, ConfigModel)

        with pytest.raises(yaml.YAMLError):
            config_manager.load()

    def test_getattr_before_load(self, config_manager):
        """Test attribute access before loading configuration."""
        with pytest.raises(ValueError, match="No configuration loaded"):
            assert config_manager.test_string == "expected_value"

    def test_getattr_after_load(self, config_manager):
        """Test attribute access after loading configuration."""
        config_manager.load()
        assert config_manager.test_string == "test_value"
        assert config_manager.test_int == 100

    def test_config_property(self, config_manager):
        """Test the config property."""
        with pytest.raises(ValueError, match="No configuration loaded"):
            config_manager.config

        config_manager.load()
        assert config_manager.config.test_string == "test_value"
        assert isinstance(config_manager.config, ConfigModel)

    def test_save_config(self, config_manager, tmp_path):
        """Test saving configuration to a file."""
        config_manager.load()
        config_manager._config.test_string = "new_value"
        config_manager._config.test_int = 200

        new_path = tmp_path / "new_config.yaml"
        config_manager.config_path = new_path
        config_manager.save()

        with open(new_path, 'r', encoding='utf-8') as f:
            saved_data = yaml.safe_load(f)

        assert saved_data["test_string"] == "new_value"
        assert saved_data["test_int"] == 200

    def test_save_without_load(self, config_manager):
        """Test saving without loading first."""
        with pytest.raises(ValueError, match="No configuration loaded"):
            config_manager.save()

    def test_attach_logger(self, config_manager):
        """Test attaching a logger."""
        mock_logger = MagicMock()
        config_manager.attach_logger(mock_logger)
        assert config_manager.logger == mock_logger

    def test_model_validation(self, tmp_path):
        """Test that Pydantic validation works."""

        invalid_config = {
            "test_string": "valid",
            "test_int": "not_an_integer"  # String instead of integer
        }

        config_path = tmp_path / "invalid_type.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config, f)

        config_manager = ConfigManager(config_path, ConfigModel)

        with pytest.raises(ValueError):
            config_manager.load()

    def test_default_values(self, tmp_path):
        """Test that default values are used for missing fields."""

        partial_config = {
            "test_string": "only_string_provided"
        }

        config_path = tmp_path / "partial.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(partial_config, f)

        config_manager = ConfigManager(config_path, ConfigModel)
        config = config_manager.load()

        assert config.test_string == "only_string_provided"
        assert config.test_int == 42
        assert config.test_list == []
        assert config.nested == {}
