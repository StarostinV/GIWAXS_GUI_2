from typing import Tuple
from pathlib import Path

import OpenGL.GL as gl
import glm
import numpy as np


class Shader(object):
    SHADERS_DIR = Path(__file__).parent / 'shaders'

    def __init__(self, *shaders: Tuple[str, int]):
        self._shaders: Tuple[Tuple[str, int], ...] = shaders
        self.__uniform_ids: dict = {}
        self.__id = None

    def init(self):
        shaders_lines = []

        for name, shader_type in self._shaders:
            with open(self.SHADERS_DIR / name, 'r') as f:
                shaders_lines.append((f.read(), shader_type))

        self.__id = create_shader_program(*shaders_lines)

    @property
    def id(self):
        return self.__id

    def use(self):
        gl.glUseProgram(self.id)

    def get_location(self, attr: str):
        if attr not in self.__uniform_ids:
            self.__uniform_ids[attr] = gl.glGetUniformLocation(self.id, attr)
        return self.__uniform_ids[attr]

    def set_mat4_glm(self, mat, attr: str):
        gl.glUniformMatrix4fv(self.get_location(attr), 1, gl.GL_FALSE, glm.value_ptr(mat))

    def set_vec3_glm(self, vec, attr: str):
        gl.glUniform3fv(self.get_location(attr), 1, glm.value_ptr(vec))

    def set_mat4(self, mat, attr: str):
        gl.glUniformMatrix4fv(self.get_location(attr), 1, gl.GL_FALSE, mat)

    def set_vec3(self, vec: np.ndarray, attr: str):
        gl.glUniform3fv(self.get_location(attr), 1, vec)


def create_shader(shader_code: str, shader_type) -> int:
    try:
        shader_id: int = gl.glCreateShader(shader_type)
        gl.glShaderSource(shader_id, shader_code)
        # second arg is number of lines

        gl.glCompileShader(shader_id)
        if gl.glGetShaderiv(shader_id, gl.GL_COMPILE_STATUS) != gl.GL_TRUE:
            info = gl.glGetShaderInfoLog(shader_id)
            raise RuntimeError(f'Shader compilation failed: {info}')
        return shader_id
    except Exception as err:
        raise RuntimeError(f'Failed creating shader {shader_type}.') from err


def create_shader_program(*shaders: Tuple[str, int]) -> int:
    shader_ids = [create_shader(shader_code, shader_type) for shader_code, shader_type in shaders]
    shader_program: int = gl.glCreateProgram()
    for shader_id in shader_ids:
        gl.glAttachShader(shader_program, shader_id)
    gl.glLinkProgram(shader_program)

    if gl.glGetProgramiv(shader_program, gl.GL_LINK_STATUS) != gl.GL_TRUE:
        info = gl.glGetShaderInfoLog(shader_program)
        raise RuntimeError(f'Shader program linking failed: {info}')

    for shader_id in shader_ids:
        gl.glDeleteShader(shader_id)

    return shader_program
