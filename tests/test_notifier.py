import sys
import platform
import types
import pytest
from unittest import mock
from swarm.blueprints.common.notifier import Notifier, send_notification

def test_send_notification_linux():
    with mock.patch("subprocess.Popen") as popen_mock:
        with mock.patch("platform.system", return_value="Linux"):
            send_notification("Title", "Message")
            popen_mock.assert_called_once()
            args = popen_mock.call_args[0][0]
            assert args[0] == "notify-send"
            assert "Title" in args and "Message" in args

def test_send_notification_mac():
    with mock.patch("subprocess.Popen") as popen_mock:
        with mock.patch("platform.system", return_value="Darwin"):
            send_notification("Title", "Message")
            popen_mock.assert_called_once()
            args = popen_mock.call_args[0][0]
            assert args[0] == "osascript"
            assert "-e" in args
            assert "Title" in args[-1] and "Message" in args[-1]

def test_notifier_notify():
    n = Notifier(enabled=True)
    with mock.patch("subprocess.Popen") as popen_mock:
        with mock.patch("platform.system", return_value="Linux"):
            n.notify("Title", "Body")
            popen_mock.assert_called_once()

def test_notifier_notify_disabled():
    n = Notifier(enabled=False)
    with mock.patch("subprocess.Popen") as popen_mock:
        n.notify("Title", "Body")
        popen_mock.assert_not_called()

def test_notifier_notify_delayed(monkeypatch):
    n = Notifier(enabled=True)
    with mock.patch("subprocess.Popen") as popen_mock:
        with mock.patch("platform.system", return_value="Linux"):
            # Patch threading.Event.wait to call immediately
            monkeypatch.setattr("threading.Event.wait", lambda self, t=None: None)
            n.notify_delayed("Title", "Body", delay=0.01)
            import time
            time.sleep(0.05)
            popen_mock.assert_called_once()
