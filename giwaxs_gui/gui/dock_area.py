import logging
from collections import defaultdict

from pyqtgraph.dockarea import DockArea, Dock

from ..app import App
from .image_viewer import Basic2DImageWidget
from .polar_image_viewer import PolarImageViewer
from .file_viewer.viewer import FileViewer
from .profiles.radial_profile_widget import RadialProfileWidget
from .profiles.angular_profile_widget import AngularProfileWidget
from .fitting import FitWidget


logger = logging.getLogger(__name__)


class AppDockArea(DockArea):
    def __init__(self, parent=None):
        DockArea.__init__(self, parent=parent)
        self._status_dict = defaultdict(lambda: True)
        self.app = App()

        self.__init_image_viewer()
        self.__init_polar_viewer()
        # self.__init_control_widget__()
        self.__init_radial_widget()
        self.__init_file_widget()
        self.__init_angular_widget()

        self._DOCK_DICT = {'image_view': self.image_viewer_dock,
                           'polar': self.polar_viewer_dock,
                           'radial_profile': self.radial_profile_dock,
                           # 'control': self.control_dock,
                           'file_widget': self.file_dock,
                           'angular_profile': self.angular_profile_dock}
        self._apply_default_view()
        self._fit_widget = None

        self.app.image_holder.sigFitOpen.connect(self._open_fit_widget)

    def _open_fit_widget(self, fit_object):
        fit_widget = FitWidget(fit_object, parent=self.parent())
        fit_widget.sigFitApplyActiveImage.connect(self.app.image_holder.apply_fit)

    def _apply_default_view(self):
        self.show_hide_docks('polar')
        self.show_hide_docks('radial_profile')
        self.show_hide_docks('angular_profile')
        # self.show_hide_docks('control')

    def __init_image_viewer(self):
        self.image_view = Basic2DImageWidget(self)
        dock = Dock('ImageViewer')
        dock.addWidget(self.image_view)
        self.addDock(dock, size=(1000, 1000))
        self.image_viewer_dock = dock

    def __init_polar_viewer(self):
        self.polar_view = PolarImageViewer(self)
        dock = Dock('PolarImageViewer')
        dock.addWidget(self.polar_view)
        self.addDock(dock, position='right')
        self.polar_viewer_dock = dock

    def __init_radial_widget(self):
        self.radial_profile = RadialProfileWidget(self)
        dock = Dock('Radial Profile')
        dock.addWidget(self.radial_profile)
        self.addDock(dock, position='bottom')
        self.radial_profile_dock = dock

    def __init_angular_widget(self):
        self.angular_profile = AngularProfileWidget(self)
        dock = Dock('Angular Profile')
        dock.addWidget(self.angular_profile)
        self.addDock(dock, position='bottom')
        self.angular_profile_dock = dock

    # def __init_control_widget__(self):
    #     self.control_widget = ControlWidget(
    #         self.get_lower_connector('ControlWidget'), self)
    #     control_dock = Dock('Segments')
    #     control_dock.addWidget(self.control_widget)
    #     self.addDock(control_dock, position='right')
    #     self.control_dock = control_dock

    def __init_file_widget(self):
        self.file_widget = FileViewer(self.app.fm, self)
        self.file_dock = Dock('Files')
        self.file_dock.addWidget(self.file_widget)
        self.addDock(self.file_dock, position='left')

    def show_hide_docks(self, dock_name: str):
        assert dock_name in self._DOCK_DICT.keys()
        dock = self._DOCK_DICT[dock_name]
        status = self._status_dict[dock_name]
        if status:
            dock.hide()
        else:
            dock.show()
        self._status_dict[dock_name] = not status
