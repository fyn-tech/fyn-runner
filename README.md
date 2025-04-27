# fyn-runner
A runner for collecting hardware specs and executing CFD simulations on local or remote systems.

## Overview

The fyn-runner is a critical component of the Fyn-Tech ecosystem, designed to serve as the execution layer for CFD simulations.
It communicates with the fyn-api backend to manage simulation jobs, report system capabilities, and handle simulation data transfer.

Key responsibilities include:
- Collecting and reporting system hardware information
- Managing the execution environment for simulations
- Communicating with the fyn-api regarding job status
- Organising and synchronising simulation files
- Providing secure authentication with the Fyn-Tech backend

> **Note:** This project is in early development stages, and many components are still evolving.

## System Requirements

The fyn-runner is designed with cross-platform compatibility in mind, supporting:
- Windows
- Linux
- macOS

## Usage

```bash
python -m fyn_runner.main -c /path/to/config.yaml
```
The current configuration options for the `.yaml` can be found in `fyn_runner/config.py`.

## Architecture

The runner follows a modular design pattern with several key components:

- **Server Proxy**: Handles communication with the fyn-api backend
- **File Manager**: Organises simulation input/output and synchronises with cloud storage
- **System Integration**: Collects hardware information and manages runner installation

Additional components under development:
- Job Manager
- Simulation Monitor

Further documentation can be found in the `/doc` folder, where `primary_design.md` contains the high-level architecture design.

## Testing strategy

Most of the tests in this library will be written by AI, or at least it's requested that LLMs generate the initial boilerplate for the unit tests.
The organisation should still be maintained within the test files and structures.
Further, generated tests should still be checked for coverage and correctness (acting as a code review for tests).
See the `/doc/test_prompt.md` document, which can be used for prompting the LLM when generating unit tests;
This document also contains the specific guidelines regarding `fixtures`, `mocking`, what needs testing, and whether to combine or separate tests.

## Project Context

The fyn-runner is part of the larger Fyn-Tech ecosystem, which aims to build a cloud-based CFD solver with a browser-based frontend.
Find further details [here](https://github.com/fyn-tech)

## License

This project is licensed under the GNU General Public License v3 - see the LICENSE.md file for details.
