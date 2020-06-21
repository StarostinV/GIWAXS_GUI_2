from pathlib import Path
import logging

from PyQt5.QtWidgets import (QMainWindow, QWidget, QSizePolicy,
                             QApplication, QShortcut, QMessageBox,
                             QFileDialog)
from PyQt5.QtCore import (Qt, pyqtSlot, pyqtSignal,
                          QObject, QThreadPool)
from PyQt5.QtGui import QKeySequence

import qdarkstyle
import qdarkgraystyle

from ..app import App
from ..app.update import CheckVersionMessage, check_outdated, update_package
from ..app.utils import Worker
from ..__version import __version__

from .dock_area import AppDockArea
from .basic_widgets import ToolBar
from .tools import Icon, get_image_filepath, get_folder_filepath, save_file_dialog

from .init_window import InitWindow
from .debug_widgets import DebugWindow
from .exception_message import UncaughtHook
from .notifications import (PopUpWrapper, NotificationTypes,
                            CheckingVersion, AskRestart, UpdatingProgram,
                            UpdateFailed, get_check_result_notification)


class GIWAXSMainController(QObject):
    EXIT_CODE_REBOOT: int = -123456789

    log = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()
        self.app = App()

        if self.app.fm.config['is_updated']:
            self.is_updated = True
            del self.app.fm.config['is_updated']
        else:
            self.is_updated = False

        self.init_window = None
        self.main_window = None

        if self.log.level <= logging.DEBUG:
            self.debug_window = DebugWindow()
        self.exception_hook = UncaughtHook()

        self.log.info(f'{"*" * 10}')
        self.log.info(f'Starting GIWAXS analysis {__version__}!')
        self.log.info(f'{"*" * 10}')
        self.set_style(self.app.fm.config['style'] or 'Gray Dark')
        self.open_init_window()

    def open_main_window(self):
        self.main_window = GIWAXSMainWindow(self.is_updated)

        self.main_window.sigCloseApp.connect(self.close_app)
        self.main_window.sigRestartApp.connect(self.restart_app)
        self.main_window.sigRestartAfterUpdate.connect(self.restart_after_update)
        self.main_window.sigOpenProject.connect(self.open_new_project)
        self.main_window.sigCloseProject.connect(self.close_project)
        self.main_window.sigSetStyle.connect(self.set_style)

    def open_init_window(self):
        self.init_window = InitWindow(self.app.fm.recent_projects, self.is_updated)
        self.init_window.sigOpenProject.connect(self.open_new_project)
        self.init_window.sigExit.connect(self.close_app)

    @pyqtSlot(name='closeProject')
    def close_project(self):
        self.app.fm.close_project()
        self.main_window.hide()
        self.open_init_window()

    @pyqtSlot(object, name='NewProject')
    def open_new_project(self, path: Path):
        if self.init_window:
            self.init_window.close()
            self.init_window = None
        if not self.main_window:
            self.open_main_window()
        else:
            self.main_window.show()
        self.app.fm.open_project(path)

    @pyqtSlot(name='restartAppAfterUpdate')
    def restart_after_update(self):
        self.app.fm.config['is_updated'] = True
        self.restart_app()

    @pyqtSlot(name='restartApp')
    def restart_app(self):
        self.app.close()
        q_app = QApplication.instance()
        App._instance = None
        q_app.exit(self.EXIT_CODE_REBOOT)

    @pyqtSlot(name='closeApp')
    def close_app(self):
        self.app.close()
        q_app = QApplication.instance()
        App._instance = None
        q_app.exit(0)

    @pyqtSlot(str, name='setStyle')
    def set_style(self, name: str = 'Gray Dark'):
        q_app = QApplication.instance()
        if not q_app:
            raise RuntimeError('No running application found.')
        if name == 'Dark':
            q_app.setStyleSheet('')
            q_app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        elif name == 'Gray Dark':
            q_app.setStyleSheet('')
            q_app.setStyleSheet(qdarkgraystyle.load_stylesheet_pyqt5())
        else:
            return

        self.app.fm.config['style'] = name


class GIWAXSMainWindow(QMainWindow):
    _MinimumSize = (500, 500)

    sigCloseApp = pyqtSignal()
    sigOpenProject = pyqtSignal(object)
    sigCloseProject = pyqtSignal()
    sigRestartApp = pyqtSignal()
    sigRestartAfterUpdate = pyqtSignal()
    sigSetStyle = pyqtSignal(str)

    def __init__(self, is_updated: bool, parent=None):
        super(GIWAXSMainWindow, self).__init__(parent=parent)
        self.__closing: bool = False
        self.app = App()
        self._init_toolbar()
        self._init_shortcuts()
        self._init_menubar()
        self.popups = PopUpWrapper(self)

        self.q_thead_pool = QThreadPool(self)

        self.dock_area = AppDockArea(self)
        self.app.fm.sigProjectClosed.connect(self.update_window_title)
        self.app.fm.sigProjectOpened.connect(self.update_window_title)

        self.setCentralWidget(self.dock_area)
        self.update_window_title()
        self.setWindowIcon(Icon('window_icon'))
        self.setMinimumSize(*self._MinimumSize)
        self.setWindowState(Qt.WindowMaximized)
        self.show()

        if not is_updated:
            self.check_update()
        else:
            self.popups.add_notification(get_check_result_notification(CheckVersionMessage.latest_version_installed))

    def check_update(self):
        self.popups.add_notification(CheckingVersion(), NotificationTypes.checking_version)
        worker = Worker(check_outdated, version=__version__)
        worker.autoDelete()
        worker.signals.result.connect(self._version_checked)
        self.q_thead_pool.start(worker)

    def update_package(self, target_version: str = ''):
        worker = Worker(update_package, version=target_version)
        worker.autoDelete()
        worker.signals.result.connect(self._package_updated)
        self.q_thead_pool.start(worker)
        self.popups.add_notification(UpdatingProgram(target_version), NotificationTypes.updating_program)

    @pyqtSlot(object, name='versionChecked')
    def _version_checked(self, res: CheckVersionMessage):
        self.popups.remove_by_name(NotificationTypes.checking_version)
        self.popups.add_notification(get_check_result_notification(res), NotificationTypes.check_result)

        if res.value == CheckVersionMessage.new_version_available.value:
            try:
                self.update_package(res.version)
            except AttributeError:
                return

    @pyqtSlot(object, name='packageUpdated')
    def _package_updated(self, is_updated: bool):
        self.popups.remove_by_name(NotificationTypes.updating_program)
        if is_updated:
            ask_restart = AskRestart()
            ask_restart.sigRestart.connect(self.sigRestartAfterUpdate)
            self.popups.add_notification(ask_restart)
        else:
            self.popups.add_notification(UpdateFailed())

    def update_window_title(self):
        if self.app.fm.project_opened:
            self.setWindowTitle(f'{self.app.fm.project_name} - GIWAXS analysis')
        else:
            self.setWindowTitle('GIWAXS analysis')

    @pyqtSlot(name='NewProjectDialog')
    def _new_project_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, 'New project folder')
        if not folder:
            return
        folder = Path(folder)
        if folder.is_dir():
            self.sigOpenProject.emit(folder)

    @pyqtSlot(name='addExSitu')
    def _add_file_dialog(self):
        filepath = get_image_filepath(self)
        if filepath:
            self.app.fm.add_root_path_to_project(filepath)

    def _save_as_h5(self):
        path = save_file_dialog(self, title='Save project')
        if path:
            self.app.fm.save_as_h5(path)

    def _add_folder_dialog(self):
        filepath = get_folder_filepath(self, message='Choose directory containing images or h5 files')
        if filepath:
            self.app.fm.add_root_path_to_project(filepath)

    def _init_menubar(self):
        self.menubar = self.menuBar()

        # File menu

        self.file_menu = self.menubar.addMenu('File')
        self.file_menu.addAction('New project', self._new_project_dialog)
        recent_projects_menu = self.file_menu.addMenu('Recent projects')

        for project_path in self.app.fm.recent_projects:
            recent_projects_menu.addAction(
                project_path.name, lambda *x, p=project_path: self.sigOpenProject.emit(p))

        # Save

        self.save_menu = self.file_menu.addMenu('Save project as ...')
        self.save_menu.addAction('Save as h5 file', self._save_as_h5)

        # Close project

        self.file_menu.addAction('Close project', lambda *x: self.sigCloseProject.emit())

        # Restart

        self.file_menu.addAction('Restart', lambda *x: self.restart())

        # Data menu

        self.data_menu = self.menubar.addMenu('Data')
        self.add_data_menu = self.data_menu.addMenu('Add data')

        self.add_data_menu.addAction('Add file', self._add_file_dialog)
        self.add_data_menu.addAction('Add folder', self._add_folder_dialog)

        # Preferences menu

        self.preferences = self.menubar.addMenu('Preferences')
        self.themes_menu = self.preferences.addMenu('Themes')
        themes = ['Dark', 'Gray Dark']
        # themes = CSS.list_css() + QStyleFactory.keys()
        for theme in themes:
            theme_action = self.themes_menu.addAction(theme)
            theme_action.triggered.connect(lambda *x, t=theme: self.sigSetStyle.emit(t))

    def _init_shortcuts(self):
        self.copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        self.copy_shortcut.activated.connect(lambda *x: self.app.roi_dict.copy_rois('selected'))

        self.paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
        self.paste_shortcut.activated.connect(lambda *x: self.app.roi_dict.paste_rois())

        self.select_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        self.select_shortcut.activated.connect(lambda *x: self.app.roi_dict.select_all())

        self.delete_shortcut = QShortcut(QKeySequence('Del'), self)
        self.delete_shortcut.activated.connect(lambda *x: self.app.roi_dict.delete_selected_roi())

        self.fit_shortcut = QShortcut(QKeySequence('Ctrl+F'), self)
        self.fit_shortcut.activated.connect(lambda *x: self.app.roi_dict.open_fit_rois(True))

        def raise_err(*_):
            raise ValueError('Congratulations, you found an error combination used for testing! '
                             'Your project will be deleted in 3 seconds...')

        self.raise_shortcut = QShortcut(QKeySequence('Ctrl+R'), self)
        self.raise_shortcut.activated.connect(raise_err)

    def _init_toolbar(self):

        docks_toolbar = ToolBar('Docks', self)
        self.addToolBar(docks_toolbar)

        control_widget = docks_toolbar.addAction(Icon('folder'), 'File Manager')
        control_widget.triggered.connect(lambda: self.dock_area.show_hide_docks('file_widget'))

        radial_profile = docks_toolbar.addAction(Icon('radial_profile'), 'Radial profile')
        radial_profile.triggered.connect(lambda: self.dock_area.show_hide_docks('radial_profile'))

        angular_profile = docks_toolbar.addAction(Icon('angular_profile'), 'Angular profile')
        angular_profile.triggered.connect(lambda: self.dock_area.show_hide_docks('angular_profile'))

        interpolation = docks_toolbar.addAction(Icon('interpolate'), 'Polar Viewer')
        interpolation.triggered.connect(lambda: self.dock_area.show_hide_docks('polar'))

        self.gen_toolbar = ToolBar('General')
        self.addToolBar(self.gen_toolbar)
        spacer_widget = QWidget()
        spacer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer_widget.setVisible(True)
        self.gen_toolbar.addWidget(spacer_widget)

        self.fullscreen_action = self.gen_toolbar.addAction(Icon('tofullscreen'), 'Full screen')
        self.fullscreen_action.triggered.connect(self._on_fullscreen_changed)

    def _on_fullscreen_changed(self):
        if self.isFullScreen():
            self.setWindowState(Qt.WindowMaximized)
            self.fullscreen_action.setIcon(Icon('tofullscreen'))
        else:
            self.setWindowState(Qt.WindowFullScreen)
            self.fullscreen_action.setIcon(Icon('fromfullscreen'))

    @pyqtSlot(name='restartApp')
    def restart(self):
        self.__closing = True
        self.sigRestartApp.emit()

    def closeEvent(self, a0) -> None:
        if self.__closing:
            super().closeEvent(a0)
        else:
            reply = QMessageBox.question(self, 'Message',
                                         "Are you sure to quit? The project will be saved.",
                                         QMessageBox.Yes |
                                         QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                a0.accept()
                self.__closing = True
                self.sigCloseApp.emit()
            else:
                a0.ignore()
