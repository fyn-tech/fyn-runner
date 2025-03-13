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


import yaml
from pathlib import Path
from typing import Dict
from dataclasses import asdict, dataclass, field
from enum import Enum


@dataclass
class APISettings:
    base_url: str = "https:api.fyn-tech.com"
    port: int = 443
    runner_id: str = None
    runner_token: str = None
    end_points: Dict = None
    heartbeat_period: int = 60
    max_retries: int = 60


@dataclass
class LocalCache:
    directory: Path = None


class State(Enum):
    Unknown = 0
    StartUp = 1
    Active = 2
    Shutdown = 3


@dataclass
class Settings:
    debug: bool = False
    state: State = State.Unknown

    local_cache: LocalCache = field(default_factory=LocalCache)
    api_settings: APISettings = field(default_factory=APISettings)


def load(config_path: str | Path) -> Settings:
    """Load settings from a YAML file."""

    path = Path(config_path)

    if not path.exists():
        return Settings()

    with path.open("r") as f:
        yaml_data = yaml.safe_load(f)

    if yaml_data is None:
        return Settings()

    if "state" in yaml_data:
        yaml_data["state"] = State[yaml_data["state"]]

    if "local_cache" in yaml_data:
        if yaml_data["local_cache"].get("directory"):
            yaml_data["local_cache"]["directory"] = Path(
                yaml_data["local_cache"]["directory"]
            )
        yaml_data["local_cache"] = LocalCache(**yaml_data["local_cache"])
    if "api_settings" in yaml_data:
        yaml_data["api_settings"] = APISettings(**yaml_data["api_settings"])

    return Settings(**yaml_data)


def save(settings: Settings, config_path: str | Path) -> None:
    """Save settings to a YAML file."""
    path = Path(config_path)

    settings_dict = asdict(settings)
    settings_dict["state"] = settings.state.name

    if settings.local_cache.directory:
        settings_dict["local_cache"]["directory"] = str(settings.local_cache.directory)

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w") as f:
        yaml.safe_dump(settings_dict, f, default_flow_style=False)
