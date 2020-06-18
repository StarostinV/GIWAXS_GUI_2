from copy import deepcopy
from typing import List, Tuple

from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject

from .roi import Roi, RoiTypes
from .roi_data import RoiData
from ..file_manager import FileManager, ImageKey
from ..geometry_holder import GeometryHolder


def _check_non_empty(func):
    def wrapper(self, *args, **kwargs):
        if not self._current_key:
            return
        else:
            return func(self, *args, **kwargs)

    return wrapper


class RoiDict(QObject):
    sig_roi_created = pyqtSignal(tuple)
    sig_roi_deleted = pyqtSignal(tuple)
    sig_roi_moved = pyqtSignal(tuple, str)

    sig_selected = pyqtSignal(tuple)
    sig_one_selected = pyqtSignal(int)
    sig_roi_renamed = pyqtSignal(int)
    sig_fixed = pyqtSignal(tuple)
    sig_unfixed = pyqtSignal(tuple)

    sig_type_changed = pyqtSignal(int)
    sigFitRoisOpen = pyqtSignal(list)

    EMIT_NAME = 'RoiDict'

    def __init__(self, file_manager: FileManager, geometry_holder: GeometryHolder):
        super().__init__()
        self._geometry_holder: GeometryHolder = geometry_holder
        self._fm: FileManager = file_manager
        self._roi_data: RoiData = RoiData()
        self._current_key: ImageKey or None = None
        self._copied_rois: CopiedRois = CopiedRois()

    @property
    def is_copied(self):
        return len(self._copied_rois) > 0

    @property
    def ring_bounds(self) -> Tuple[float, float]:
        return self._geometry_holder.geometry.ring_bounds

    @_check_non_empty
    def save_state(self):
        if len(self._roi_data):
            self._fm.rois_data[self._current_key] = self._roi_data
        else:
            del self._fm.rois_data[self._current_key]

    def clear(self):
        if len(self._roi_data):
            self.sig_roi_deleted.emit(tuple(self.keys()))
            self._roi_data.clear()

    def save_and_clear(self):
        self.save_state()
        self.clear()

    def change_image(self, image_key: ImageKey):
        self.clear()
        self._current_key = image_key
        if not self._current_key:
            return
        self._update()

    # def _update_real_time(self):
    #
    #     roi_data = self._fm.rois_data[self._current_key] or RoiData()
    #     prev_key = self._current_key.get_previous()
    #     if prev_key:
    #         prev_data = self._fm.rois_data[prev_key] or RoiData()
    #     else:
    #         prev_data = RoiData()
    #
    #     self._merge_data(roi_data, prev_data)

    def _update(self):
        self._roi_data = self._fm.rois_data[self._current_key] or RoiData()
        self._roi_data.change_ring_bounds(self._geometry_holder.geometry.ring_bounds)
        if len(self._roi_data):
            self.sig_roi_created.emit(tuple(self.keys()))

    def _merge_data(self, roi_data: RoiData, prev_data: RoiData = None):
        prev_data = prev_data or {}

        to_move = []
        to_create = []
        to_delete = []

        def _add_roi(roi_):
            key_ = roi_.key
            if key_ in self.keys():
                prev_roi = self[key_]
                if prev_roi.deleted and roi_.deleted:
                    pass
                elif prev_roi.deleted and not roi_.deleted:
                    to_create.append(key_)
                elif not prev_roi.deleted and not roi_.deleted:
                    to_move.append(key_)
                elif not prev_roi.deleted and roi_.deleted:
                    to_delete.append(key_)
                roi_.active = prev_roi.active
                prev_roi.update(roi_)

            else:
                self._roi_data.add_roi(roi_)
                if not roi_.deleted:
                    to_create.append(key_)

        for key in set(roi_data.keys()).union(prev_data.keys()).union(self.keys()):
            if key in roi_data:
                _add_roi(roi_data[key])
            elif key in prev_data:
                _add_roi(prev_data[key])
            else:
                roi = self[key]
                if not roi.deleted:
                    roi.deleted = True
                    to_delete.append(key)

        if to_move:
            self.sig_roi_moved.emit(tuple(to_move), self.EMIT_NAME)
        if to_create:
            self.sig_roi_created.emit(tuple(to_create))
        if to_delete:
            self.sig_roi_deleted.emit(tuple(to_delete))

    @property
    def selected_rois(self) -> List[Roi]:
        return self._roi_data.selected_rois

    def keys(self):
        yield from self._roi_data.keys()

    def values(self):
        yield from self._roi_data.values()

    def items(self):
        yield from self._roi_data.items()

    def __getitem__(self, item: int) -> Roi:
        return self._roi_data[item]

    @pyqtSlot(int, name='select')
    def select(self, key: int):
        change_select = self._roi_data.select(key)
        if change_select:
            self.sig_selected.emit(change_select)
            if self._roi_data.selected_num == 1:
                self.sig_one_selected.emit(next(iter(self._roi_data.selected_keys)))

    @pyqtSlot(int, name='shift_select')
    def shift_select(self, key: int):
        self._roi_data.shift_select(key)
        self.sig_selected.emit((key,))
        if self._roi_data.selected_num == 1:
            self.sig_one_selected.emit(next(iter(self._roi_data.selected_keys)))

    @pyqtSlot(name='selectAll')
    @_check_non_empty
    def select_all(self) -> None:
        self._emit_select(self._roi_data.select_all())

    @pyqtSlot(name='unselectAll')
    @_check_non_empty
    def unselect_all(self):
        self._emit_select(self._roi_data.unselect_all())

    @pyqtSlot(name='deleteSelected')
    @_check_non_empty
    def delete_selected_roi(self):
        for key in list(self._roi_data.selected_keys):
            self.delete_roi(key)

    @pyqtSlot(int, str, name='changeName')
    def change_name(self, key: int, name: str):
        try:
            self[key].name = name
            self.sig_roi_renamed.emit(key)
        except KeyError:
            return

    def _emit_select(self, keys: List[int]):
        if keys:
            self.sig_selected.emit(tuple(keys))
        if self._roi_data.selected_num == 1:
            self.sig_one_selected.emit(next(iter(self._roi_data.selected_keys)))

    def add_roi(self, roi: Roi) -> None:
        self._roi_data.add_roi(roi)
        self.sig_roi_created.emit((roi.key,))
        if roi.active:
            self._emit_select((roi.key,))

    def add_rois(self, roi_list: List[Roi]):
        to_select = self._roi_data.add_rois(roi_list)
        self.sig_roi_created.emit(tuple(roi.key for roi in roi_list))
        self._emit_select(to_select)

    @_check_non_empty
    def delete_roi(self, key: int):
        self._roi_data.delete_roi(key)
        self.sig_roi_deleted.emit((key,))

    @_check_non_empty
    def create_roi(self, radius: float = None, width: float = None, **params) -> Roi:
        d = self._default_params()
        d.update(params)
        if radius and width:
            d.update(radius=radius, width=width)
        roi = self._roi_data.create_roi(**d)
        self.sig_roi_created.emit((roi.key,))
        if roi.active:
            self._emit_select((roi.key,))
        return roi

    @pyqtSlot(tuple, name='change_ring_bounds')
    def change_ring_bounds(self, bounds: Tuple[float, float]):
        keys = self._roi_data.change_ring_bounds(bounds)
        if keys:
            self.sig_roi_moved.emit(tuple(keys), self.EMIT_NAME)

    @pyqtSlot(name='on_scale_changed')
    def on_scale_changed(self):
        self._roi_data.on_scale_changed(self._geometry_holder.geometry.scale_change)
        self.sig_roi_moved.emit(tuple(self.keys()), self.EMIT_NAME)

    def _default_params(self) -> dict:
        r0, r1 = self._geometry_holder.geometry.r_range
        r0 *= self._geometry_holder.geometry.scale
        r1 *= self._geometry_holder.geometry.scale
        radius = (r0 + r1) / 2
        width = (r1 - r0) / 10
        angle, angle_std = self.ring_bounds
        return dict(radius=radius, width=width, angle=angle, angle_std=angle_std)

    @pyqtSlot(int, str, name='moveRoi')
    def move_roi(self, key: int, name: str):
        self.select(key)
        self.sig_roi_moved.emit((key,), name)
        angle, angle_std = self.ring_bounds
        roi = self[key]
        if roi.type == RoiTypes.ring and (roi.angle != angle or roi.angle_std != angle_std):
            roi.type = RoiTypes.segment
            self.sig_type_changed.emit(key)

    @pyqtSlot(int, name='roiTypeChanged')
    def change_roi_type(self, key: int):
        try:
            roi = self[key]
            if roi.type == RoiTypes.ring and (roi.angle, roi.angle_std) != self.ring_bounds:
                roi.angle, roi.angle_std = self.ring_bounds
                self.sig_roi_moved.emit((key,), self.EMIT_NAME)
        except KeyError:
            return
        self.sig_type_changed.emit(key)

    @pyqtSlot(name='fixAll')
    def fix_all(self, only_selected: bool = False):
        keys = []
        for roi in self.values():
            if only_selected and not roi.active:
                continue
            if roi.movable:
                roi.movable = False
                keys.append(roi.key)
        if keys:
            self.sig_fixed.emit(tuple(keys))

    @pyqtSlot(name='fixSelected')
    def fix_selected(self):
        self.fix_all(True)

    @pyqtSlot(name='unfixAll')
    def unfix_all(self, only_selected: bool = False):
        keys = []
        for roi in self.values():
            if only_selected and not roi.active:
                continue
            if not roi.movable:
                roi.movable = True
                keys.append(roi.key)
        if keys:
            self.sig_unfixed.emit(tuple(keys))

    @pyqtSlot(name='unfixSelected')
    def unfix_selected(self):
        self.unfix_all(True)

    @pyqtSlot(int, name='fixRoi')
    def fix_roi(self, key: int):
        try:
            self[key].movable = False
            self.sig_fixed.emit((key,))
        except KeyError:
            return

    @pyqtSlot(int, name='unfixRoi')
    def unfix_roi(self, key: int):
        try:
            self[key].movable = True
            self.sig_unfixed.emit((key,))
        except KeyError:
            return

    def copy_rois(self, key: int or str = 'selected'):
        if key == 'selected':
            rois = self.selected_rois
        elif key == 'all':
            rois = list(self.values())
        else:
            try:
                rois = [self[key]]
            except KeyError:
                return
        if rois:
            self._copied_rois.copy_rois(rois, self._geometry_holder.geometry)

    def paste_rois(self):
        if not self._current_key or not len(self._copied_rois):
            return
        self.add_rois(self._copied_rois.paste(self._geometry_holder.geometry))

    @pyqtSlot(bool, name='openFitRois')
    def open_fit_rois(self, only_selected: bool):
        if only_selected:
            rois = deepcopy(self.selected_rois)
        else:
            rois = deepcopy(list(self.values()))
        if rois:
            self.sigFitRoisOpen.emit(rois)

    def apply_fit(self, rois: List[Roi], image_key: ImageKey):

        if self._current_key == image_key:
            keys_to_create, keys_to_move = self._roi_data.apply_fit(rois)
            self.sig_roi_created.emit(keys_to_create)
            self.sig_roi_moved.emit(keys_to_move, self.EMIT_NAME)
            self.sig_fixed.emit(keys_to_move)
            self.sig_selected.emit(keys_to_move)

        else:
            roi_data = self._fm.rois_data[image_key] or RoiData()
            roi_data.apply_fit(rois)
            self._fm.rois_data[image_key] = roi_data


class CopiedRois(object):
    def __init__(self, rois: List[Roi] = None, geometry=None):
        self._rois = None
        self._scale = None
        self._bounds = None

        if rois and geometry:
            self.copy_rois(rois, geometry)

    def __len__(self):
        return len(self._rois) if self._rois else 0

    def copy_rois(self, rois: List[Roi], geometry):
        self._rois = deepcopy(rois)

        for roi in self._rois:
            roi.active = True

        self._scale = geometry.scale
        self._bounds = geometry.ring_bounds

    def paste(self, geometry, *, clear_keys: bool = True,
              clear: bool = False):
        if not self._rois:
            return

        if clear:
            rois = self._rois
            self.clear()
        else:
            rois = deepcopy(self._rois)

        if self._scale != geometry.scale:
            s = geometry.scale / self._scale
            for roi in rois:
                roi.radius *= s
                roi.width *= s
        if self._bounds != geometry.ring_bounds:
            for roi in rois:
                if roi.type == RoiTypes.ring:
                    roi.angle, roi.angle_std = geometry.ring_bounds
        if clear_keys:
            for roi in rois:
                roi.key = None

        return rois

    def clear(self):
        self._rois = None
        self._scale = None
        self._bounds = None
