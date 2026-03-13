import unittest
from unittest.mock import patch

from agent import autostart


class WindowsAutostartTests(unittest.TestCase):
    @patch("agent.autostart._install_windows_startup_fallback")
    @patch("agent.autostart._install_windows_run_entry")
    @patch("agent.autostart._install_windows_task")
    @patch("agent.autostart._remove_windows_startup_fallback")
    @patch("agent.autostart._write_windows_helper")
    def test_install_uses_run_fallback_when_task_registration_fails(
        self,
        write_helper,
        remove_startup,
        install_task,
        install_run_entry,
        install_startup_fallback,
    ) -> None:
        install_task.return_value = False
        install_run_entry.return_value = True

        result = autostart._install_windows()

        self.assertTrue(result)
        write_helper.assert_called_once()
        remove_startup.assert_called_once()
        install_task.assert_called_once()
        install_run_entry.assert_called_once()
        install_startup_fallback.assert_not_called()

    @patch("agent.autostart._install_windows_startup_fallback")
    @patch("agent.autostart._install_windows_run_entry")
    @patch("agent.autostart._install_windows_task")
    @patch("agent.autostart._remove_windows_startup_fallback")
    @patch("agent.autostart._write_windows_helper")
    def test_install_uses_startup_fallback_when_task_and_run_fail(
        self,
        write_helper,
        remove_startup,
        install_task,
        install_run_entry,
        install_startup_fallback,
    ) -> None:
        install_task.return_value = False
        install_run_entry.return_value = False
        install_startup_fallback.return_value = True

        result = autostart._install_windows()

        self.assertTrue(result)
        install_task.assert_called_once()
        install_run_entry.assert_called_once()
        install_startup_fallback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
