# -*- coding: utf-8 -*-
from setuptools import setup, find_packages, Extension
from Cython.Build import cythonize
from pathlib import Path
import numpy
from glob import glob

def open_requirements(fname):
    with open(fname, mode='r') as f:
        requires = f.read().split('\n')
    requires = [e for e in requires if len(e) > 0 and not e.startswith('#')]
    return requires

# d = {}
# exec(open("wavpack_numcodecs/version.py").read(), None, d)
# version = d['version']
version = "0.1.0"
long_description = open("README.md").read()

pkg_folder = Path(__file__).parent

entry_points = None

install_requires = open_requirements('requirements.txt')

src_folder = pkg_folder / "wavpack_cython" / "src"
wavpack_src_folder = pkg_folder / "wavpack_cython" / "src" / "wavpack"

sources = [str(pkg_folder / "wavpack_cython" / "wavpack.pyx")]
wavpack_sources = glob(f"{wavpack_src_folder}/*.c")

include_dirs = [str(wavpack_src_folder)]

sources = sources + wavpack_sources

extensions = [
        Extension('wavpack_cython.wavpack',
                  sources=sources,
                  include_dirs=include_dirs + [numpy.get_include()],
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
