from collections import OrderedDict

from PyQt5.QtWidgets import (QWidget,
                             QGridLayout, QTreeView)
from PyQt5.QtCore import Qt, QObject, QItemSelection
from PyQt5.QtGui import QColor, QStandardItem, QStandardItemModel

from giwaxs_gui.app.rois import Roi
from giwaxs_gui.gui.roi_widgets import AbstractRoiHolder, AbstractRoiWidget


class StandardItem(QStandardItem):
    def __init__(self, text: str, key: int, is_numeric: bool = True):
        super().__init__(text)
        self.key = key
        self.is_numeric = is_numeric

    def __lt__(self, other):
        if self.is_numeric:
            try:
                return float(self.text()) < float(other.text())
            except ValueError:
                pass
        return super().__lt__(other)


class RoiWidgetItem(AbstractRoiWidget, QObject):
    COLOR_DICT = dict(
        default=QColor(0, 0, 0, 0),
        active=QColor(0, 128, 255, 100),
        fixed=QColor(0, 255, 0, 100),
        fixed_active=QColor(255, 0, 255, 100)
    )

    PARAM_DICT = OrderedDict([('name', 'Name'),
                              ('type', 'Roi type'),
                              ('radius', 'Radius'),
                              ('width', 'Width'),
                              ('angle', 'Angle'),
                              ('angle_std', 'Angle Width'),
                              ('key', 'Key')])

    def __init__(self, roi: Roi, parent):
        AbstractRoiWidget.__init__(self, roi, enable_context=True)
        QObject.__init__(self, parent)

        self.__items = self._init_items()
        self.update_color()
        self.move_roi()

    @property
    def row(self):
        return self.__items['name'].row()

    def _init_items(self) -> dict:
        roi_key = self.roi.key
        items = dict(name=StandardItem(self.roi.name, roi_key),
                     key=StandardItem(str(self.roi.key), roi_key),
                     type=StandardItem(str(self.roi.type.name), roi_key, False))
        for key in 'radius width angle angle_std'.split():
            items[key] = StandardItem('', roi_key)

        return items

    def move_roi(self):
        for key in 'radius width angle angle_std'.split():
            self.__items[key].setText(f'{getattr(self.roi, key):.2f}')

    def items(self):
        return [self.__items[key] for key in self.PARAM_DICT.keys()]

    def send_move(self):
        pass

    def rename(self):
        self.__items['name'].setText(self.roi.name)

    def change_type(self):
        self.__items['type'].setText(str(self.roi.type.name))

    def set_color(self, color):
        for item in self.__items.values():
            item.setBackground(color)


class RoiMetaWidget(AbstractRoiHolder, QWidget):
    def __init__(self, parent=None):
        AbstractRoiHolder.__init__(self, 'RoiMetaWidget')
        QWidget.__init__(self, parent)

        self._model = QStandardItemModel(0, len(RoiWidgetItem.PARAM_DICT), self)
        self._model.setHorizontalHeaderLabels(list(RoiWidgetItem.PARAM_DICT.values()))
        # self._model.setRowCount(0)

        self.tree_view = QTreeView(self)
        self.tree_view.setModel(self._model)

        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._custom_menu)
        self.tree_view.selectionModel().selectionChanged.connect(self._selection_changed)
        self.tree_view.header().setSectionsClickable(True)
        self.tree_view.header().setSortIndicatorShown(True)
        self.tree_view.header().sortIndicatorChanged.connect(self._model.sort)

        self._roi_dict.sig_roi_renamed.connect(self._rename)

        self._init_ui()

    def _init_connect(self):
        super()._init_connect()
        self._roi_dict.sig_type_changed.connect(self._type_changed)

    def _init_ui(self):
        layout = QGridLayout(self)
        layout.addWidget(self.tree_view)

    def _type_changed(self, key: int):
        self._roi_widgets[key].change_type()

    def _delete_roi_widget(self, roi_widget) -> None:
        self.tree_view.selectionModel().blockSignals(True)
        self._model.removeRow(roi_widget.row)
        self.tree_view.selectionModel().blockSignals(False)

    def _make_roi_widget(self, roi: Roi) -> AbstractRoiWidget:
        roi_widget = RoiWidgetItem(roi, self.tree_view)
        self._model.appendRow(roi_widget.items())
        return roi_widget

    def _custom_menu(self, pos):
        item = self._model.itemFromIndex(self.tree_view.indexAt(pos))
        if item:
            self._roi_widgets[item.key].show_context_menu()

    def _selection_changed(self, item: QItemSelection):
        keys = set(self._model.itemFromIndex(index).key for index in item.indexes())
        if len(keys) == 1:
            self._roi_dict.select(next(iter(keys)))

    def _rename(self, key: int):
        try:
            self._roi_widgets[key].rename()
        except KeyError:
            pass
