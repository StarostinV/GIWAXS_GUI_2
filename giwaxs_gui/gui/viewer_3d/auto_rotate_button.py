from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import pyqtSignal


class AutoRotateButton(QPushButton):
    sigStartRotating = pyqtSignal()
    sigStopRotating = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__('Auto rotate', parent)
        self._rotating: bool = False
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        if self._rotating:
            self._rotating = False
            self.setText('Auto rotate')
            self.sigStopRotating.emit()
        else:
            self._rotating = True
            self.setText('Stop rotation')
            self.sigStartRotating.emit()
