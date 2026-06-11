import argparse
import atexit
import ctypes
import os
import sys

_MUTEX_HANDLE = None
_MUTEX_NAME = "Global\\StealthLuma.SingleInstance.v1"
_WINDOW_TITLE = "Stealth Luma"


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--lang", choices=["fr", "en"])
    parser.add_argument("--install-dir")
    return parser.parse_known_args()[0]


def _activate_existing_window():
    if sys.platform != "win32":
        return
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, _WINDOW_TITLE)
    if not hwnd:
        return
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)


def acquire_single_instance():
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return True
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, True, _MUTEX_NAME)
    if kernel32.GetLastError() == 183:
        kernel32.CloseHandle(handle)
        _activate_existing_window()
        return False
    _MUTEX_HANDLE = handle
    return True


args = parse_args()
if args.setup:
    from core import run_install_setup

    if not args.lang or not args.install_dir:
        os._exit(2)
    run_install_setup(args.lang, args.install_dir)
    os._exit(0)

if args.uninstall:
    from core import run_uninstall_restore

    run_uninstall_restore()
    os._exit(0)

if not acquire_single_instance():
    os._exit(0)

import logging
import traceback

from core import restore_steam_user32_if_needed, setup_logging
from PyQt5.QtWidgets import QApplication
from Qt.logic import MainWindow
from Qt.theme import apply_theme

atexit.register(restore_steam_user32_if_needed)


def except_hook(type_, value, trace_back):
    setup_logging()
    logging.exception("".join(traceback.format_exception(type_, value, trace_back)))
    QApplication.quit()


sys.excepthook = except_hook

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
app.aboutToQuit.connect(restore_steam_user32_if_needed)
apply_theme(app)

window = MainWindow()
window.show()

sys.exit(app.exec_())
