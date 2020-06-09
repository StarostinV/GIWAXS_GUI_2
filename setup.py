from setuptools import setup, find_packages
from pathlib import Path


def read(filename: str):
    with open(Path(__file__).parent / filename, mode='r', encoding='utf-8') as f:
        return f.read()


setup(
        name='giwaxs_gui',
        packages=find_packages(),
        version='0.1.0',
        author='Vladimir Starostin',
        author_email='vladimir.starostin@uni-tuebingen.de',
        description='A GUI program for GIWAXS images analysis',
        long_description=read('README.md'),
        long_description_content_type='text/markdown',
        license='GPLv3',
        python_requires='>=3.7.2',
        entry_points={
                "gui_scripts": [
                    "giwaxs_gui = giwaxs_gui.__main__:run",
                ]
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
            'qdarkstyle',
            'qdarkgraystyle'
            ],
        include_package_data=True,
        keywords='xray python giwaxs scientific-analysis',
        url='https://pypi.org/project/giwaxs-gui',
)
