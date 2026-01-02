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
import sys

import fyn_runner.command_line_interface.install as install
import fyn_runner.command_line_interface.run as run
import fyn_runner.command_line_interface.service as service

def main():
    """Runner entry point."""

    parser = argparse.ArgumentParser(
        prog='fyn_runner',
        description="Application to execute simulations and interact with the local and remote "
        "fyn-tech infrastructure.")
    subparsers = parser.add_subparsers(dest='command')
    install.add_subparser_args(subparsers.add_parser("install", help="Interactive runner setup"))
    run.add_subparser_args(subparsers.add_parser("run", help="Runs the runner daemon"))
    service.add_subparser_args(subparsers.add_parser("service", help="Manage the runner service (start/stop/status)"))

    args, unknown_args = parser.parse_known_args()

    match args.command:
        case 'install':
            install.install(args, unknown_args)
        case 'run':
            run.run(args, unknown_args)
        case 'service':
            service.service(args, unknown_args)
        case _:
            print(f"Error: unknown command '{args.command}'")
            parser.print_help()

if __name__ == "__main__":
    main()
