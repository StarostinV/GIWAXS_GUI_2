from abc import abstractmethod
from typing import Dict

from .abstract_roi_widget import AbstractRoiWidget
from ...app.app import App
from ...app.rois.roi import Roi


class AbstractRoiHolder(object):
    def __init__(self, name: str):
        self._name = name
        self._roi_dict = App().roi_dict
        self._roi_widgets: Dict[int, AbstractRoiWidget] = {}
        self._init_connect()

    def _init_connect(self):
        self._roi_dict.sig_roi_created.connect(self._create_roi)
        self._roi_dict.sig_roi_deleted.connect(self._delete_roi)
        self._roi_dict.sig_roi_moved.connect(self._move_rois)
        self._roi_dict.sig_selected.connect(self._update_select)
        self._roi_dict.sig_fixed.connect(self._fix_rois)
        self._roi_dict.sig_unfixed.connect(self._unfix_rois)

    def _create_roi(self, keys: tuple):
        for key in keys:
            self._roi_widgets[key] = self._make_roi_widget(self._roi_dict[key])
            self._connect_roi_widget(self._roi_widgets[key])

    def _move_rois(self, keys: tuple, name: str):
        if name != self._name:
            for key in keys:
                try:
                    self._roi_widgets[key].move_roi()
                except KeyError:
                    pass

    def _connect_roi_widget(self, roi_widget: AbstractRoiWidget):
        roi_widget.sigRoiMoved.connect(
            lambda k: self._roi_dict.move_roi(k, self._name))
        roi_widget.sigSelected.connect(self._roi_dict.select)
        roi_widget.sigShiftSelected.connect(self._roi_dict.shift_select)

    def _update_select(self, keys: tuple):
        for key in keys:
            self._roi_widgets[key].update_select()

    def _delete_roi(self, keys: tuple):
        for key in keys:
            try:
                self._delete_roi_widget(self._roi_widgets.pop(key))
            except KeyError:
                pass

    def _fix_rois(self, keys: tuple):
        for key in keys:
            try:
                self._roi_widgets[key].fix()
            except KeyError:
                pass

    def _unfix_rois(self, keys: tuple):
        for key in keys:
            try:
                self._roi_widgets[key].unfix()
            except KeyError:
                pass

    @abstractmethod
    def _delete_roi_widget(self, roi_widget) -> None:
        pass

    @abstractmethod
    def _make_roi_widget(self, roi: Roi) -> AbstractRoiWidget:
        pass
