REM @echo off


REM Batch script to clone a conda environement from a local drive to an UNC share


SET "envname=%1"

IF not defined envname (
  echo Please, define src_env
  EXIT /B 3
) ELSE (
  echo src_env=%envname%
)

set default_conda_exe="%ProgramFiles%\ArcGIS\Pro\bin\Python\Scripts\conda.exe"

set PYTHON_VERSION=3.9.18


REM ... or for the Pool VDI ???
set src_env=D:\conda\envs\%envname%
set dest_env=\\v0t0020a.adr.admin.ch\prod\lgX\TOPGIS\conda\envs\%envname%
set conda_exe=%src_env%\condabin\conda.bat
echo Target %dest_env%

echo %time% === Cloning conda env "%src_env%"  to %dest_env% ===


REM cleanup
if not exist "c:\temp\" mkdir "c:\temp\"
del c:\temp\%envname%_conda_clone*.txt
del %dest_env%

ECHO %time% === Cleaning env '%envname%'   ===

CALL %conda_exe%  clean -p %src_env%  --all --yes 1> c:\temp\%envname%_conda_clone_clean.txt ^
   2> c:\temp\%envname%_conda_clone_clean_err.txt



ECHO %time% === Cloning env '%envname%' from %src_env%  ===

CALL %default_conda_exe% create --clone %src_env%  -p %dest_env%  -vv --no-shortcuts ^
  --pinned 1> c:\temp\%envname%_conda_clone_clone.txt ^
  2> c:\temp\%envname%_conda_clone_clone_err.txt

ECHO %time% === Done ===
