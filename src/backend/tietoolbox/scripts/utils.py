import json
from math import ceil
from os.path import normpath
from pathlib import Path, PurePath, PurePosixPath
from pathlib import PureWindowsPath

import numpy as np
import rasterio as rst
from affine import Affine
from rasterio.features import rasterize
import geopandas as gpd
from rasterio.mask import mask

import unicodedata
import re
import shapely


def cropDEMextent(geotif: rst.io.DatasetReader, shapefile: gpd.GeoDataFrame) -> dict:
    """Crop DEM with Shapefile."""

    crs = (geotif.crs,)

    bbox = [2569800, 1221000, 2573200, 1223000]
    box = shapely.geometry.box(*bbox)

    print(box)

    output_meta = geotif.meta.copy()

    DEM, out_trans = mask(geotif, [box], crop=False, filled=True)
    z = DEM[0]

    xend = out_trans[2] + out_trans[0] * z.shape[1] + 1
    x1 = out_trans[2] + 1
    y1 = out_trans[5] + out_trans[4] * z.shape[0] + 1
    yend = out_trans[5] + 1

    x = np.arange(x1, xend, out_trans[0])
    y = np.arange(y1, yend, out_trans[0])

    out_meta = geotif.meta.copy()
    out_meta.update(
        {
            "driver": "GTiff",
            "height": DEM.shape[0],
            "width": DEM.shape[1],
            "transform": out_trans,
        }
    )

    DEM = {"z": z, "x": x, "y": y, "meta": out_meta}
    return DEM


def load_config(project_name):
    try:
        with open("config.json", "r") as f:
            config = json.loads(f.read())
    except (json.decoder.JSONDecodeError, IOError):
        print("Cannot load config.json. Exiting")

    return config.get(project_name)


def path_to_str(obj):
    if isinstance(obj, (Path, PurePath, PurePosixPath)):
        return str(obj)
    return obj


# https://stackoverflow.com/a/43184871
def search(d, key, default=None):
    """Return a value corresponding to the specified key in the (possibly
    nested) dictionary d. If there is no item with that key, return
    default.
    """
    stack = [iter(d.items())]
    while stack:
        for k, v in stack[-1]:
            if isinstance(v, dict):
                stack.append(iter(v.items()))
                break
            elif k == key:
                return v
        else:
            stack.pop()
    return default


# Windows forbidden characters:  " # % & * : < > ? \ / { | } ~
def processString6(txt):
    dictionary = {">": "gt", "<": "lt"}
    pattern = re.compile("|".join(sorted(dictionary.keys(), key=len, reverse=True)))
    result = pattern.sub(lambda x: dictionary[x.group()], txt)
    return result


def get_valid_filename(s):
    """
    Return the given string converted to a string that can be used for a clean
    filename. Remove leading and trailing spaces; convert other spaces to
    underscores; and remove anything that is not an alphanumeric, dash,
    underscore, or dot.
    >>> get_valid_filename("john's portrait in 2004.jpg")
    'johns_portrait_in_2004.jpg'
    """
    s = str(s).strip().replace(" ", "_")
    return re.sub(r"(?u)[^-\w.]", "", s)


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def universalpath(path):
    return PureWindowsPath(normpath(PureWindowsPath(path).as_posix())).as_posix()


# https://pygis.io/docs/e_raster_rasterize.html
def rasterizeGPD(gdf, prop, bounds, res) -> np.ndarray:
    """Rasterizes Shapefile.

    Rasterizes a shapefile according to a specific attribute field value.

    Parameters
    ----------
    shp : geopandas.geodataframe.GeoDataFrame
        Opened geopandas handle to a shapefile.

    prop : str
        Attribute in shapefile that will be used to distinguish between different types
        of tectonic boundaries or litho-stratigraphic units. The attribute value must be a number.

    bounds : list
        bounds  (x, y, and z) of the analyzed zone (see crop2DEMextent).

    res tuple
       resolution (x, y)

    Returns
    -------
    numpy.ndarray
        Raster matrix.
    """
    # geometries = [shapes for shapes in gdf.geometry]

    geometries = ((geom, value) for geom, value in zip(gdf.geometry, gdf[prop]))
    if not isinstance(res, (list, tuple)):
        res = (res, res)

    print(res, bounds)
    width = max(int(ceil((bounds[2] - bounds[0]) / float(res[0]))), 1)
    height = max(int(ceil((bounds[3] - bounds[1]) / float(res[1]))), 1)

    # TODO: check crs
    kwargs = {
        "count": 1,
        "crs": 2056,
        "width": width,
        "height": height,
        "all_touched": False,
        "transform": Affine(res[0], 0, bounds[0], 0, -res[1], bounds[3]),
        "driver": "GTiff",
        "dtype": "float64",
        "fill": -9999.0,
    }

    rasterized = rasterize(
        geometries,
        out_shape=(kwargs["height"], kwargs["width"]),
        transform=kwargs["transform"],
        dtype=kwargs.get("dtype", None),
        default_value=1,
    )
    """
    with rasterio.open(output, "w", **kwargs) as out:
        out.write(result, indexes=1)
    """

    return rasterized


def array_to_tif(arr, fname, crs, transform):
    """Write a NumPy array to a GeoTIFF file.

    Parameters
    ----------
    arr : numpy.ndarray
        2D array to be written to GeoTIFF.
    fname : str
        Filepath for the output GeoTIFF file.
    crs : rasterio.crs.CRS
        Coordinate Reference System of the data.
    transform : rasterio.transform.Affine
        Affine transformation that maps pixel coordinates to coordinates in the
        given CRS.

    Returns
    -------
    None
    """
    # inversé
    new_dataset = rst.open(
        fname,
        "w",
        driver="GTiff",
        height=arr.shape[0],
        width=arr.shape[1],
        count=1,
        dtype=str(arr.dtype),
        crs=crs,
        transform=transform,
    )

    new_dataset.write(arr, 1)
    new_dataset.close()


# DEM dict to array


def dem_to_array(DEM):
    x_values = DEM["x"]
    y_values = DEM["y"]
    z_values = DEM["z"]

    # Create a 2D grid from x and y values using meshgrid
    # Create a 2D array for elevation values (z)
    elevation_array = np.array(z_values)

    # Reshape the elevation values into a 2D array
    dem_array = elevation_array.reshape(len(y_values), len(x_values))

    return dem_array
