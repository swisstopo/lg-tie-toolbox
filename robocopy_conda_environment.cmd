@echo off


REM Batch script to clone a conda environement from a local drive to an UNC share
REM
REM Usage:
REM         clone_conda_environment.bat SRC_ENV_NAME  DST_ENV_NAME
REM
REM   with D:\conda\envs\%SRC_ENV_NAME%
REM        T:\conda\envs\%DST_ENV_NAME%


SET "srcEnvName=%1"
SET "dstEnvName=%2"

IF not defined srcEnvName (
  echo Please, define src_env
  EXIT /B 3
) ELSE (
  echo srcEnvName=%srcEnvName%
)
IF not defined dstEnvName (
  echo Please, define dstEnvname
  EXIT /B 3
) ELSE (
  echo destEnvName=%dstEnvName%
)

set default_conda_exe="%ProgramFiles%\ArcGIS\Pro\bin\Python\Scripts\conda.exe"

set PYTHON_VERSION=3.9.18


REM ... or for the Pool VDI ???
set src_env=D:\conda\envs\%srcEnvName%
set dest_env=\\v0t0020a.adr.admin.ch\prod\lgX\TOPGIS\TIEToolbox\conda\envs\%dstEnvName%
set conda_exe=%src_env%\condabin\conda.bat
echo Target %dest_env%

echo %time% === Robocopying conda env "%src_env%"  to %dest_env% ===


REM cleanup
if not exist "c:\temp\" mkdir "c:\temp\"
del c:\temp\%srcEnvName%_conda_clone*.txt
del %dest_env%

ECHO %time% === Cleaning env '%srcEnvName%'   ===

CALL %conda_exe%  clean -p %src_env%  --all --yes 1> c:\temp\%srcEnvName%_conda_clone_clean.txt ^
   2> c:\temp\%srcEnvName%_conda_clone_clean_err.txt



ECHO %time% === Robocopying env '%srcEnvName%' from %src_env% to %dest_env%   ===

REM /MIR: Mirrors the directory tree, including deletions.
REM  or
REM /E: This option ensures that all subdirectories, including empty ones, are copied.
REM /XF *.pyc: Excludes all .pyc files.
REM /XD __pycache__: Excludes all __pycache__ directories.

CALL robocopy %src_env% %dest_env%   /MIR /XF *.pyc /XD __pycache__ ^ 
 1> c:\temp\%srcEnvName%_conda_clone_clone.txt ^
  2> c:\temp\%srcEnvName%_conda_clone_clone_err.txt

ECHO %time% === Done ===
