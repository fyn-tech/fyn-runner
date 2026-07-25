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

from unittest.mock import MagicMock, PropertyMock, patch

import psutil

from fyn_runner.command_line_interface import service


class TestServiceDispatch:
    """Test suite for the `service` subcommand action dispatch."""

    def test_dispatches_start(self):
        """action='start' must delegate to start(args, unknown_args)."""
        args = MagicMock(action='start')
        with patch.object(service, 'start') as start_fn:
            service.service(args, ['--foo'])

        start_fn.assert_called_once_with(args, ['--foo'])

    def test_dispatches_stop(self):
        """action='stop' must delegate to stop()."""
        args = MagicMock(action='stop')
        with patch.object(service, 'stop') as stop_fn:
            service.service(args, None)

        stop_fn.assert_called_once_with()

    def test_dispatches_status(self):
        """action='status' must delegate to status()."""
        args = MagicMock(action='status')
        with patch.object(service, 'status') as status_fn:
            service.service(args, None)

        status_fn.assert_called_once_with()

    def test_stop_warns_on_unknown_args(self, capsys):
        """Unrecognised extra args passed to stop/status must be surfaced to the user."""
        args = MagicMock(action='stop')
        with patch.object(service, 'stop'):
            service.service(args, ['--bogus'])

        assert "Unknown args parsed" in capsys.readouterr().out

    def test_unknown_action_prints_error(self, capsys):
        """An action outside {start, stop, status} must report an error, not crash."""
        args = MagicMock(action='bogus')

        service.service(args, None)

        assert "unknown service action" in capsys.readouterr().out


class TestStart:
    """Test suite for `start` (launching the daemon)."""

    def test_launches_when_not_already_running(self):
        """Extra CLI args must be forwarded through to the spawned `fyn-runner run`."""
        with (patch.object(service, 'find_runner_process', return_value=None),
              patch.object(service.subprocess, 'Popen') as mock_popen):
            service.start(MagicMock(), ['--config', 'a.yaml'])

        mock_popen.assert_called_once_with(
            ['fyn-runner', 'run', '--config', 'a.yaml'],
            stdout=service.subprocess.DEVNULL,
            stderr=service.subprocess.DEVNULL,
            start_new_session=True,
        )

    def test_launches_with_no_unknown_args(self):
        """unknown_args=None must not blow up building the Popen command list."""
        with (patch.object(service, 'find_runner_process', return_value=None),
              patch.object(service.subprocess, 'Popen') as mock_popen):
            service.start(MagicMock(), None)

        mock_popen.assert_called_once_with(
            ['fyn-runner', 'run'],
            stdout=service.subprocess.DEVNULL,
            stderr=service.subprocess.DEVNULL,
            start_new_session=True,
        )

    def test_skips_launch_when_already_running(self, capsys):
        """A second `start` while the daemon is already up must be a no-op."""
        with (patch.object(service, 'find_runner_process', return_value=MagicMock()),
              patch.object(service.subprocess, 'Popen') as mock_popen):
            service.start(MagicMock(), None)

        mock_popen.assert_not_called()
        assert "already running" in capsys.readouterr().out

    def test_reports_failure_without_raising(self, capsys):
        """A failure to spawn the daemon must be reported, not propagated."""
        with (patch.object(service, 'find_runner_process', return_value=None),
              patch.object(service.subprocess, 'Popen', side_effect=OSError('no such file'))):
            service.start(MagicMock(), None)

        assert "Failed to start Daemon service" in capsys.readouterr().out


class TestStop:
    """Test suite for `stop` (terminating the daemon)."""

    def test_terminates_running_process(self):
        """A running daemon must be terminated and waited on."""
        proc = MagicMock()
        with patch.object(service, 'find_runner_process', return_value=proc):
            service.stop()

        proc.terminate.assert_called_once()
        proc.wait.assert_called_once_with(timeout=5)

    def test_reports_when_not_running(self, capsys):
        """Stopping when nothing is running must be reported, not raise."""
        with patch.object(service, 'find_runner_process', return_value=None):
            service.stop()

        assert "not running" in capsys.readouterr().out


class TestStatus:
    """Test suite for `status` (reporting daemon state)."""

    def test_reports_running_process_details(self, capsys):
        """Status output must include pid, CPU and memory usage of the running daemon."""
        proc = MagicMock()
        proc.pid = 4242
        proc.create_time.return_value = 1700000000.0
        proc.cpu_percent.return_value = 3.5
        proc.memory_info.return_value.rss = 100 * 1024 * 1024

        with patch.object(service, 'find_runner_process', return_value=proc):
            service.status()

        out = capsys.readouterr().out
        assert "4242" in out
        assert "3.5" in out
        assert "100.0 MB" in out

    def test_reports_when_not_running(self, capsys):
        """Status must report absence cleanly when the daemon isn't running."""
        with patch.object(service, 'find_runner_process', return_value=None):
            service.status()

        assert "not running" in capsys.readouterr().out


class TestFindRunnerProcess:
    """Test suite for the psutil-based process lookup."""

    def _make_proc(self, cmdline):
        proc = MagicMock()
        proc.info = {'pid': 1, 'name': 'python', 'cmdline': cmdline}
        return proc

    def test_finds_matching_process(self):
        """The runner daemon's own process must be found among unrelated ones."""
        target = self._make_proc(['python', '-m', 'fyn_runner.main', 'run'])
        other = self._make_proc(['python', '-m', 'some_other_tool'])

        with patch.object(service.psutil, 'process_iter', return_value=[other, target]):
            found = service.find_runner_process()

        assert found is target

    def test_returns_none_when_no_process_matches(self):
        """No fyn_runner process running must resolve to None, not raise."""
        other = self._make_proc(['python', '-m', 'some_other_tool'])

        with patch.object(service.psutil, 'process_iter', return_value=[other]):
            found = service.find_runner_process()

        assert found is None

    def test_ignores_cmdline_without_run_argument(self):
        """`fyn_runner` alone isn't enough - a bare `install`/`service` invocation must not
        match, only one that is actually running the daemon (`run`)."""
        installer = self._make_proc(['python', '-m', 'fyn_runner.main', 'install'])

        with patch.object(service.psutil, 'process_iter', return_value=[installer]):
            found = service.find_runner_process()

        assert found is None

    def test_skips_processes_that_vanish_during_iteration(self):
        """A process that disappears mid-scan must be skipped, not abort the search."""
        vanished = MagicMock()
        type(vanished).info = PropertyMock(side_effect=psutil.NoSuchProcess(pid=1))
        target = self._make_proc(['python', '-m', 'fyn_runner.main', 'run'])

        with patch.object(service.psutil, 'process_iter', return_value=[vanished, target]):
            found = service.find_runner_process()

        assert found is target

    def test_skips_processes_with_denied_access(self):
        """A process we lack permission to inspect must be skipped, not abort the search."""
        denied = MagicMock()
        type(denied).info = PropertyMock(side_effect=psutil.AccessDenied(pid=1))

        with patch.object(service.psutil, 'process_iter', return_value=[denied]):
            found = service.find_runner_process()

        assert found is None
