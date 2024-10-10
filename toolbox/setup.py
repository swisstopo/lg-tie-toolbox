import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="tietoolbox",
    version=read("VERSION").strip(),
    author="swisstopo",
    description=(
        "Basic ESRI ArcMap/ArcGis Pro TIE Toolbox to perform Trace Information Extraction (TIE) Analysis."
    ),
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    python_requires=">=3.9",
    packages=[
        "tietoolbox",
        "tietoolbox.scripts",
        "tietoolbox.esri.toolboxes",
    ],
    license_files=("LICENSE.txt",),
    install_requires=[
        "shapely",
        "geocube",
        "numpy",
        "geopandas",
        "mayavi",
        "matplotlib",
        "rasterio",
        "scipy",
        "scikit-image",
        "dask",
        "tqdm",
        "gdal",
        "pyproj",
        "geojson",
        "pyyaml",
        "pyogrio",
        "ipycytoscape",
        "untie>=0.0.8",
        "geocover_utils>=0.4.0",
    ],
    package_data={
        "tietoolbox.scripts": [
            "scripts/symbols.tsv",
            "scripts/*",
        ],
        "tietoolbox": [
            "data/*",
            "data/cache/*",
            "esri/toolboxes/*",
            "esri/arcpy/*",
            "esri/help/gp/*",
            "esri/help/gp/toolboxes/*",
            "esri/help/gp/messages/*",
        ],
    },
    include_package_data=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: BSD License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Topic :: Scientific/Engineering :: Image Processing",
        "Topic :: Scientific/Engineering :: GIS",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
         "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    entry_points={
        "console_scripts": [
            "tie_analysis = tietoolbox.scripts.tie_analysis_dask:main",
            "tie_viewer = tietoolbox.scripts.tie_viewer:main",
            "tie_demo = tietoolbox.scripts.tie_demo:main",
        ],
    },
)
