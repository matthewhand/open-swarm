import platform
import subprocess
import threading


def send_notification(title: str, message: str):
    system = platform.system()
    if system == "Linux":
        subprocess.Popen(["notify-send", title, message])
    elif system == "Darwin":
        script = f'display notification "{message}" with title "{title}"'
        subprocess.Popen(["osascript", "-e", script])
    else:
        # No-op for unsupported OS
        pass

class Notifier:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def notify(self, title: str, message: str):
        if self.enabled:
            send_notification(title, message)

    def notify_delayed(self, title: str, message: str, delay: float = 30.0):
        def delayed():
            threading.Event().wait(delay)
            self.notify(title, message)
        threading.Thread(target=delayed, daemon=True).start()
