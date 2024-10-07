TIE Analysis
============

Basic ESRI ArcMap's Toolbox to perform Trace Information Extraction (TIE) Analysis.


![TIE flow](images/flow.png)

![TIE analysis](images/trace_analysis.png)


## Installation

Basically, this is an ESRI ArcMap/ArcGis Pro ToolBox (Python2.7 and Python 3.9) running external scripts using `Python3`.

### Automatic installation (VDI Win10 TopGis)

Use the `install.bat` script in _\\v0t0020a.adr.admin.ch\prod\lgX\TOPGIS\TIEToolbox_

It will create:

  * A new network drive T:\ pointing to _\\v0t0020a.adr.admin.ch\prod\lgX\TOPGIS\TIEToolbox_
  * A new _H:\.condarc_ file (proxy setting) 
  * A configuration file _H:\config\geocover\geocover.ini_ with the name of the conda environment to use. By default _TIE_
  * Copy the toolbox itself to D:\Argis_Home


### Manual install


Conda
-----

On the Citrix VDI and the  BURAUT laptop, the only Python3 available is the one 
of the  ESRI ArcGis Pro _C:\Program Files\ArcGIS\Pro_ installation.

There are several limitations:

 * You cannnot modify the default `argispro-py3` conda environment. You may only clone it.
 * On BURAUT, you only have a C:\ drive and may only write to _C:\LegacySW_
 * On the VDI, you have C:\ and D:\ and may write almost everywhere. 
 * Calling any `conda env` from within `ArcGis Pro` will pollute the _sys-path_ with the default environment variables.

Creating a conda env from scratch (takes about 2-4 hours). The command will create a new env in _D:\conda\envs_

    H:\code\bitbuckets\arcmap-tie-toolbox> setup_conda_environment.cmd TIE

---
**NOTE**

As there are no `arcgis` and `arcpy` modules in this environnement, it's labelled as `broken`by ArcGis Pro.
---


## Build 

    (c:\LegacySW\build-distribute) H:\code\arcmap-tie-toolbox>conda build --debug  recipe -c swisstopo -c conda-forge



## Traces InterfacesExtraction (TIE)

Using a `dask` pipeline

![](images/flow.png "TIE pipeline")


Exporting TIE Analysis to GeoJSON or KML

![](images/lines_to_poly.png "Traces as surfaces")

## Usage


![](images/toolbox.png "ArcMap TIE ToolBox")


Select an area (a few square kilometers, around 1:10'000 or bigger, no sheet border!)

![](images/export_data.png "Exporting data")

GDB structure

![](images/gdb_structure.png "Layers in the GDB")

Download DEM and create a mosiac

![](images/download_dem.png "Donwlaod DEM")

New Mosic file
![](images/mosaic_file.png "Mosaic file in project folder")

Hillshade from DEM mosaic (only for demo)
![](images/mosaic_from_dem.png "Hillshade from DEM mosaic")


TIE Analysis

Takes about 10-15 minutes for 5 km2

![](images/tie_analysis.png "TIE Analysis")


3D View and TIE Analysis

![](images/3D_with_TIE_analysis.png "3D View and TIE analysis")
[map.geo.admin.ch (3D)](https://s.geo.admin.ch/3k4ctm9jhzdn)

 Or add manually the following KML files:       
    
    https://dubious.cloud/TIE/data/Kaiseregg/2.0/tie_as_multilines_under.kml 
    https://dubious.cloud/TIE/data/Kaiseregg/2.0/tie_as_lines_under.kml 


