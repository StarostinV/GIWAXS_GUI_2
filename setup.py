from setuptools import setup, find_packages
from pathlib import Path
import re

PACKAGE_NAME = 'giwaxs_gui'


def read(filename: str):
    with open(Path(__file__).parent / filename, mode='r', encoding='utf-8') as f:
        return f.read()


def get_version():
    version_file = f'{PACKAGE_NAME}/__version.py'
    with open(version_file, 'r') as f:
        file_str = f.read()

    mo = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", file_str, re.M)
    if mo:
        return mo.group(1)
    else:
        raise RuntimeError("Unable to find version string in %s." % (version_file,))


setup(
    name=PACKAGE_NAME,
    packages=find_packages(),
    version=get_version(),
    author='Vladimir Starostin',
    author_email='vladimir.starostin@uni-tuebingen.de',
    description='A GUI program for GIWAXS images analysis',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    license='GPLv3',
    python_requires='>=3.7.2',
    entry_points={
        'gui_scripts': [
            'giwaxs_gui = giwaxs_gui:main',
        ],
        'console_scripts': [
            'giwaxs_gui_update = giwaxs_gui.app.update:giwaxs_gui_update'],
    },
    install_requires=[
        'numpy>=1.18.1',
        'opencv-python>=4.0.0.0',
        'scipy>=1.4.1',
        'h5py>=2.10.0',
        'PyQt5',
        'pyqtgraph==0.11.0rc0',
        'read_edf',
        'Pillow',
        'requests',
        'qdarkstyle',
        'qdarkgraystyle'
    ],
    include_package_data=True,
    keywords='xray python giwaxs scientific-analysis',
    url='https://pypi.org/project/giwaxs-gui',
)
