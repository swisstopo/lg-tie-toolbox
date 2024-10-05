# Simplified version to only get the `cm`

import geopandas as gpd
import numpy as np

from shapely.geometry import LineString


def bed2cmap(BEDrst, legendfile, leg_labels=False):
    kind = np.unique(BEDrst.flatten())
    kind = np.extract(np.isnan(kind) == False, kind)
    cm = np.zeros(np.size(BEDrst.flatten()))
    leg = np.loadtxt(legendfile, usecols=(0, 1, 2, 3))
    k_col = np.zeros(np.shape(kind))

    for k in range(len(kind)):
        i = (BEDrst.flatten() == kind[k]).nonzero()
        cm[i] = k + 1
        # TODO: Error ValueError: setting an array element with a sequence
        # k_col[k] = (leg[:, 0] == kind[k]).nonzero()[0]
        # Fix the line causing the error
        matching_rows = np.where(leg[:, 0] == kind[k])[0]
        if matching_rows.size > 0:
            # print("matching row", matching_rows.size)
            k_col[k] = matching_rows[0]

    cm = cm.reshape(np.shape(BEDrst))
    cm = np.fliplr(cm)

    cmap = np.zeros((255, 4))

    if any(np.isnan(BEDrst.flatten())):
        c_step = np.linspace(0, 255, np.size(k_col) + 2)
        c_step = np.round(c_step, 0).astype(int)
        cmap[0 : int(c_step[1]), 0:3] = np.ones((int(c_step[1]), 3)) * [230, 230, 230]

        for ci in range(1, len(c_step) - 1):
            ind1 = int(c_step[ci])
            ind2 = int(c_step[ci + 1])
            rgb_c = leg[int(k_col[ci - 1]), 1:4]
            cmap[ind1:ind2, 0:3] = np.ones((ind2 - ind1, 3)) * rgb_c
    else:
        c_step = np.linspace(0, 255, np.size(k_col) + 1)
        c_step = np.round(c_step, 0).astype(int)

        for ci in range(len(c_step) - 1):
            ind1 = int(c_step[ci])
            ind2 = int(c_step[ci + 1])
            rgb_c = leg[int(k_col[ci]), 1:4]
            cmap[ind1:ind2, 0:3] = np.ones((ind2 - ind1, 3)) * rgb_c
    cmap[:, 3] = (np.ones((255, 1)) * 255).flatten()

    return cm, cmap


def export_traces(DEM, BTraces=[]):
    """
    Exporting a trace object as geopandas

    Parameters
    ----------
    DEM : dict
        Dictionary containing DEM and coordinate data obtained with TIE_load.cropDEMextent.
    list
        List of trace objects (trace_OBJ) defined in TIE_classes.

    Returns
    -------
    geopandas.GeoDataFrame
        The converted traces.



    """
    mx, my = np.meshgrid(DEM["x"], DEM["y"])
    mz = np.flipud(DEM["z"].copy())
    mx = mx.astype(float)
    my = my.astype(float)

    vx = np.fliplr(mx).flatten()
    vy = my.flatten()
    vz = np.fliplr(mz).flatten()  # TODO: check  if correct

    try:
        crs = DEM["meta"]["crs"]
    except Exception:
        print("No CRS")

    txx = []
    tyy = []
    tzz = []
    if len(BTraces) > 0:
        for tr in BTraces:
            tx = vx[tr.index.astype(int)]
            ty = vy[tr.index.astype(int)]
            tz = vz[tr.index.astype(int)]
            txx.append(tx)
            tyy.append(ty)
            tzz.append(tz)
    line_strings = [LineString(list(zip(x, y, z))) for x, y, z in zip(txx, tyy, tzz)]

    # Now line_strings is an array of LineString objects
    # Create a GeoDataFrame with the LineString objects
    authority_str = "epsg:{}".format(crs.to_epsg())
    gdf = gpd.GeoDataFrame(geometry=line_strings, crs=authority_str)

    return gdf
