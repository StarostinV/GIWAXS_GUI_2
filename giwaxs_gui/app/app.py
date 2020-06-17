import logging

from .rois.roi_dict import RoiDict
from .file_manager import FileManager
from .utils import SingletonMeta
from .geometry import Geometry
from .geometry_holder import GeometryHolder
from .image_holder import ImageHolder
from .profiles import RadialProfile, AngularProfile
from .debug_tracker import TrackQObjects


class App(metaclass=SingletonMeta):
    log = logging.getLogger(__name__)

    def __init__(self):
        self.fm: FileManager = FileManager()
        self.geometry_holder: GeometryHolder = GeometryHolder(self.fm)
        self.roi_dict: RoiDict = RoiDict(self.fm, self.geometry_holder)
        self.image_holder: ImageHolder = ImageHolder(self.fm, self.geometry_holder, self.roi_dict)
        self.radial_profile: RadialProfile = RadialProfile(self.image_holder, self.fm)
        self.angular_profile: AngularProfile = AngularProfile(self.image_holder)

        self.image_holder.sigPolarImageChanged.connect(self.radial_profile.update)
        self.image_holder.sigPolarImageChanged.connect(self.angular_profile.update)

        self.geometry_holder.sigScaleChanged.connect(self.roi_dict.on_scale_changed)
        self.geometry_holder.sigRingBoundsChanged.connect(self.roi_dict.change_ring_bounds)

        self.fm.sigActiveImageChanged.connect(self.image_holder.change_image)
        self.fm.sigProjectIsClosing.connect(self.save_state)

        if self.log.level <= logging.DEBUG:
            self.debug_tracker: TrackQObjects = TrackQObjects()
        else:
            self.debug_tracker: TrackQObjects = None

    def save_state(self):
        self.geometry_holder.save_state()
        self.roi_dict.save_state()
        # self.radial_profile.save_state()

    @property
    def image(self):
        return self.image_holder.image

    @property
    def polar_image(self):
        return self.image_holder.polar_image

    @property
    def geometry(self) -> Geometry:
        return self.geometry_holder.geometry

    def close(self):
        self.fm.close()
