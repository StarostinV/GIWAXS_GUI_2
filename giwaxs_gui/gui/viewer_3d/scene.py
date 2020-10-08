from abc import abstractmethod
from typing import Generator, Tuple
from collections import namedtuple

import OpenGL.GL as gl
import glm
import numpy as np

from .meshes import SphereMesh, CylinderMesh, PlaneMesh
from .navigation import Navigation, BasicNavigation
from .camera import Camera
from .shader import Shader

UnitVectors = namedtuple('UnitVectors', 'a b c')
SceneCrystal = namedtuple('Crystal', 'atoms unit_vectors')

Vec3 = Tuple[float, float, float]
Vec4 = Tuple[float, float, float, float]


class Atom(object):
    def __init__(self, element: str, coords: Vec3, color: Vec4 = None):
        self._element = element
        self._coords = coords
        self._color = color or (1, 1, 1)

    @property
    def element(self):
        return self._element

    @property
    def coords(self):
        return self._coords

    @property
    def color(self):
        return self._color

    def set_color(self, color):
        self._color = color


class Scene(object):
    @property
    @abstractmethod
    def navigation(self) -> Navigation:
        pass

    @property
    def camera(self) -> Camera:
        return self.navigation.camera

    @abstractmethod
    def should_redraw(self) -> bool:
        pass

    @abstractmethod
    def force_redraw(self):
        pass

    @abstractmethod
    def set_projection(self, projection_mat):
        pass

    @abstractmethod
    def set_plane(self, miller_indices: Vec3):
        pass

    @abstractmethod
    def remove_plane(self):
        pass

    @abstractmethod
    def init_scene(self):
        pass

    @abstractmethod
    def update_view(self):
        pass

    @abstractmethod
    def draw(self):
        pass

    @abstractmethod
    def set_crystal(self, crystal: SceneCrystal):
        pass

    @property
    @abstractmethod
    def crystal(self) -> SceneCrystal:
        pass

    @abstractmethod
    def clear(self):
        pass

    @abstractmethod
    def set_backcolor(self, backcolor: Vec4):
        pass


class CrystalScene(Scene):
    def __init__(self,
                 light_position: Vec3 = (500, 200, 0),
                 backcolor: Vec4 = (1., 1., 1., 1)
                 ):

        self._navigation = BasicNavigation(Camera())

        self._sphere = SphereMesh.load()
        self._cylinder = CylinderMesh.load()
        self._plane = PlaneMesh()

        self._shader: Shader = Shader(
            ('vertex_shader.vs', gl.GL_VERTEX_SHADER),
            ('fragment_shader.fs', gl.GL_FRAGMENT_SHADER)
        )

        self._should_redraw: bool = True
        self._should_update_view: bool = True
        self._light_position: Vec3 = light_position

        self._cylinder_matrices = []
        self._crystal = None
        self._show_plane: bool = False

        self._backcolor: Vec4 = backcolor

    @property
    def navigation(self) -> Navigation:
        return self._navigation

    def should_redraw(self) -> bool:
        return self._should_redraw or self._navigation.should_move()

    def force_redraw(self):
        self._should_redraw = True

    def set_projection(self, projection_mat):
        self._should_redraw = True
        self._shader.use()
        self._shader.set_mat4_glm(projection_mat, 'projection')

    def update_view(self):
        self._shader.use()
        self.camera.set_view(self._shader)
        self._shader.set_vec3_glm(self.camera.cam_pos, 'viewPos')
        self._should_update_view = False

    def init_scene(self):
        self._shader.init()
        self._sphere.init_vao()
        self._cylinder.init_vao()
        self._plane.init_vao()
        self.update_view()
        self._shader.set_vec3_glm(glm.vec3(*self._light_position), 'lightPos')
        self._shader.set_vec3_glm(glm.vec3(1.), 'lightColor')
        self._shader.set_vec3_glm(glm.vec3(1.), 'objectColor')

    def set_crystal(self, crystal: SceneCrystal):
        self._should_redraw = True
        self._should_update_view = True
        self._crystal = crystal
        self._cylinder_matrices = _get_cylinder_matrices(crystal.unit_vectors)
        self.camera.cam_target = glm.vec3(*np.add.reduce(crystal.unit_vectors) / 2)

    def set_plane(self, miller_indices: Vec3):
        if not self._crystal:
            return
        self._show_plane = True

    def remove_plane(self):
        self._show_plane = None

    @property
    def crystal(self) -> SceneCrystal:
        return self._crystal

    def clear(self):
        self._should_redraw = True
        self._crystal = None
        self._cylinder_matrices = []

    def set_backcolor(self, backcolor: Vec4):
        self._should_redraw = True
        self._backcolor = backcolor

    def draw(self):
        self._should_redraw = False

        gl.glClearColor(*self._backcolor)

        if self._navigation.should_move():
            self.navigation.move_camera()
            self.update_view()

        elif self._should_update_view:
            self.update_view()

        if not self._crystal:
            return

        self._draw_atoms()
        self._draw_unit_cell()

        if self._show_plane:
            self._draw_plane()

    def _draw_plane(self):
        self._shader.set_vec3_glm(glm.vec3(0, 1, 0), 'objectColor')
        self._plane.draw()

    def _draw_atoms(self):
        for atom in self._crystal.atoms:
            self._shader.set_mat4_glm(_atom_model_mat(atom.coords), 'model')
            self._shader.set_vec3_glm(glm.vec3(*atom.color), 'objectColor')
            self._sphere.draw()

    def _draw_unit_cell(self):
        self._shader.set_vec3_glm(glm.vec3(0.3, 0.3, 0.3), 'objectColor')

        for cylinder_mat4 in self._cylinder_matrices:
            self._shader.set_mat4_glm(cylinder_mat4, 'model')
            self._cylinder.draw()


def _get_cylinder_matrices(unit_vectors: UnitVectors, radius: float = 0.02):
    cylinder_matrices = []
    for center, direction in _generate_unitcell_coords(unit_vectors):
        cylinder_matrices.append(_init_cylinder_mat4(center, direction, radius))
    return cylinder_matrices


def _init_cylinder_mat4(center: glm.dvec3, direction: glm.dvec3, radius: float = 0.02):
    init_vector = glm.vec3(0, 1, 0)
    length = glm.length(direction)

    angle = _angle_between(direction, init_vector)
    translate_vector = direction / 2 + center

    model = glm.translate(glm.mat4(1.), translate_vector)

    if angle:
        model = glm.rotate(model, angle, glm.cross(init_vector, glm.normalize(direction)))

    model = glm.scale(model, glm.vec3(radius, length, radius))
    return model


def _generate_unitcell_coords(unit_vectors: UnitVectors) -> Generator[Tuple[glm.dvec3, glm.dvec3], None, None]:
    zero_vector = glm.vec3(0.)

    a = glm.vec3(*unit_vectors.a)
    b = glm.vec3(*unit_vectors.b)
    c = glm.vec3(*unit_vectors.c)

    yield zero_vector, a
    yield zero_vector, b
    yield zero_vector, c

    yield a, b
    yield a, c

    yield b, a
    yield b, c

    yield c, a
    yield c, b

    yield a + b, c
    yield b + c, a
    yield c + a, b


def _atom_model_mat(atom_coords, radius: float = 0.2):
    atom_model = glm.translate(glm.mat4(1.), glm.vec3(*atom_coords))
    return glm.scale(atom_model, glm.vec3(radius))


def _angle_between(v1, v2):
    v1_u = glm.normalize(v1)
    v2_u = glm.normalize(v2)
    return glm.acos(np.clip(glm.dot(v1_u, v2_u), -1.0, 1.0))
