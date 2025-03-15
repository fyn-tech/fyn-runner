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

from pathlib import Path
from typing import Generic, Optional, Type, TypeVar

import yaml
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class ConfigManager(Generic[T]):
    """
    Manages an injected pydantic configuration (typically derived from the BaseModel). This manager
    effectively wraps the configuration, from which loading and saving to disk is possible along
    with general retrieval.

    The generic type T must be a subclass of BaseModel.
    """

    def __init__(self, config_file_path: Path, model_cls: Type[T]):
        """
        Initialize with the path to the configuration file and model class.

        Args:
            config_file_path: Path to the configuration file
            model_cls: Pydantic model class to use for this configuration
        """

        self.config_path = Path(config_file_path)
        self.model_cls = model_cls
        self._config: Optional[T] = None
        self.logger = None

    def __getattr__(self, name):
        """
        Forwards attribute access to the underlying configuration object.

        Raises:
            ValueError: If no configuration has been loaded yet
        """

        if self._config is None:
            raise ValueError("No configuration loaded")
        return getattr(self._config, name)

    def attach_logger(self, logger):
        """
        Attaches a logger to the configuration manager.
        """
        self.logger = logger

    def load(self) -> T:
        """Load the configuration from file."""

        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)

        self._config = self.model_cls(**config_dict)
        return self._config

    def save(self):
        """
        Save the current configuration to file in YAML format.

        Raises:
            ValueError: If no configuration has been loaded yet
        """
        if self._config is None:
            raise ValueError("No configuration loaded")

        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config.model_dump(), f)

    @property
    def config(self) -> T:
        """
        Returns the complete configuration object.

        Returns:
            T: The loaded configuration

        Raises:
            ValueError: If no configuration has been loaded yet
        """
        if self._config is None:
            raise ValueError("No configuration loaded")

        return self._config
