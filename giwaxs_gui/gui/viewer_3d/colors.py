from PyQt5.QtGui import QColor

from crystals import Crystal


class CrystalColors(object):
    _COLORMAP = ['gold', 'red', 'blue', 'green', 'gray'] + ['white'] * 40

    _PREDEFINED_COLORS: dict = {
        'Au': 'gold',
        'C': 'green',
        'Pl': 'blue',
    }

    def __init__(self):
        self._crystal = None
        self._color_dict = {}

    @property
    def crystal(self):
        return self._crystal

    def set_crystal(self, crystal: Crystal):
        self._crystal = crystal
        self._make_color_dict()

    def _make_color_dict(self):
        atom_set: set = {atom.element for atom in self.crystal}
        cmap = iter(self._COLORMAP)
        self._color_dict = {}

        for element in atom_set:
            if element in self._PREDEFINED_COLORS:
                self._color_dict[element] = QColor(self._PREDEFINED_COLORS[element])
            else:
                self._color_dict[element] = QColor(next(cmap))

        self._PREDEFINED_COLORS.update(**self._color_dict)

    def set_color(self, element: str, color: QColor):
        self._color_dict[element] = color
        self._PREDEFINED_COLORS[element] = color

    def __getitem__(self, item):
        return self._color_dict.get(item, QColor('black'))

    def __iter__(self):
        yield from self._color_dict.items()
