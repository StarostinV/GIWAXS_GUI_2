import sys
import logging

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from .app import App
from .gui import GIWAXSMainWindow, UncaughtHook, DebugWindow


def run(logging_level: int = logging.ERROR):
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    for logger in loggers:
        logger.setLevel(logging_level)

    exception_hook = UncaughtHook()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    qapp = QApplication(sys.argv)
    giwaxs_app = App()
    if logging_level <= logging.DEBUG:
        debug_window = DebugWindow()
    window = GIWAXSMainWindow()
    sys.exit(qapp.exec_())
