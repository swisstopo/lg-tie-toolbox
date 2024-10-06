@echo off


REM Batch script to create a conda environement suitable for TIE (https://github.com/geoloar/TIE-toolbox)
REM
REM usage setup_conda_environement.cmd <Env name> from within a Python command Prompt.
REM
REM This script uses the python from an ArcGis Pro installation, but do not clone nor install any ESRI modules. Hence,
REM you cannot swap this environment (to be used in ArcGis Pro)
REM
REM First install the .condarc in your %USERPROFILE%  with copy_condarc.cmd
REM

SET "ARCGIS_HOME=D:\ArcGIS_Home"
SET "envpath=%1"
SET "envname=%2"

IF not defined envname (
  echo Please, define envname
  EXIT /B 3
) ELSE (
  echo envname=%envname%
)
IF not defined envname (
  echo Please, define envpath
  EXIT /B 3
) ELSE (
  echo envpath=%envpath%
)

set conda_exe="%ProgramFiles%\ArcGIS\Pro\bin\Python\Scripts\conda.exe"
set activate="%ProgramFiles%\ArcGIS\Pro\bin\Python\Scripts\activate.bat"
set PYTHON_VERSION=3.9.18

if not exist "c:\temp\" mkdir "c:\temp\"

echo %time% === Creating conda env "%envname%" from scratch ===
REM %LOCALAPPDATA%
REM set dest_env="%LOCALAPPDATA%\ESRI\conda\envs\%envname%"

REM On the VDI itself..
set dest_env=%envpath%

set mamba=%dest_env%/condabin/mamba.bat
set conda=%dest_env%/condabin/conda.bat


REM ... or for the Pool VDI ??? (Good luck Mr. Bronski)
REM set dest_env="\\v0t0020a.adr.admin.ch\prod\lgX\TOPGIS\conda\envs\%envname%"
echo Target %dest_env%

REM cleanup
del c:\temp\%envname%*.txt
del %dest_env%

ECHO %time% === Creating env '%envname%'  (%dest_env%) from scratch for python %PYTHON_VERSION% ===


call %conda_exe% create -p %dest_env% -v --override-channels -c conda-forge -y --show-channel-urls ^
python=%PYTHON_VERSION% conda mamba  1> c:\temp\%envname%_create.txt ^
  2> c:\temp\%envname%_create_err.txt

ECHO %time% === Activating env '%envname%'  ===
echo  %activate%  %dest_env%
CALL %activate%  %dest_env%

ECHO %time% === Mamba install '%envname%' TIE packages === ===
call %mamba% install -v --override-channels -c conda-forge -y  pip setuptools  geopandas scikit-image scipy rasterio shapely mayavi geocube ^
  1> c:\temp\%envname%_mamba.txt 2> c:\temp\%envname%_mamba_err.txt

ECHO %time% === Installing General  packages into  %envname% ===
call  %mamba% install -p %dest_env% -v --override-channels -c conda-forge -y --show-channel-urls ^
shapely tqdm requests gdal pyproj geojson pyyaml pyogrio dask ipycytoscape psutil  --json ^
--no-shortcuts 1> c:\temp\%envname%_install_TIE.txt 2> c:\temp\%envname%_install_TIE_err.txt

ECHO %time% === Installing DEV  packages into  %envname% ===
REM Install after TIE package, otherwise it will use the latest versions, which are not supported py
call  %mamba% install -p %dest_env%  -v --override-channels -c conda-forge -y ^
--show-channel-urls  pycodestyle flake8 pep8-naming yapf isort black ruff  ^
  --json --no-shortcuts 1> c:\temp\%envname%_install_dev.txt 2> c:\temp\%envname%_install_dev_err.txt

ECHO %time% === Set GDAL_DATA ===

SETX GDAL_DATA  %dest_env%/Library/share/gdal

ECHO %time% === Exporting packages ===
call %conda%  env   export -p %dest_env% > %dest_env%\environment.yml


ECHO %time% === Copying toolbox to %ARCGIS_HOME%  ===
if not exist %ARCGIS_HOME% mkdir %ARCGIS_HOME%
xcopy %dest_env%\Lib\site-packages\tietoolbox\esri\toolboxes %ARCGIS_HOME% /s /e /y

ECHO Activate with: activate %dest_env%
ECHO If missing a 'name': conda config --append envs_dirs D:\conda\envs\
REM This needs arcgispro to be installed
REM echo %time% === Swap into new env  %envname% ===
REM --- swap to new environment ---
REM %conda_exe% proswap -p %dest_env% --json 1> c:\temp\%envname%_swap.txt 2> c:\temp\%envname%_swap_err.txt

ECHO %time% === Done ===
