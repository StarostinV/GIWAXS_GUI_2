from PyQt5.QtWidgets import QWidget, QGridLayout
from PyQt5.QtCore import pyqtSlot

from ...app.structures import CustomCrystal
from .legend import CrystalLegend
from .info import CrystalLabel
from .auto_rotate_button import AutoRotateButton

try:
    from .viewer import CrystalView
except ImportError:
    import warnings
    warnings.warn('PyQt3D package is not installed on your computer. 3D rendering is unavailable. '
                  'Please, consider installing it manuially via `pip install PyQt3D` or '
                  'wait for the new release that relies on OpenGl library.')
    CrystalView = None


class Crystal3DWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        if CrystalView:
            self._init_ui()
        self._crystal = None

    def _init_ui(self):
        layout = QGridLayout(self)
        self.setMinimumSize(400, 400)
        self.setWindowTitle('Crystal View')
        self.crystal_label = CrystalLabel(self)
        self.crystal_legend = CrystalLegend()
        self.crystal_view = CrystalView(self.crystal_legend)
        self.auto_rotate_btn = AutoRotateButton(self)
        self.crystal_view_widget = QWidget.createWindowContainer(self.crystal_view)
        layout.addWidget(self.crystal_label, 0, 0)
        layout.addWidget(self.auto_rotate_btn, 0, 1)
        layout.addWidget(self.crystal_view_widget, 1, 0)
        layout.addWidget(self.crystal_legend, 1, 1)

        self.auto_rotate_btn.sigStartRotating.connect(self.crystal_view.start_rotation)
        self.auto_rotate_btn.sigStopRotating.connect(self.crystal_view.stop_rotation)

    @pyqtSlot(CustomCrystal, name='setCrystal')
    def set_crystal(self, crystal: CustomCrystal):
        if CrystalView and (not self._crystal or crystal.key != self._crystal.key):
            self._crystal = crystal

            self.crystal_legend.set_crystal(crystal)
            self.crystal_view.set_crystal(crystal)
            self.crystal_label.set_crystal(crystal)
