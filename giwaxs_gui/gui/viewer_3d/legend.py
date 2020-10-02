from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import pyqtSlot, pyqtSignal

from pyqtgraph import ColorButton
from crystals import Crystal

from .colors import CrystalColors


class CrystalLegend(QWidget):
    sigColorChanged = pyqtSignal(str, QColor)

    def __init__(self):
        super().__init__()
        self._widgets = []
        self._crystal = None
        self.colors = CrystalColors()
        self._layout = QGridLayout(self)
        self.setMaximumWidth(100)

    @property
    def crystal(self):
        return self._crystal

    @pyqtSlot(object, name='setCrystal')
    def set_crystal(self, crystal: Crystal):
        self._crystal = crystal
        self.colors.set_crystal(crystal)
        self._clear_layout()

        for num, (element, color) in enumerate(self.colors):
            label, color_btn = self._add_element(element, color)
            self._layout.addWidget(label, num, 0)
            self._layout.addWidget(color_btn, num, 1)

    def _add_element(self, element: str, color: QColor):
        color_btn = ColorButton(self, color)
        color_btn.setFixedSize(30, 30)
        label = QLabel(element)
        label.setFont(QFont('Helvetica', 16))
        color_btn.sigColorChanging.connect(self._on_color_changed(element))
        self._widgets.extend([label, color_btn])
        return label, color_btn

    def _clear_layout(self):
        widgets, self._widgets = self._widgets, []
        for widget in widgets:
            self._layout.removeWidget(widget)
            widget.deleteLater()

    def _on_color_changed(self, element):
        def func(btn):
            self.colors.set_color(element, btn.color())
            self.sigColorChanged.emit(element, btn.color())

        return func
