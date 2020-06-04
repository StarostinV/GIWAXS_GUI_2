from pathlib import Path

from PyQt5.QtWidgets import (QTreeView, QFileDialog, QMenu,
                             QWidget, QHBoxLayout, QLabel)
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtCore import Qt

from ..basic_widgets import RoundedPushButton
from ..tools import Icon
from ...app.file_manager import FileManager, ImageKey

AVAILABLE_FILE_FORMATS = tuple('.tif .tiff .edf .edf.gz'.split())


def filter_files(path: Path):
    yield from (p for p in path.iterdir() if p.suffix in AVAILABLE_FILE_FORMATS)


def filter_dirs(path: Path):
    yield from (p for p in path.iterdir() if p.is_dir())


class FileModel(QStandardItemModel):
    def __init__(self):
        super(FileModel, self).__init__()
        self.setHorizontalHeaderLabels([''])
        self.setRowCount(0)

    def new_project(self):
        self.removeRows(1, self.rowCount() - 1)


class ImageItem(QStandardItem):

    def __init__(self, key: ImageKey):
        super().__init__(key.name)
        self.key: ImageKey = key
        self.path: Path = self.key.path
        self.setIcon(Icon('data'))


class FolderItem(QStandardItem):

    def __init__(self, path: Path, is_parsed: bool = False):
        super().__init__(path.name)
        self.path: Path = path
        self._is_parsed = is_parsed

    @property
    def is_parsed(self):
        return self._is_parsed

    def on_clicked(self):
        if not self.is_parsed:
            self.update()

    def update(self):
        if self.is_parsed:
            self.removeRows(0, self.rowCount())
        self._is_parsed = True
        for path in sorted(list(filter_dirs(self.path))):
            self.appendRow(FolderItem(path))

        for path in sorted(list(filter_files(self.path))):
            self.appendRow(ImageItem(ImageKey(path)))


class FileViewer(QTreeView):

    def __init__(self, fm: FileManager, parent=None):
        super().__init__(parent)
        self._model = FileModel()
        self.setModel(self._model)
        self.setEditTriggers(QTreeView.NoEditTriggers)
        self._fm = fm
        self._fm.sigNewFile.connect(self._add_new_file)
        self._fm.sigNewFolder.connect(self._add_new_folder)
        self._fm.sigProjectClosed.connect(self._model.new_project)
        # self._fm.sigExSituAddedFile.connect(self._add_ex_situ)
        # self._fm.sigPathsChanged.connect(self._update_paths)
        self.selectionModel().currentChanged.connect(self._on_clicked)
        self.customContextMenuRequested.connect(self._context_menu)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self._init_ui()
        self.show()

    def _init_ui(self):
        add_file_button = RoundedPushButton(icon=Icon('data'), radius=30,
                                            background_color='transparent')
        add_file_button.clicked.connect(self._open_add_file_menu)
        add_folder_button = RoundedPushButton(icon=Icon('folder'), radius=30,
                                              background_color='transparent')
        add_folder_button.clicked.connect(self._open_add_folder_menu)
        layout = self._get_header_layout(QStandardItem(), 'Files')
        layout.addWidget(add_file_button)
        layout.addWidget(add_folder_button)

    def _get_header_layout(self, item: QStandardItem, label: str):
        header_widget = QWidget(self)
        layout = QHBoxLayout()
        header_widget.setLayout(layout)
        label_widget = QLabel(label)
        layout.addWidget(label_widget, alignment=Qt.AlignLeft)
        layout.addStretch(1)
        self._model.appendRow(item)
        self.setIndexWidget(item.index(), header_widget)
        return layout

    def _add_new_file(self, key: ImageKey):
        self._model.appendRow(ImageItem(key))

    def _add_new_folder(self, path: Path):
        self._model.appendRow(FolderItem(path))

    def _on_clicked(self, index):
        item = self._model.itemFromIndex(index)
        if isinstance(item, ImageItem):
            self._fm.change_image(item.key)
        elif isinstance(item, FolderItem):
            item.on_clicked()
            self.setExpanded(item.index(), True)

    def _open_add_file_menu(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filepath, _ = QFileDialog.getOpenFileName(
            self, 'Open image', '',
            'edf, tiff files (*.tiff *.edf *.tif *.edf.gz)', options=options)
        if filepath:
            self._fm.add_ex_situ_data(Path(filepath))

    def _open_add_folder_menu(self):
        options = QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        folder_path = QFileDialog.getExistingDirectory(
            self, 'Choose directory containing edf or tiff files', '',
            options=options)
        if folder_path:
            self._fm.add_ex_situ_data(Path(folder_path))

    def _context_menu(self, position):
        item = self._model.itemFromIndex(self.indexAt(position))
        menu = QMenu()
        if isinstance(item, FolderItem):
            update_folder = menu.addAction('Update folder')
            update_folder.triggered.connect(item.update)
            close_folder = menu.addAction('Remove from project')
            close_folder.triggered.connect(
                lambda *x, it=item: self._remove_item(it))

        elif isinstance(item, ImageItem):
            close_image = menu.addAction('Remove from project')
            close_image.triggered.connect(
                lambda *x, it=item: self._remove_item(it))
        else:
            return
        menu.exec_(self.viewport().mapToGlobal(position))

    def _remove_item(self, item: FolderItem or ImageItem):
        self._fm.remove_path(item.path)
        item.parent().removeRow(item.row())
