import pytest

from h5py import File
import numpy as np

from giwaxs_gui import App
from giwaxs_gui.app.data_manager import SavingParameters
from giwaxs_gui.app.geometry import Geometry


def test_save(project_1, project_1_info, tmp_path):
    h5path = tmp_path / 'data.h5'
    paths_dict = project_1_info.paths_dict()
    params = SavingParameters(paths_dict, h5path,
                              save_image=True,
                              save_polar_image=True)
    app = App()
    image_keys = list(project_1_info.get_all_image_keys())
    assert len(image_keys) > 0

    image_key_with_segments = image_keys[0]
    app.fm.change_image(image_key_with_segments)
    app.geometry_holder.set_beam_center((10, 10))
    app.geometry_holder.save_as_default()
    roi1 = app.roi_dict.create_roi(radius=2, width=5)
    roi2 = app.roi_dict.create_roi(radius=3, width=6)
    app.save_state()

    app.data_manager.save(params)

    compare_params_to_h5(params, str(h5path.resolve()))


def compare_params_to_h5(params: SavingParameters, h5path: str):
    app = App()
    paths_dict = params.selected_images

    with File(h5path, 'r') as f:
        assert len(list(f.keys())) == len(paths_dict)
        for folder_key, image_keys in paths_dict.items():
            if image_keys:
                assert folder_key.name in f.keys()

                folder_group = f[folder_key.name]
                folder_attrs = dict(folder_group.attrs)

                if params.save_geometries:
                    default_geometry = app.fm.geometries.default[folder_key]
                    if default_geometry:
                        assert default_geometry == Geometry.fromdict(folder_attrs)
                # if params.save_roi_metadata:
                #     roi_metadata = app.fm.rois_meta_data[folder_key]
                #     if roi_metadata:
                #         pass

                for image_key in image_keys:
                    assert image_key.name in folder_group.keys()
                    image_group = folder_group[image_key.name]
                    if params.save_image:
                        assert 'image' in image_group
                        assert np.all(image_key.get_image() == image_group['image'][()])
                    if params.save_polar_image:
                        assert 'polar_image' in image_group
                    if params.save_positions and app.fm.rois_data[image_key]:
                        assert 'roi_dict' in image_group
            else:
                assert folder_key.name not in f.keys()

        # for key in f.keys():
        #     folder_group = f[key]
        #     if params.save_geometries and app.fm.geometries.default[]
