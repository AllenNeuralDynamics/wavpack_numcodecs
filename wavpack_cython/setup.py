# -*- coding: utf-8 -*-
from setuptools import setup, find_packages, Extension
from Cython.Build import cythonize
from pathlib import Path
import platform
from glob import glob
from pathlib import Path
import shutil

force_rebuild = True

build_folder = Path("build")
if force_rebuild and build_folder.is_dir():
    shutil.rmtree(build_folder)

def open_requirements(fname):
    with open(fname, mode='r') as f:
        requires = f.read().split('\n')
    requires = [e for e in requires if len(e) > 0 and not e.startswith('#')]
    return requires

version = "0.1.0"
long_description = open("README.md").read()

pkg_folder = Path(__file__).parent

entry_points = None

install_requires = open_requirements('requirements.txt')
wavpack_headers_folder = pkg_folder / "include"

sources = [str(pkg_folder / "wavpack_cython" / "wavpack.pyx")]
include_dirs = [str(wavpack_headers_folder)]

if platform.system() == "Linux":
    if shutil.which("wavpack") is not None:
        print("wavpack is installed!")
        extra_link_args=["-L/usr/local/lib/", "-L/usr/bin"]
    else:
        extra_link_args=[f"-L{pkg_folder / 'libraries' / 'linux-x86_64'}"]
elif platform.system() == "Darwin":
    assert shutil.which("wavpack") is not None, ("wavpack need to be installed externally. "
                                                 "You can use: brew install wavpack")
    print("wavpack is installed!")
    extra_link_args=["-L~/include/", "-L/usr/local/include/", "-L/usr/include"]
else: # windows
    if "64" in platform.architecture()[0]:
        extra_link_args=[f"-L{pkg_folder / 'libraries' / 'windows-x86_64'}"]
    else:
        extra_link_args=[f"-L{pkg_folder / 'libraries' / 'windows-x86_32'}"]

extensions = [
        Extension('wavpack_cython.wavpack',
                  sources=sources,
                  include_dirs=include_dirs,
                  libraries=["wavpack"],
                  extra_link_args=extra_link_args
                #   extra_link_args=["-L/usr/local/lib/"]
                #   extra_link_args=[f"-L{str(pkg_folder / 'libraries' / 'linux-x86_64')}"]
                  ),
    ]

setup(
    name="wavpack_cython",
    version=version,
    author="Alessio Buccino",
    author_email="alessiop.buccino@gmail.com",
    description="Numcodecs implementation of WavPack audio codec in Cython.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AllenNeuralDynamics/wavpack_cython",
    install_requires=install_requires,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    ext_modules=cythonize(extensions),
    entry_points=entry_points,
    include_package_data=True,
)
