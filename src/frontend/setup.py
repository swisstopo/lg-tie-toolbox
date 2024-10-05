import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="tietools.esri",
    version=read("VERSION").strip(),
    author="swisstopo",
    description=(
        "Basic ESRI ArcMap/ArcGis Pro TIE Toolbox (UI)"
    ),
    long_description=read("README.md"),
    long_description_content_type='text/markdown',
    python_requires=">=2.7",
    packages=[ "tietools.esri",],
    license_files = ('LICENSE.txt',),
    install_requires=[
        "arcpy",
        "tietools>=0.5.0",
    ],

    include_package_data=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: BSD License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Topic :: Scientific/Engineering :: Image Processing",
        "Topic :: Scientific/Engineering :: GIS",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],

)
