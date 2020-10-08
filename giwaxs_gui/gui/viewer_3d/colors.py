from typing import Dict, List

from PyQt5.QtGui import QColor

from .scene import SceneCrystal, Atom


class CrystalColors(object):
    _COLORMAP = ['gold', 'red', 'blue', 'green', 'gray'] + ['white'] * 40

    _PREDEFINED_COLORS: dict = {
        'Au': 'gold',
        'C': 'green',
        'Pl': 'blue',
    }

    def __init__(self):
        self._crystal = None
        self._color_dict: Dict[str, QColor] = {}
        self._atoms_dict: Dict[str, List[Atom, ...]] = {}

    @property
    def crystal(self):
        return self._crystal

    def set_crystal(self, crystal: SceneCrystal):
        self._crystal = crystal
        self._make_color_dict()

    def _make_color_dict(self):
        element_set: set = {atom.element for atom in self.crystal.atoms}
        colormap = iter(self._COLORMAP)

        self._atoms_dict = {}
        self._color_dict = {}

        for element in element_set:
            if element in self._PREDEFINED_COLORS:
                self._color_dict[element] = QColor(self._PREDEFINED_COLORS[element])
            else:
                self._color_dict[element] = QColor(next(colormap))

        for atom in self.crystal.atoms:
            if atom.element not in self._atoms_dict:
                self._atoms_dict[atom.element] = []
            self._atoms_dict[atom.element].append(atom)

        for element in element_set:
            self._update_atoms(element)

        self._PREDEFINED_COLORS.update(**self._color_dict)

    def _update_atoms(self, element: str):
        color = self._color_dict[element]
        r, g, b = color.red() / 255, color.green() / 255, color.blue() / 255
        for atom in self._atoms_dict[element]:
            atom.set_color((r, g, b))

    def set_color(self, element: str, color: QColor):
        self._color_dict[element] = color
        self._PREDEFINED_COLORS[element] = color
        self._update_atoms(element)

    def __getitem__(self, item):
        return self._color_dict.get(item, QColor('black'))

    def __iter__(self):
        yield from self._color_dict.items()
