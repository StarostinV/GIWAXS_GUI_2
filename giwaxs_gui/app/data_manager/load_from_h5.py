from h5py import File, Group
from PIL import Image
from pathlib import Path

from ..geometry import Geometry
from ..rois import RoiData
from ..file_manager import ImagePathKey, FileManager


class LoadProjectFromH5(object):
    def __init__(self, fm: FileManager):
        self.fm = fm

    def __call__(self, project_path: Path, h5path: Path):
        self.fm.open_project(project_path)

        img_folder = project_path / 'Source images'
        img_folder.mkdir()

        with File(h5path, 'r') as f:
            for folder_name, group in f.items():

                folder_path = img_folder / folder_name
                folder_path.mkdir()

                folder_key = self.fm.add_root_path_to_project(folder_path)

                self.fm.geometries.default[folder_key] = Geometry.fromdict(dict(group.attrs))

                for idx, (img_name, img_data) in enumerate(_parse_imgs_from_h5_group(group)):
                    img_path = folder_path / img_name
                    img = img_data['image']
                    Image.fromarray(img).save(img_path)
                    img_key = ImagePathKey(folder_key, path=img_path, idx=idx)
                    folder_key._image_children.append(img_key)

                    self.fm.polar_images[img_key] = img_data.get('polar_image', None)
                    self.fm.rois_data[img_key] = img_data.get('roi_data', None)


def _parse_imgs_from_h5_group(h5group: Group, skip_empty_imgs: bool = False):
    for img_name, img_group in h5group.items():
        img_data = {}

        if 'roi_data' in img_group:
            roi_dict = {
                k: v[()] for k, v in img_group['roi_data'].items()
            }
            img_data['roi_data'] = RoiData.from_dict(roi_dict)

            if skip_empty_imgs and not len(img_data['roi_data']):
                continue

        elif skip_empty_imgs:
            continue

        for key in ('image', 'polar_image'):
            if key in img_group:
                img_data[key] = img_group[key][()]

        yield img_name, img_data
