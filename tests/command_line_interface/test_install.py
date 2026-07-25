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

# pylint: disable=protected-access

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fyn_runner.command_line_interface import install


class TestInstall:
    """Test suite for the interactive `install` command."""

    @pytest.fixture
    def args(self):
        """Parsed CLI args for a non-interactive-defaults install."""
        args = MagicMock()
        args.use_defaults = False
        args.description = False
        return args

    @pytest.fixture
    def mocks(self):
        """Patches every collaborator `install()` reaches out to, wired up for the happy path."""
        with (patch.object(install, 'ConfigManager') as config_manager_cls,
              patch.object(install, 'FileManager') as file_manager_cls,
              patch.object(install, 'create_logger') as create_logger_fn,
              patch.object(install, 'ServerProxy') as server_proxy_cls,
              patch('builtins.input') as mock_input):

            config = MagicMock()
            config.file_manager.model_dump.return_value = {
                'working_directory': Path('/fake/work'),
                'simulation_directory': Path('simulations'),
            }
            config.logging.model_dump.return_value = {'level': 'INFO'}
            config_manager_cls.return_value = config

            file_manager = MagicMock()
            file_manager.config_dir = Path('/fake/work/config')
            file_manager.log_dir = Path('/fake/work/logs')
            file_manager_cls.return_value = file_manager

            logger = MagicMock()
            create_logger_fn.return_value = logger

            server_proxy = MagicMock()
            server_proxy.id = 'runner-id-123'
            server_proxy.token = 'initial-token-abc'
            runner_api = MagicMock()
            server_proxy.create_runner_manager_api.return_value = runner_api
            server_proxy_cls.return_value = server_proxy

            runner_info = MagicMock()
            runner_info.name = 'registered-name'
            runner_info.token = 'permanent-token'
            runner_api.runner_manager_runner_register_create.return_value = runner_info

            mock_input.side_effect = ['my-runner', 'n']

            yield {
                'input': mock_input,
                'ConfigManager': config_manager_cls,
                'config': config,
                'FileManager': file_manager_cls,
                'file_manager': file_manager,
                'create_logger': create_logger_fn,
                'ServerProxy': server_proxy_cls,
                'server_proxy': server_proxy,
                'runner_api': runner_api,
                'runner_info': runner_info,
            }

    def test_install_happy_path_declines_autostart(self, args, mocks, capsys):
        """Full success path: config generated, directories created, runner registered, config
        saved, and auto-start skipped because the user declined."""
        with patch.object(install, 'setup_auto_start') as setup_auto_start:
            install.install(args, None)

        mocks['ConfigManager'].assert_called_once_with(
            Path('./my-runner.yaml'), install.RunnerConfig)
        mocks['config'].generate_interactively.assert_called_once_with(
            args.use_defaults, args.description)

        mocks['FileManager'].assert_called_once_with(
            working_directory=Path('/fake/work'), simulation_directory=Path('simulations'))
        mocks['file_manager'].init_directories.assert_called_once_with(False, True)
        assert mocks['config'].config_path == Path('/fake/work/config/my-runner.yaml')

        mocks['ServerProxy'].assert_called_once_with(
            mocks['create_logger'].return_value,
            mocks['file_manager'],
            mocks['config'].server_proxy,
            False)

        request = mocks['runner_api'].runner_manager_runner_register_create.call_args.args[0]
        assert request.id == 'runner-id-123'
        assert request.token == 'initial-token-abc'

        assert mocks['config']._config.server_proxy.name == 'registered-name'
        assert mocks['config']._config.server_proxy.token == 'permanent-token'
        mocks['config'].save.assert_called_once()
        mocks['file_manager'].create_default_config_path_file.assert_called_once_with(
            mocks['config'].config_path)

        setup_auto_start.assert_not_called()
        assert "Setup completed successfully." in capsys.readouterr().out

    def test_install_accepts_autostart(self, args, mocks):
        """Answering 'y' to the startup prompt must trigger auto-start setup."""
        mocks['input'].side_effect = ['my-runner', 'y']

        with patch.object(install, 'setup_auto_start') as setup_auto_start:
            install.install(args, None)

        setup_auto_start.assert_called_once()

    def test_install_aborts_if_name_input_fails(self, args, mocks):
        """A failure reading the runner name must abort before any side effects."""
        mocks['input'].side_effect = EOFError()

        with pytest.raises(SystemExit) as exc_info:
            install.install(args, None)

        assert exc_info.value.code == 1
        mocks['ConfigManager'].assert_not_called()

    def test_install_aborts_and_does_not_register_when_directory_setup_fails(self, args, mocks):
        """A directory setup failure must abort before attempting registration."""
        mocks['file_manager'].init_directories.side_effect = OSError('disk full')

        with pytest.raises(SystemExit) as exc_info:
            install.install(args, None)

        assert exc_info.value.code == 1
        mocks['ServerProxy'].assert_not_called()

    def test_install_aborts_and_cleans_up_when_registration_fails(self, args, mocks):
        """A registration failure must roll back the directories it already created."""
        mocks['runner_api'].runner_manager_runner_register_create.side_effect = \
            Exception('network error')

        with pytest.raises(SystemExit) as exc_info:
            install.install(args, None)

        assert exc_info.value.code == 1
        mocks['file_manager'].remove_directories.assert_called_once()
        mocks['config'].save.assert_not_called()

    def test_install_completes_even_if_autostart_setup_fails(self, args, mocks, capsys):
        """Auto-start failures are non-fatal - install must still report success."""
        mocks['input'].side_effect = ['my-runner', 'y']

        with patch.object(install, 'setup_auto_start', side_effect=Exception('no systemd')):
            install.install(args, None)

        out = capsys.readouterr().out
        assert "Warning: Could not enable auto-start" in out
        assert "Setup completed successfully." in out


class TestUninstall:
    """Test suite for the interactive `uninstall` command."""

    @pytest.fixture
    def args(self):
        """Parsed CLI args for uninstall (currently unused by the command itself)."""
        return MagicMock()

    @pytest.fixture
    def mocks(self):
        """Patches every collaborator `uninstall()` reaches out to, wired up for the happy path."""
        with (patch.object(install, 'ConfigManager') as config_manager_cls,
              patch.object(install, 'FileManager') as file_manager_cls,
              patch.object(install, 'create_logger'),
              patch.object(install, 'ServerProxy') as server_proxy_cls,
              patch.object(install, 'remove_auto_start') as remove_auto_start_fn,
              patch('builtins.input') as mock_input):

            config = MagicMock()
            config.file_manager.model_dump.return_value = {}
            config.logging.model_dump.return_value = {}
            config_manager_cls.return_value = config

            file_manager = MagicMock()
            file_manager_cls.return_value = file_manager

            server_proxy = MagicMock()
            server_proxy.id = 'runner-id-123'
            runner_api = MagicMock()
            server_proxy.create_runner_manager_api.return_value = runner_api
            server_proxy_cls.return_value = server_proxy

            mock_input.side_effect = ['', 'my-runner']

            yield {
                'input': mock_input,
                'ConfigManager': config_manager_cls,
                'FileManager': file_manager_cls,
                'file_manager': file_manager,
                'ServerProxy': server_proxy_cls,
                'server_proxy': server_proxy,
                'runner_api': runner_api,
                'remove_auto_start': remove_auto_start_fn,
            }

    def test_uninstall_happy_path(self, args, mocks, capsys):
        """Full success path: deregister, remove directories, remove auto-start."""
        install.uninstall(args, None)

        mocks['runner_api'].runner_manager_runner_destroy.assert_called_once_with('runner-id-123')
        mocks['file_manager'].remove_directories.assert_called_once_with(None)
        mocks['file_manager'].delete_default_config_path_file.assert_called_once()
        mocks['remove_auto_start'].assert_called_once()
        assert "Uninstall completed successfully." in capsys.readouterr().out

    def test_uninstall_passes_through_simulation_directory_choice(self, args, mocks):
        """Whatever the user types at the simulation-directory prompt is passed through
        verbatim - the code does not parse it as a yes/no answer."""
        mocks['input'].side_effect = ['y', 'my-runner']

        install.uninstall(args, None)

        mocks['file_manager'].remove_directories.assert_called_once_with('y')

    def test_uninstall_aborts_if_name_input_fails(self, args, mocks):
        """A failure reading the runner name must abort before any side effects."""
        mocks['input'].side_effect = ['', EOFError()]

        with pytest.raises(SystemExit) as exc_info:
            install.uninstall(args, None)

        assert exc_info.value.code == 1
        mocks['ConfigManager'].assert_not_called()

    def test_uninstall_continues_when_deregistration_fails(self, args, mocks, capsys):
        """Server-side deregistration failing must not block local cleanup."""
        mocks['runner_api'].runner_manager_runner_destroy.side_effect = Exception('offline')

        install.uninstall(args, None)

        mocks['file_manager'].remove_directories.assert_called_once()
        mocks['remove_auto_start'].assert_called_once()
        assert "Uninstall completed successfully." in capsys.readouterr().out

    def test_uninstall_continues_when_directory_removal_fails(self, args, mocks, capsys):
        """Directory removal failing must not block auto-start removal."""
        mocks['file_manager'].remove_directories.side_effect = OSError('permission denied')

        install.uninstall(args, None)

        mocks['remove_auto_start'].assert_called_once()
        assert "Uninstall completed successfully." in capsys.readouterr().out

    def test_uninstall_continues_when_autostart_removal_fails(self, args, mocks, capsys):
        """Auto-start removal failing must still end in a reported success."""
        mocks['remove_auto_start'].side_effect = Exception('no systemd')

        install.uninstall(args, None)

        out = capsys.readouterr().out
        assert "Warning: Could not remove auto-start" in out
        assert "Uninstall completed successfully." in out


class TestAutoStartDispatch:
    """Test suite for the setup_auto_start / remove_auto_start platform dispatch."""

    @pytest.mark.parametrize('system_name, target', [
        ('Linux', '_setup_systemd_service'),
        ('Darwin', '_setup_launchd_service'),
        ('Windows', '_setup_windows_task'),
    ])
    def test_setup_auto_start_dispatches_by_platform(self, system_name, target):
        """setup_auto_start must delegate to the platform-specific helper."""
        with (patch.object(install.platform, 'system', return_value=system_name),
              patch.object(install, target) as target_fn):
            install.setup_auto_start()

        target_fn.assert_called_once()

    def test_setup_auto_start_unsupported_platform_raises(self):
        """An unrecognised platform must raise rather than silently do nothing."""
        with patch.object(install.platform, 'system', return_value='PlanNine'):
            with pytest.raises(Exception, match='Unsupported platform'):
                install.setup_auto_start()

    @pytest.mark.parametrize('system_name, target', [
        ('Linux', '_remove_systemd_service'),
        ('Darwin', '_remove_launchd_service'),
        ('Windows', '_remove_windows_task'),
    ])
    def test_remove_auto_start_dispatches_by_platform(self, system_name, target):
        """remove_auto_start must delegate to the platform-specific helper."""
        with (patch.object(install.platform, 'system', return_value=system_name),
              patch.object(install, target) as target_fn):
            install.remove_auto_start()

        target_fn.assert_called_once()

    def test_remove_auto_start_unsupported_platform_raises(self):
        """An unrecognised platform must raise rather than silently do nothing."""
        with patch.object(install.platform, 'system', return_value='PlanNine'):
            with pytest.raises(Exception, match='Unsupported platform'):
                install.remove_auto_start()


class TestSystemdService:
    """Test suite for the Linux systemd auto-start helpers."""

    def test_setup_writes_unit_file_and_enables_service(self, tmp_path):
        """Setup must write a unit file pointing at the resolved executable and enable it."""
        with (patch.object(install.shutil, 'which', return_value='/usr/bin/fyn-runner'),
              patch.object(install.Path, 'home', return_value=tmp_path),
              patch.object(install.subprocess, 'run') as mock_run):
            install._setup_systemd_service()

        service_file = tmp_path / '.config' / 'systemd' / 'user' / 'fyn-runner.service'
        assert service_file.exists()
        content = service_file.read_text()
        assert 'ExecStart=/usr/bin/fyn-runner service start' in content

        mock_run.assert_any_call(['systemctl', '--user', 'daemon-reload'], check=True)
        mock_run.assert_any_call(['systemctl', '--user', 'enable',
                                 'fyn-runner.service'], check=True)

    def test_setup_raises_if_executable_not_on_path(self, tmp_path):
        """Setup must refuse to write a unit file that points nowhere."""
        with (patch.object(install.shutil, 'which', return_value=None),
              patch.object(install.Path, 'home', return_value=tmp_path),
              patch.object(install.subprocess, 'run') as mock_run):
            with pytest.raises(Exception, match='not found in PATH'):
                install._setup_systemd_service()

        mock_run.assert_not_called()

    def test_remove_deletes_existing_unit_file(self, tmp_path):
        """Removal must stop/disable the service and delete its unit file."""
        service_dir = tmp_path / '.config' / 'systemd' / 'user'
        service_dir.mkdir(parents=True)
        service_file = service_dir / 'fyn-runner.service'
        service_file.write_text('placeholder')

        with (patch.object(install.Path, 'home', return_value=tmp_path),
              patch.object(install.subprocess, 'run') as mock_run):
            install._remove_systemd_service()

        assert not service_file.exists()
        mock_run.assert_any_call(
            ['systemctl', '--user', 'stop', 'fyn-runner.service'], check=False)
        mock_run.assert_any_call(
            ['systemctl', '--user', 'disable', 'fyn-runner.service'], check=False)

    def test_remove_is_a_noop_when_unit_file_missing(self, tmp_path):
        """Removal must not fail when there is no unit file left to delete."""
        with (patch.object(install.Path, 'home', return_value=tmp_path),
              patch.object(install.subprocess, 'run') as mock_run):
            install._remove_systemd_service()

        mock_run.assert_any_call(
            ['systemctl', '--user', 'stop', 'fyn-runner.service'], check=False)


class TestLaunchdService:
    """Test suite for the macOS launchd auto-start helpers."""

    def test_setup_writes_plist(self, tmp_path):
        """Setup must write a launch agent plist pointing at the resolved executable."""
        with (patch.object(install.shutil, 'which', return_value='/usr/local/bin/fyn-runner'),
              patch.object(install.Path, 'home', return_value=tmp_path)):
            install._setup_launchd_service()

        plist_file = tmp_path / 'Library' / 'LaunchAgents' / 'com.fynbos.fyn-runner.plist'
        assert plist_file.exists()
        content = plist_file.read_text()
        assert '<string>/usr/local/bin/fyn-runner</string>' in content
        assert '<string>service</string>' in content
        assert '<string>start</string>' in content

    def test_setup_raises_if_executable_not_on_path(self, tmp_path):
        """Setup must refuse to write a plist that points nowhere."""
        with (patch.object(install.shutil, 'which', return_value=None),
              patch.object(install.Path, 'home', return_value=tmp_path)):
            with pytest.raises(Exception, match='not found in PATH'):
                install._setup_launchd_service()

    def test_remove_unloads_and_deletes_existing_plist(self, tmp_path):
        """Removal must unload the agent and delete its plist file."""
        agents_dir = tmp_path / 'Library' / 'LaunchAgents'
        agents_dir.mkdir(parents=True)
        plist_file = agents_dir / 'com.fynbos.fyn-runner.plist'
        plist_file.write_text('placeholder')

        with (patch.object(install.Path, 'home', return_value=tmp_path),
              patch.object(install.subprocess, 'run') as mock_run):
            install._remove_launchd_service()

        mock_run.assert_called_once_with(['launchctl', 'unload', str(plist_file)], check=False)
        assert not plist_file.exists()

    def test_remove_skips_unload_when_plist_missing(self, tmp_path):
        """Removal must not attempt to unload a plist that was never written."""
        with (patch.object(install.Path, 'home', return_value=tmp_path),
              patch.object(install.subprocess, 'run') as mock_run):
            install._remove_launchd_service()

        mock_run.assert_not_called()


class TestWindowsTask:
    """Test suite for the Windows Task Scheduler auto-start helpers."""

    def test_setup_creates_scheduled_task(self):
        """Setup must create a logon task pointing at the resolved executable."""
        with (patch.object(install.shutil, 'which', return_value=r'C:\fyn-runner.exe'),
              patch.object(install.subprocess, 'run') as mock_run):
            install._setup_windows_task()

        mock_run.assert_called_once_with([
            "schtasks", "/create",
            "/tn", "FynRunner",
            "/tr", r'"C:\fyn-runner.exe" service start',
            "/sc", "onlogon",
            "/rl", "highest",
            "/f",
        ], check=True, shell=True)

    def test_setup_raises_if_executable_not_on_path(self):
        """Setup must refuse to create a task that points nowhere."""
        with (patch.object(install.shutil, 'which', return_value=None),
              patch.object(install.subprocess, 'run') as mock_run):
            with pytest.raises(Exception, match='not found in PATH'):
                install._setup_windows_task()

        mock_run.assert_not_called()

    def test_remove_deletes_scheduled_task(self):
        """Removal must delete the scheduled task by name."""
        with patch.object(install.subprocess, 'run') as mock_run:
            install._remove_windows_task()

        mock_run.assert_called_once_with(
            ["schtasks", "/delete", "/tn", "FynRunner", "/f"], check=False, shell=True)
