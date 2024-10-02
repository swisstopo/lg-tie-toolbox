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


SET "envname=%1"

IF not defined envname (
  echo Please, define src_env
  EXIT /B 3
) ELSE (
  echo src_env=%envname%
)

set conda_exe="%ProgramFiles%\ArcGIS\Pro\bin\Python\Scripts\conda.exe"

set PYTHON_VERSION=3.9.18


REM ... or for the Pool VDI ???
set src_env="D:\conda\envs\%envname%"
set dest_env="\\v0t0020a.adr.admin.ch\prod\lgX\TOPGIS\conda\envs\%envname%"
echo Target %dest_env%

echo %time% === Cloning conda env "%src_env%"  to %dest_env% ===


REM cleanup
del c:\temp\%envname%_conda_clone*.txt
del %dest_env%

ECHO %time% === Cloning env '%envname%' from %src_env%  ===

%conda_exe% create --clone %src_env%  -p %dest_env%  -vv --no-shortcuts --pinned 1> c:\temp\%envname%_conda_clone_create.txt 2> c:\temp\%envname%_conda_clone_create_err.txt

ECHO %time% === Done ===
