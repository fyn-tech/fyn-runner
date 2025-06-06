# Copyright (C) 2025 fyn-api Authors
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

import argparse
from pathlib import Path
from pydantic import BaseModel, Field
import sys
import time
import yaml


class Config(BaseModel):
    """Configuration for the test program."""
    sleep_time: int = Field(
        description="The seconds the program must sleep for.")
    exit_code: int = Field(
        description="The exit code the program must print")

def main():
    """Runner entry point."""

    parser = argparse.ArgumentParser(
        prog='test_program',
        description="A small test application to test remote runner tracking.")
    parser.add_argument(
        '-i',
        '--input',
        type=str,
        help="The path to the input yaml file")
    args = parser.parse_args()


    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {input_path}")

    print(f"Reading input file: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)

    print("Processing parsed configuration.")
    config = Config(**config_dict)

    print(f"Entering sleep for {config.sleep_time}s.")
    time.sleep(config.sleep_time)

    print(f"Exiting with code {config.exit_code}.")
    sys.exit(config.exit_code)


if __name__ == "__main__":
    main()
