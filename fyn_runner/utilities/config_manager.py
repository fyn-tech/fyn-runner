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
from pydantic import BaseModel, ValidationError, create_model
from pydantic_core import PydanticUndefined
from typing import Generic, Optional, Type, TypeVar
import yaml

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
            yaml.safe_dump(self._config.model_dump(mode='json'), f, default_flow_style=False)

    def generate_interactively(self, use_defaults, add_help_text):
        """
            TODO: FIXME
        """
        config_dict = generate_recursive("runner_config_root", self.model_cls, use_defaults, add_help_text)
        self._config = self.model_cls(**config_dict)


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


def generate_recursive(field_name, field_info, skip_default, add_help_text, level = 0):
    print(f"{field_name}")
    config_dict = {}
    for sub_field_name, sub_field_info in field_info.model_fields.items():
        if isinstance(sub_field_info.annotation, type) and issubclass(sub_field_info.annotation, BaseModel):
            config_dict[sub_field_name] = generate_recursive(sub_field_name, sub_field_info.annotation, skip_default, add_help_text, level+1) 
        else:
            config_dict[sub_field_name] = prompt_setting(sub_field_name, sub_field_info, skip_default, add_help_text, level+1)
    
    return config_dict
        
def prompt_setting(field_name, field_info, use_defaults, add_help_text, level):
    
    has_default_value = field_info.default is not PydanticUndefined 
    has_default_factory = field_info.default_factory is not None
    has_default = has_default_value or has_default_factory
    while True:
        try:
            user_input = None

            if not (has_default and use_defaults):
                prompt_text = (
                    f"{'  '*level}{field_name}\n{'  '*level}Description: {field_info.description}"
                    f"\n{'  '*level}Enter value{' (leave blank for default)' if has_default else ''}:"
                    if add_help_text else 
                    f"{'  '*level}Enter {field_name}"
                    f"{' (leave blank for default)' if has_default else ""}:"
                )

                user_input = input(prompt_text).strip()

            if has_default and (user_input is None or len(user_input) == 0):
                user_input = field_info.default if has_default_value else field_info.default_factory()

            TempModel = create_model('TempModel', **{field_name: (field_info.annotation, field_info)})
            validated = TempModel(**{field_name: user_input})
            return getattr(validated, field_name)
        except ValidationError as e:
            print(f"Failed to validate input: {e}")
    
