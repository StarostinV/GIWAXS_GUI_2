from abc import abstractmethod
from pathlib import Path

import numpy as np
import OpenGL.GL as gl
import ctypes

MESH_DIR: Path = Path(__file__).parent / 'meshes'


def mesh_path(name: str) -> str:
    return str((MESH_DIR / f'{name}.npy').resolve())


class Mesh(object):
    @abstractmethod
    def init_vao(self):
        pass

    @abstractmethod
    def copy(self):
        pass

    @abstractmethod
    def draw(self):
        pass


class BasicMesh(Mesh):
    def __init__(self, *args, vertices: np.ndarray = None, **kwargs):
        if vertices is not None:
            self._vertices = vertices
        else:
            self._vertices = self._init_vertices(*args, **kwargs)

    @abstractmethod
    def _init_vertices(self, *args, **kwargs) -> np.ndarray:
        pass

    def copy(self):
        return self.__class__(vertices=self._vertices)

    def save(self):
        np.save(mesh_path(self.__class__.__name__), self._vertices)

    @classmethod
    def load(cls, *args, **kwargs):
        try:
            return cls(vertices=np.load(mesh_path(cls.__name__)))
        except (FileNotFoundError, IOError):
            return cls(*args, **kwargs)


class NormalsMeshMixin(object):
    def init_vao(self):
        self._vao = gl.glGenVertexArrays(1)
        vbo = gl.glGenBuffers(1)

        gl.glBindVertexArray(self._vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER,
                        self._vertices.nbytes,
                        self._vertices, gl.GL_STATIC_DRAW)

        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 6 * np.dtype('f').itemsize, None)
        gl.glEnableVertexAttribArray(0)
        gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, gl.GL_FALSE, 6 * np.dtype('f').itemsize,
                                 ctypes.c_void_p(3 * np.dtype('f').itemsize))
        gl.glEnableVertexAttribArray(1)


class SphereMesh(NormalsMeshMixin, BasicMesh):
    def __init__(self, n_v: int = 30, n_h: int = 30, vertices: np.ndarray = None):
        super().__init__(vertices=vertices, n_v=n_v, n_h=n_h)

        self._num_of_triangles = int(self._vertices.size / 3)
        self._vao = None

    def draw(self):
        gl.glBindVertexArray(self._vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self._num_of_triangles)

    def _init_vertices(self, n_v: int = 20, n_h: int = 20):
        phi_step = 180 // n_v
        theta_step = 360 // n_h
        vertices_dict = {}
        pi_k = np.pi / 180

        for phi in range(-90, 90 + phi_step, phi_step):
            phi_rad = phi * pi_k
            z = np.sin(phi_rad)
            cos_phi = np.cos(phi_rad)

            for theta in range(0, 360 + theta_step, theta_step):
                theta_rad = theta * pi_k
                x = cos_phi * np.cos(theta_rad)
                y = cos_phi * np.sin(theta_rad)
                vertices_dict[(phi, theta)] = np.array([x, y, z])

        def vertex(phi, theta):
            ver = vertices_dict[(phi, theta)]
            return (*ver, *(ver / np.linalg.norm(ver)))

        vertices = []

        for phi in range(-90, 90, phi_step):

            for theta in range(0, 360, theta_step):
                vertices.append(vertex(phi, theta))
                vertices.append(vertex(phi + phi_step, theta))
                vertices.append(vertex(phi + phi_step, theta + theta_step))

                vertices.append(vertex(phi, theta))
                vertices.append(vertex(phi + phi_step, theta + theta_step))
                vertices.append(vertex(phi, theta + theta_step))

        return np.array(vertices, 'f')


class SimpleCubeMesh(BasicMesh):
    def init_vao(self):
        self._vao = gl.glGenVertexArrays(1)
        vbo = gl.glGenBuffers(1)

        gl.glBindVertexArray(self._vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER,
                        self._vertices.nbytes,
                        self._vertices, gl.GL_STATIC_DRAW)

        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 3 * np.dtype('f').itemsize, None)
        gl.glEnableVertexAttribArray(0)

    def draw(self):
        gl.glBindVertexArray(self._vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 36)

    def _init_vertices(self):
        yz = []
        s = 0.5

        # one side: 2 triangles, 6 vertexes
        yz.append((s, s, s))
        yz.append((s, s, -s))
        yz.append((s, -s, s))

        yz.append((s, s, -s))
        yz.append((s, -s, -s))
        yz.append((s, -s, s))

        # negative side: different direction

        yz.append((-s, s, s))
        yz.append((-s, -s, s))
        yz.append((-s, s, -s))

        yz.append((-s, s, -s))
        yz.append((-s, -s, s))
        yz.append((-s, -s, -s))

        # flip x and y

        xz = [(a[1], a[0], a[2]) for a in yz]

        # flip z and x

        xy = [(a[2], a[1], a[0]) for a in yz]

        return np.array(yz + xz + xy, 'f').flatten()


class CubeMesh(NormalsMeshMixin, BasicMesh):
    def draw(self):
        gl.glBindVertexArray(self._vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 36)

    def _init_vertices(self):
        yz = []
        s = 0.5

        # one side: 2 triangles, 6 vertexes. 3 coords of vertex + normal vector
        yz.append((s, s, s, 1., 0., 0.))
        yz.append((s, s, -s, 1., 0., 0.))
        yz.append((s, -s, s, 1., 0., 0.))

        yz.append((s, s, -s, 1., 0., 0.))
        yz.append((s, -s, -s, 1., 0., 0.))
        yz.append((s, -s, s, 1., 0., 0.))

        # negative side: different direction

        yz.append((-s, s, s, -1., 0., 0.))
        yz.append((-s, -s, s, -1., 0., 0.))
        yz.append((-s, s, -s, -1., 0., 0.))

        yz.append((-s, s, -s, -1., 0., 0.))
        yz.append((-s, -s, s, -1., 0., 0.))
        yz.append((-s, -s, -s, -1., 0., 0.))

        # flip x and y

        xz = [(a[1], a[0], a[2], a[3 + 1], a[3], a[3 + 2]) for a in yz]

        # flip z and x

        xy = [(a[2], a[1], a[0], a[3 + 2], a[3 + 1], a[3]) for a in yz]

        return np.array(yz + xz + xy, 'f').flatten()


class PlaneMesh(Mesh):
    def __init__(self):
        self._vao = None
        self._vbo = None
        self._vertices = None
        self.set_base_vectors(
            np.array([0, 0, 0]),
            np.array([1, 0, 0]),
            np.array([0, 1, 0])
        )

    def set_base_vectors(self,
                         vec1: np.ndarray,
                         vec2: np.ndarray,
                         vec3: np.ndarray):
        vertices = []
        n = np.cross(vec2 - vec1, vec3 - vec1)
        n = n / (np.linalg.norm(n) or 1)
        vertices.extend([*vec1, *n])
        vertices.extend([*vec2, *n])
        vertices.extend([*vec3, *n])
        self._vertices = np.array(vertices, 'f').flatten()

    def update_vao(self):
        gl.glBindVertexArray(self._vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self._vbo)
        gl.glBufferSubData(gl.GL_ARRAY_BUFFER, 0,
                           self._vertices.nbytes,
                           self._vertices, gl.GL_DYNAMIC_DRAW)

    def init_vao(self):
        self._vao = gl.glGenVertexArrays(1)
        self._vbo = gl.glGenBuffers(1)

        gl.glBindVertexArray(self._vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self._vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER,
                        self._vertices.nbytes,
                        self._vertices, gl.GL_DYNAMIC_DRAW)

        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 6 * np.dtype('f').itemsize, None)
        gl.glEnableVertexAttribArray(0)
        gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, gl.GL_FALSE, 6 * np.dtype('f').itemsize,
                                 ctypes.c_void_p(3 * np.dtype('f').itemsize))
        gl.glEnableVertexAttribArray(1)

    def copy(self):
        return PlaneMesh()

    def draw(self):
        gl.glBindVertexArray(self._vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 1)


class CylinderMesh(NormalsMeshMixin, BasicMesh):
    def __init__(self, n_h: int = 30, vertices: np.ndarray = None):
        super().__init__(vertices=vertices, n_h=n_h)

        self._num_of_triangles = int(self._vertices.size / 3)
        self._vao = None

    def draw(self):
        gl.glBindVertexArray(self._vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self._num_of_triangles)

    def _init_vertices(self, n_h: int = 30):
        vertices = []
        theta_step = 360 // n_h
        pi_k = np.pi / 180

        bottom_y = -0.5
        top_y = 0.5

        norm_down = (0, -1, 0)
        norm_up = (0, 1, 0)
        center_bottom = (0, bottom_y, 0)
        center_top = (0, top_y, 0)

        theta_dict = {theta: (np.cos(theta * pi_k), np.sin(theta * pi_k))
                      for theta in range(0, 360 + theta_step, theta_step)}

        for theta in range(0, 360, theta_step):
            x, z = theta_dict[theta]
            x1, z1 = theta_dict[theta + theta_step]

            side_norm = (x, 0, z)

            # triangle on the bottom
            vertices.append((x, bottom_y, z, *norm_down))
            vertices.append((x1, bottom_y, z1, *norm_down))
            vertices.append((*center_bottom, *norm_down))

            # triangle on the top
            vertices.append((x1, top_y, z1, *norm_up))
            vertices.append((x, top_y, z, *norm_up))
            vertices.append((*center_top, *norm_up))

            # side triangles
            vertices.append((x, bottom_y, z, *side_norm))
            vertices.append((x, top_y, z, *side_norm))
            vertices.append((x1, top_y, z1, *side_norm))

            vertices.append((x1, top_y, z1, *side_norm))
            vertices.append((x1, bottom_y, z1, *side_norm))
            vertices.append((x, bottom_y, z, *side_norm))

        return np.array(vertices, 'f').flatten()


if __name__ == '__main__':
    SphereMesh().save()
    CubeMesh().save()
    CylinderMesh().save()
