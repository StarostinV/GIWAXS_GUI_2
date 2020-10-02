from collections import namedtuple
from typing import Generator, Tuple
from itertools import product

import numpy as np
from crystals import Crystal, Atom, Lattice

from PyQt5.QtGui import QVector3D, QColor, QQuaternion
from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.Qt3DCore import QTransform, QEntity

from PyQt5.Qt3DExtras import (
    Qt3DWindow,
    QDiffuseSpecularMaterial,
    QSphereMesh,
    QOrbitCameraController,
    QCylinderMesh,
    QPlaneMesh
)

from .legend import CrystalLegend

UnitVectors = namedtuple('UnitVectors', 'a b c')


class CrystalView(Qt3DWindow):
    def __init__(self, legend: CrystalLegend, crystal: Crystal = None):
        super().__init__()
        self._scene = None
        self._crystal = None
        self._unit_vectors = None
        self._camera_control = None

        self.wheel_speed: float = 1.
        self._materials_dict = {}
        self._init_camera()
        self._timer = self._init_timer()

        self.legend = legend
        self.legend.sigColorChanged.connect(self.set_atom_color)

        if crystal:
            self.set_crystal(crystal)

    def _init_camera(self, distance: int = 15):
        camera = self.camera()
        camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 1000)
        camera.setPosition(QVector3D(0, 0, distance))
        return camera

    def _init_timer(self):
        timer = QTimer(self)
        timer.setInterval(25)
        timer.timeout.connect(self._rotate_camera)
        return timer

    def wheelEvent(self, event):
        delta = - event.angleDelta().y() / 120  # 1 or -1
        self.set_camera_distance(delta=delta * self.wheel_speed)

    def set_camera_distance(self, *, distance: float = None, delta: float = None):
        if not distance and not delta:
            raise ValueError('Either distance or direction should be specified.')

        current_position = self.camera().position()
        if delta:
            direction = current_position.normalized() * delta
            new_position = current_position + direction * self.wheel_speed
        else:
            new_position = current_position.normalized() * abs(distance)

        if new_position.length():
            self.camera().setPosition(new_position)

    def start_rotation(self):
        self._timer.start()

    def stop_rotation(self):
        self._timer.stop()

    def _rotate_camera(self):
        self.camera().tiltAboutViewCenter(0.4)

    @property
    def unit_vectors(self):
        return self._unit_vectors

    @property
    def crystal(self):
        return self._crystal

    @property
    def camera_distance(self):
        return self.camera().position().length()

    def _update_camera_center(self):
        view_center = np.add.reduce(self.unit_vectors) / 2
        self.camera().setViewCenter(QVector3D(*view_center))

    def _init_camera_control(self):
        cam_controller = QOrbitCameraController(self._scene)
        cam_controller.setLinearSpeed(0)
        cam_controller.setLookSpeed(200)
        cam_controller.setCamera(self.camera())

        return cam_controller

    def clear_scene(self):
        if self._scene:
            for component in self._scene.components():
                self._scene.removeComponent(component)

        self._scene = QEntity()
        self.setRootEntity(self._scene)
        self._camera_control = self._init_camera_control()

    def set_crystal(self, crystal: Crystal):
        self.clear_scene()
        self._crystal = crystal
        self._unit_vectors = UnitVectors(*self._crystal.lattice_vectors)
        self._materials_dict = {}

        for atom in _generate_unitcell_atoms(self.crystal):
            color = self.legend.colors[atom.element]
            self.create_atom(atom, self._scene, color)

        for center, direction in self._generate_unitcell_coords():
            self.create_cylinder(self._scene, center, direction)

        view_center = np.add.reduce(self.unit_vectors) / 2
        self.camera().setViewCenter(QVector3D(*view_center))

    def _generate_unitcell_coords(self) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        zero_vector = np.array([0, 0, 0])

        yield zero_vector, self.unit_vectors.a
        yield zero_vector, self.unit_vectors.b
        yield zero_vector, self.unit_vectors.c

        yield self.unit_vectors.a, self.unit_vectors.b
        yield self.unit_vectors.a, self.unit_vectors.c

        yield self.unit_vectors.b, self.unit_vectors.a
        yield self.unit_vectors.b, self.unit_vectors.c

        yield self.unit_vectors.c, self.unit_vectors.a
        yield self.unit_vectors.c, self.unit_vectors.b

        yield self.unit_vectors.a + self.unit_vectors.b, self.unit_vectors.c
        yield self.unit_vectors.b + self.unit_vectors.c, self.unit_vectors.a
        yield self.unit_vectors.c + self.unit_vectors.a, self.unit_vectors.b

    def create_atom(self, atom: Atom, root_entity, color: QColor):
        if atom.element in self._materials_dict:
            material = self._materials_dict[atom.element]
        else:
            material = QDiffuseSpecularMaterial(root_entity)
            material.setDiffuse(color)
            material.setAmbient(color.darker(200))
            self._materials_dict[atom.element] = material

        sphere_entity = QEntity(root_entity)
        sphere_mesh = QSphereMesh()
        sphere_mesh.setRadius(0.5)
        sphere_transform = QTransform()
        sphere_transform.setTranslation(QVector3D(*atom.coords_cartesian))

        sphere_entity.addComponent(sphere_mesh)
        sphere_entity.addComponent(sphere_transform)
        sphere_entity.addComponent(material)

    @pyqtSlot(str, QColor, name='setAtomColor')
    def set_atom_color(self, element: str, color: QColor):
        if element in self._materials_dict:
            material = self._materials_dict[element]
            material.setDiffuse(color)
            material.setAmbient(color.darker(200))

    @staticmethod
    def create_cylinder(root_entity, center, direction):
        material = QDiffuseSpecularMaterial(root_entity)
        material.setDiffuse(QColor(200, 200, 200, 50))
        material.setAmbient(QColor(200, 200, 200, 50))

        cylinder_entity = QEntity(root_entity)
        cylinder_mesh = QCylinderMesh()

        length = np.linalg.norm(direction)
        translate_vector = center + direction / 2

        cylinder_mesh.setLength(length)
        cylinder_mesh.setRadius(0.02)

        cylinder_transform = QTransform()

        cylinder_transform.setRotation(_get_quaternion(direction))

        cylinder_transform.setTranslation(QVector3D(*translate_vector))

        cylinder_entity.addComponent(cylinder_mesh)
        cylinder_entity.addComponent(cylinder_transform)
        cylinder_entity.addComponent(material)

    @staticmethod
    def create_plane(root_entity, vector_1: np.ndarray, vector_2: np.ndarray):
        material = QDiffuseSpecularMaterial(root_entity)
        material.setDiffuse(QColor(200, 200, 200))
        material.setAmbient(QColor(200, 200, 200))

        plane_entity = QEntity(root_entity)
        plane_mesh = QPlaneMesh()
        plane_transform = QTransform()
        plane_mesh.setWidth(np.linalg.norm(vector_1))
        plane_mesh.setHeight(np.linalg.norm(vector_2))
        plane_mesh.setMirrored(False)

        translation_vector = (vector_1 + vector_2) / 2
        plane_transform.setRotation(_get_quaternion(np.cross(vector_1, vector_2)))
        plane_transform.setTranslation(QVector3D(*translation_vector))

        plane_entity.addComponent(plane_mesh)
        plane_entity.addComponent(plane_transform)
        plane_entity.addComponent(material)


def _generate_unitcell_atoms(crystal: Crystal):
    for atm in crystal:
        for factors in product(range(-2, 2), range(-2, 2), range(-2, 2)):
            coords = atm.coords_fractional + np.asarray(factors)
            if np.all(coords <= 1.1) and np.all(coords >= -0.1):
                yield Atom(
                    element=atm.element,
                    coords=coords,
                    lattice=Lattice(crystal.lattice_vectors),
                    displacement=atm.displacement,
                    magmom=atm.magmom,
                    occupancy=atm.occupancy,
                )


def _get_quaternion(direction: np.ndarray) -> QQuaternion:
    init_vector = np.array([0, 1, 0])

    a = np.cross(init_vector, direction)
    w = np.linalg.norm(direction) + np.dot(init_vector, direction)
    return _norm_q(w, a)


def _norm_q(w, vector):
    n = np.sqrt(w ** 2 + vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
    if n:
        w = w / n
        vector = vector / n
    return QQuaternion(w, QVector3D(*vector))
