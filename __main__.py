import sys
from pathlib import Path
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
	# giwaxs_app.fm.open_project(Path(__file__).parent / 'test_project')
	# data_folder = Path(__file__).parent / 'data'
	# giwaxs_app.fm._project_structure.new_time_series('_real_time', sorted(list(data_folder.glob('*.tiff'))))

	# giwaxs_app.roi_dict.create_roi(10, 10)
	sys.exit(qapp.exec_())
