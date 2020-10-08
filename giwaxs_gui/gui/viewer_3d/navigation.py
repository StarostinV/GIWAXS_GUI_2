from dataclasses import dataclass

from PyQt5.QtGui import QKeyEvent
from PyQt5.QtCore import Qt

from .camera import Camera


class Navigation(object):
    def __init__(self, camera: Camera):
        self.camera = camera

    def should_move(self) -> bool:
        return False

    def key_press_event(self, a0: QKeyEvent) -> None:
        pass

    def key_release_event(self, a0: QKeyEvent) -> None:
        pass

    def wheel_event(self, event):
        pass

    def mouse_press(self, event):
        pass

    def mouse_release(self, event):
        pass

    def mouse_move(self, event):
        pass

    def move_camera(self):
        pass


@dataclass
class MouseState:
    first_move: bool = True
    is_moving: bool = False
    is_pressed: bool = False
    x: float = 0.
    y: float = 0.

    @property
    def should_move(self):
        return self.is_pressed and (self.first_move or self.is_moving)


class BasicNavigation(Navigation):
    def __init__(self, camera: Camera):
        super().__init__(camera)
        self._key_translations = set()
        self._mouse_translations = 0
        self._mouse_state: MouseState = MouseState()

    def should_move(self) -> bool:
        return bool(self._key_translations) or self._mouse_translations != 0 or self._mouse_state.should_move

    def key_press_event(self, a0: QKeyEvent) -> None:
        if a0.key() in (Qt.Key_Down, Qt.Key_Left, Qt.Key_Right, Qt.Key_Up):
            self._key_translations.add(a0.key())

    def key_release_event(self, a0: QKeyEvent) -> None:
        if a0.key() in self._key_translations:
            self._key_translations.remove(a0.key())

    def wheel_event(self, event):
        delta = - event.angleDelta().y() / 120  # 1 or -1
        self._mouse_translations += delta

    def mouse_press(self, event):
        self._mouse_state.is_pressed = True
        self._mouse_state.first_move = True
        self._mouse_state.x = event.x()
        self._mouse_state.y = event.y()

    def mouse_release(self, event):
        self._mouse_state.is_pressed = False

    def mouse_move(self, event):
        self._mouse_state.is_moving = True
        self._mouse_state.x = event.x()
        self._mouse_state.y = event.y()

    def move_camera(self):
        if Qt.Key_Down in self._key_translations:
            self.camera.rotate_down()
        if Qt.Key_Up in self._key_translations:
            self.camera.rotate_up()
        if Qt.Key_Left in self._key_translations:
            self.camera.rotate_left()
        if Qt.Key_Right in self._key_translations:
            self.camera.rotate_right()
        if self._mouse_translations < 0:
            self.camera.move_closer()
        if self._mouse_translations > 0:
            self.camera.move_away()
        self._mouse_translations = 0

        if self._mouse_state.should_move:
            self.camera.mouse_move(x_pos=self._mouse_state.x, y_pos=self._mouse_state.y,
                                   first_move=self._mouse_state.first_move)
            self._mouse_state.first_move = False
            self._mouse_state.is_moving = False
