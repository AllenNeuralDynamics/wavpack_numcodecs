# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

def open_requirements(fname):
    with open(fname, mode='r') as f:
        requires = f.read().split('\n')
    requires = [e for e in requires if len(e) > 0 and not e.startswith('#')]
    return requires

d = {}
exec(open("wavpack_numcodecs/version.py").read(), None, d)
version = d['version']
long_description = open("README.md").read()

entry_points = None

install_requires = open_requirements('requirements.txt')

setup(
    name="wavpack_numcodecs",
    version=version,
    author="Alessio Buccino",
    author_email="alessiop.buccino@gmail.com",
    description="Numcodecs implementation of WavPack audio codec.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AllenNeuralDynamics/wavpack_numcodecs",
    install_requires=install_requires,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    entry_points=entry_points,
    include_package_data=True,
)
