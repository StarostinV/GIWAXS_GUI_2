import logging
from pathlib import Path
from typing import List

from PyQt5.QtWidgets import (QGraphicsColorizeEffect, QLineEdit,
                             QWidget, QApplication, QMessageBox,
                             QFileDialog)
from PyQt5.QtCore import QPropertyAnimation, Qt
from PyQt5.QtGui import QColor, QIcon

from ..app.file_manager import GLOB_IMAGE_FORMATS

ICON_PATH: Path = Path(__file__).parents[1] / 'static' / 'icons'
CSS_PATH: Path = Path(__file__).parents[1] / 'static' / 'css'

logger = logging.getLogger(__name__)


def save_file_dialog(parent, title: str = 'Save File', file_format: str = 'H5 file (*.h5)'
                     ):
    options = QFileDialog.Options()
    options |= QFileDialog.DontUseNativeDialog
    filename, _ = QFileDialog.getSaveFileName(parent, title, '', file_format, options=options)
    if filename:
        return Path(filename)


def get_image_filepath(parent, message: str = 'Open image') -> Path or None:
    options = QFileDialog.Options()
    options |= QFileDialog.DontUseNativeDialog
    filepath, _ = QFileDialog.getOpenFileName(
        parent, message, '',
        GLOB_IMAGE_FORMATS, options=options)
    if filepath:
        return Path(filepath)


def get_folder_filepath(parent, message: str, *, show_files: bool = True) -> Path or None:
    options = QFileDialog.DontResolveSymlinks | QFileDialog.DontUseNativeDialog
    if not show_files:
        options |= QFileDialog.ShowDirsOnly

    folder_path = QFileDialog.getExistingDirectory(
        parent, message, '',
        options=options)
    if folder_path:
        return Path(folder_path)


def show_error(err: str, *, error_title: str = 'Internal Error', info_text: str = ''):
    logger.info(f'Error message shown: {error_title} - {err} {info_text}.')

    mb = QMessageBox()
    mb.setIcon(QMessageBox.Critical)
    mb.setWindowTitle(error_title)
    mb.setWindowIcon(Icon('error'))
    mb.setText(err)
    if info_text:
        mb.setInformativeText(info_text)
    mb.exec_()


class Icon(QIcon):
    def __init__(self, name: str):
        if name.find('.') == -1:
            name += '.png'
        name = str(ICON_PATH / name)
        QIcon.__init__(self, name)


class CSS(object):
    default = 'Dark Grey'

    @staticmethod
    def get_css(name: str) -> str or None:
        if '.css' not in name:
            name += '.css'
        try:
            with open(str((CSS_PATH / name).resolve()), 'r') as f:
                return f.read()
        except FileNotFoundError:
            return
        except Exception as err:
            logger.exception(err)
            return

    @staticmethod
    def list_css() -> List[str]:
        return [p.stem for p in CSS_PATH.glob('*.css')]


def center_widget(widget):
    frame_gm = widget.frameGeometry()
    screen = QApplication.desktop().screenNumber(
        QApplication.desktop().cursor().pos())
    center_point = QApplication.desktop().screenGeometry(
        screen).center()
    frame_gm.moveCenter(center_point)
    widget.move(frame_gm.topLeft())


def validate_scientific_value(q_line_edit: QLineEdit,
                              data_type: type or None = float,
                              empty_possible: bool = False,
                              additional_conditions: tuple = ()):
    text_value = q_line_edit.text().replace(',', '.')
    if data_type is None:
        return text_value
    try:
        value = data_type(text_value)
    except ValueError:
        if not empty_possible:
            color_animation(q_line_edit)
        return
    for condition in additional_conditions:
        if not condition(value):
            return
    return value


def color_animation(widget: QWidget, color=Qt.red):
    effect = QGraphicsColorizeEffect(widget)
    widget.setGraphicsEffect(effect)

    widget.animation = QPropertyAnimation(effect, b'color')

    widget.animation.setStartValue(QColor(color))
    widget.animation.setEndValue(QColor(Qt.black))

    widget.animation.setLoopCount(1)
    widget.animation.setDuration(1500)
    widget.animation.start()
