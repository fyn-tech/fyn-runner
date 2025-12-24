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

import appdirs

# Default constants (fallback values)
APP_NAME = "fyn_tech_runner"
APP_AUTHOR = "fyn_tech"
APP_DISPLAY_NAME = "Fyn Runner"
__version__ = "dev"

# Try to override from package metadata
try:
    from importlib.metadata import metadata, version
    
    __version__ = version("fyn-runner")
    meta = metadata("fyn-runner")
    if author_meta := meta.get("Author"):
        APP_AUTHOR = author_meta
        
except Exception:
    # Metadata not available leave defaults
    pass

DEFAULT_WORK_DIRECTORY = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)