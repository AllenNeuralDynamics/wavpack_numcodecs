# -*- coding: utf-8 -*-
from setuptools import setup, find_packages, Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext
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

runtime_library_dirs = []
if platform.system() == "Linux":
    libraries=["wavpack"]
    if shutil.which("wavpack") is not None:
        print("wavpack is installed!")
        extra_link_args=["-L/usr/local/lib/", "-L/usr/bin/"]
        runtime_library_dirs=["/usr/local/lib/", "/usr/bin/"]
    else:
        print("Using shipped ilbraries")
        extra_link_args=[f"-Llibraries/linux-x86_64"]
elif platform.system() == "Darwin":
    libraries=["wavpack"]
    assert shutil.which("wavpack") is not None, ("wavpack need to be installed externally. "
                                                 "You can use: brew install wavpack")
    print("wavpack is installed!")
    extra_link_args=["-L~/include/", "-L/usr/local/include/", "-L/usr/include"]
else: # windows
    libraries=["wavpackdll"]
    if "64" in platform.architecture()[0]:
        extra_link_args=[f"-Llibraries\windows-x86_64"]
    else:
        extra_link_args=[f"-Llibraries\windows-x86_32"]

extensions = [
        Extension('wavpack_cython.compat_ext',
                  sources=['wavpack_cython/compat_ext.pyx'],
                  extra_compile_args=[]), 
        Extension('wavpack_cython.wavpack',
                  sources=sources,
                  include_dirs=include_dirs,
                  libraries=libraries,
                  extra_link_args=extra_link_args,
                  runtime_library_dirs=runtime_library_dirs
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
    cmdclass={'build_ext': build_ext}
)
