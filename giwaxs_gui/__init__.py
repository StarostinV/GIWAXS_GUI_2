import sys
import logging

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from .app import App
from .gui import GIWAXSMainWindow, UncaughtHook


def run():
    logging.basicConfig(level=logging.ERROR)
    exception_hook = UncaughtHook()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    qapp = QApplication(sys.argv)
    giwaxs_app = App()
    window = GIWAXSMainWindow()
    sys.exit(qapp.exec_())
