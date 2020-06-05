import sys
import logging

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from giwaxs_gui import App, DockAreaWidget


if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
	qapp = QApplication(sys.argv)
	giwaxs_app = App()
	window = DockAreaWidget()
	sys.exit(qapp.exec_())
