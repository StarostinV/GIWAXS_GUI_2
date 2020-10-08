from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import QTimer, pyqtSlot
from PyQt5.QtGui import QKeyEvent, QSurfaceFormat, QMouseEvent

import OpenGL.GL as gl
import glm

from .scene import Scene, CrystalScene, SceneCrystal


class CrystalViewer(QOpenGLWidget):
    def __init__(self, scene: Scene = None):
        super().__init__()
        self.scene = scene or CrystalScene()
        self.navigation = self.scene.navigation
        self.setMinimumSize(500, 500)
        self._auto_rotation: bool = False

        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._update_scene)
        self.timer.start()

    @staticmethod
    def enable_multisampling(num: int = 10):
        fmt = QSurfaceFormat()
        fmt.setSamples(num)
        QSurfaceFormat.setDefaultFormat(fmt)

    @pyqtSlot(name='startRotation')
    def start_rotation(self):
        self._auto_rotation = True

    @pyqtSlot(name='stopRotation')
    def stop_rotation(self):
        self._auto_rotation = False

    @pyqtSlot(object, name='setCrystal')
    def set_crystal(self, crystal: SceneCrystal):
        self.scene.set_crystal(crystal)

    def update_scene(self, *args):
        self.scene.force_redraw()

    def _update_scene(self):
        if self.scene.should_redraw() or self._auto_rotation:
            self.update()

    def _get_projection_matrix(self):
        return _get_projection_matrix(self.width(), self.height())

    def keyPressEvent(self, a0: QKeyEvent) -> None:
        self.navigation.key_press_event(a0)

    def keyReleaseEvent(self, a0: QKeyEvent) -> None:
        self.navigation.key_release_event(a0)

    def wheelEvent(self, event):
        self.navigation.wheel_event(event)

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        self.navigation.mouse_press(a0)

    def mouseReleaseEvent(self, a0: QMouseEvent) -> None:
        self.navigation.mouse_release(a0)

    def mouseMoveEvent(self, a0: QMouseEvent) -> None:
        self.navigation.mouse_move(a0)

    def initializeGL(self) -> None:
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_MULTISAMPLE)

        self.scene.init_scene()
        self.scene.set_projection(self._get_projection_matrix())

    def resizeGL(self, w: int, h: int) -> None:
        self.scene.set_projection(_get_projection_matrix(w, h))

    def paintGL(self) -> None:
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        if self._auto_rotation:
            self.scene.camera.autorotate()
            self.scene.update_view()
        self.scene.draw()


def _get_projection_matrix(w: int, h: int):
    return glm.perspective(glm.radians(40.), w / h, 0.1, 100)
