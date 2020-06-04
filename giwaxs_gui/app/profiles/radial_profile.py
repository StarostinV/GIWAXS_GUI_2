# -*- coding: utf-8 -*-

from .basic_profile import BasicProfile


class RadialProfile(BasicProfile):
    def __init__(self, image_holder, parent=None):
        self.image_holder = image_holder
        super().__init__(parent)

    def update_data_from_source(self):
        image_holder = self.image_holder
        profile = image_holder.get_radial_profile()
        if profile is None:
            return
        r_axis = image_holder.geometry.r_axis
        if r_axis is not None and r_axis.size == profile.size:
            self.set_data(profile, r_axis)
