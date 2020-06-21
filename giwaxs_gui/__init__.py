import sys
import argparse
import logging
import subprocess

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from giwaxs_gui.app import App
from giwaxs_gui.gui import GIWAXSMainController, UncaughtHook, DebugWindow
from giwaxs_gui.__version import __version__


__author__ = 'Vladimir Starostin'
__email__ = 'v.starostin.m@gmail.com'


def run(logging_level: int = logging.ERROR):
    for log in (logging.getLogger(name) for name in logging.root.manager.loggerDict):
        log.setLevel(logging_level)

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    q_app = QApplication([])

    giwaxs_app = GIWAXSMainController()

    return q_app.exec_()


def main():
    parser = argparse.ArgumentParser(description='Program for GIWAXS analysis')

    parser.add_argument('-d', '--debug', action='store_true', help='open program in debug mode')

    args = parser.parse_args()

    level: int = logging.DEBUG if args.debug else logging.ERROR

    exit_code: int = run(level)

    if exit_code == GIWAXSMainController.EXIT_CODE_REBOOT:
        subprocess.Popen('giwaxs_gui', creationflags=subprocess.DETACHED_PROCESS)
        return 0

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
