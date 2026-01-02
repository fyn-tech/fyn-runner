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


import os
import psutil
import subprocess

def add_subparser_args(sub_parser):
    sub_parser.add_argument('action',
        choices=['start', 'stop', 'status'],
        help="Service action to perform")
    
    
def service(args, unknown_args):
    match args.action:
        case 'start':
            start(args, unknown_args)
        case 'stop':
            if unknown_args is not None:
                print(f"Unknown args parsed: {unknown_args}")
            stop()
        case 'status':
            if unknown_args is not None:
                print(f"Unknown args parsed: {unknown_args}")
            status()
        case _:
            print(f"Error: unknown service action '{args.action}'")


def start(args, unknown_args):

    
    print(args)
    proc = find_runner_process()
    if not proc:
        try:
            subprocess.Popen(
                ['fyn-runner', 'run'] + (unknown_args or ()),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Detach from parent
            )
            print(f"Daemon service started.")
        except Exception as e:
            print(f"Failed to start Daemon service: {e}")
    else:
        print("Daemon service is already running")
        

def stop():
    proc = find_runner_process()
    if proc:
        proc.terminate() 
        proc.wait(timeout=5) 
    else:
        print("Daemon service is not running")


def status():
    """Show daemon status."""
    proc = find_runner_process()    
    if proc:
        print(f"Daemon is running (PID: {proc.pid})")
        print(f"  Uptime: {proc.create_time()}")
        print(f"  CPU: {proc.cpu_percent()}%")
        print(f"  Memory: {proc.memory_info().rss / 1024 / 1024:.1f} MB")
    else:
        print("Daemon service is not running")


def find_runner_process():
    """Find running fyn-runner process."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            # Check if this is our runner process
            if cmdline and 'fyn_runner' in ' '.join(cmdline) and 'run' in cmdline:
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None
