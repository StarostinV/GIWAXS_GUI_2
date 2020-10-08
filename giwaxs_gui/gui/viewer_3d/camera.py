import glm

from .shader import Shader


class Camera(object):
    def __init__(self):
        self._cam_target = glm.vec3(0, 0, 0)
        self._pitch = 0
        self._yaw = 0
        self._cam_unit_pos = None
        self._update_cam_unit_pos()

        self._cam_distance = 3
        self._cam_direction = glm.normalize(self.cam_pos - self._cam_target)
        self._cam_up = glm.vec3(0, 1, 0)
        self._min_distance = 0.1
        self._view_matrix = self._calc_view_matrix()
        self._should_update: bool = False
        self._last_x = 0
        self._last_y = 0

        self.rotation_speed: float = 5
        self.autorotate_speed: float = 0.5
        self.wheel_speed: float = 0.5

    @property
    def should_update(self):
        return self._should_update

    @property
    def view_matrix(self):
        if self._should_update:
            self._view_matrix = self._calc_view_matrix()
            self._should_update = False
        return self._view_matrix

    @property
    def cam_pos(self):
        return self._cam_unit_pos * self._cam_distance

    @property
    def cam_distance(self):
        return self._cam_distance

    @cam_distance.setter
    def cam_distance(self, distance: float):
        self._cam_distance = distance
        self._should_update = True

    @property
    def cam_target(self):
        return self._cam_target

    @cam_target.setter
    def cam_target(self, cam_target: glm.vec3):
        self._cam_target = cam_target
        self._should_update = True

    def _calc_view_matrix(self):
        return glm.lookAt(self.cam_pos + self._cam_target, self._cam_target, self._cam_up)

    def set_view(self, shader: Shader, attr: str = 'view'):
        shader.set_mat4_glm(self.view_matrix, attr)

    def rotate_left(self):
        self._should_update = True
        self._yaw += self.rotation_speed
        self._update_cam_unit_pos()

    def rotate_right(self):
        self._should_update = True
        self._yaw -= self.rotation_speed
        self._update_cam_unit_pos()

    def autorotate(self):
        self._should_update = True
        self._yaw -= self.autorotate_speed
        self._update_cam_unit_pos()

    def rotate_up(self):
        self._should_update = True
        self._pitch += self.rotation_speed
        self._update_cam_unit_pos()

    def rotate_down(self):
        self._should_update = True
        self._pitch -= self.rotation_speed
        self._update_cam_unit_pos()

    def move_closer(self):
        distance = self.cam_distance - self.wheel_speed
        if glm.abs(distance) >= self._min_distance:
            self.cam_distance = distance

    def move_away(self):
        self.cam_distance = self.cam_distance + self.wheel_speed

    def mouse_move(self, x_pos: float, y_pos: float, first_move: bool):
        self._should_update = True

        if first_move:
            self._last_x = x_pos
            self._last_y = y_pos

        x_offset = (x_pos - self._last_x) * self.wheel_speed
        y_offset = (y_pos - self._last_y) * self.wheel_speed

        self._last_x = x_pos
        self._last_y = y_pos

        self._yaw += x_offset
        self._pitch += y_offset

        self._update_cam_unit_pos()

    def _update_cam_unit_pos(self):
        self._pitch = max(-89., min(89., self._pitch))

        pitch = glm.radians(self._pitch)
        yaw = glm.radians(self._yaw)

        self._cam_unit_pos = glm.normalize(glm.vec3(glm.cos(yaw) * glm.cos(pitch),
                                                    glm.sin(pitch),
                                                    glm.sin(yaw) * glm.cos(pitch)))
