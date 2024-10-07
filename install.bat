@echo off


SET "condaEnvName=%1"

IF not defined condaEnvName (
  echo Using the default value for condaEnvName
  set condaEnvName=TIE
) ELSE (
  echo condaEnvName=%condaEnvName%
)

REM Define the drive letter and the network path
set driveLetter=T:
set networkPath=\\v0t0020a.adr.admin.ch\prod\lgX\TOPGIS\TIEToolbox
set dirPath=H:\config\geocover
set condarcPath=H:\.condarc
SET ARCGIS_HOME=D:\ArcGIS_Home


REM Check if the drive exists and remove it if it does
if exist %driveLetter%\ (
    net use %driveLetter% /delete /yes
)

REM Create the new drive
ECHO %time% === Create the new drive %driveLetter% ===
net use %driveLetter% %networkPath% /persistent:yes


REM Define the directory path


REM Check if the directory exists
ECHO %time% === Check if the directory exists %dirPath%  ===
if not exist "%dirPath%" (
    REM Create the directory and all necessary subdirectories
    mkdir "%dirPath%"
    echo Directory %dirPath% created.
) else (
    echo Directory %dirPath% already exists.
)

REM Writing to the .condarc file
ECHO %time% === Writing to the .condarc file  ===
echo envs_dirs: > %condarcPath%
echo   - C:\tmp\%condaEnvName% >> %condarcPath%
echo   - T:\conda\envs\%condaEnvName% >> %condarcPath%
echo channels: >> %condarcPath%
echo   - defaults >> %condarcPath%
echo ssl_verify: false >> %condarcPath%
echo proxy_servers: >> %condarcPath%
echo   http: prp04.admin.ch:8080 >> %condarcPath%

REM Writing to the geocover.ini file
ECHO %time% === Writing to the geocover.ini file  ===
setlocal enabledelayedexpansion
set "computerName=%COMPUTERNAME%"
set "userName=%USERNAME%"

(
echo [%computerName%]
echo proxy=prp04.admin.ch:8080
echo tie_conda_env=T:\conda\envs\%condaEnvName%
echo projectdir=T:\conda\envs\%condaEnvName%\demo
echo username=%userName%
echo [default]
echo proxy=prp04.admin.ch:8080
echo tie_conda_env=T:\conda\envs\%condaEnvName%
echo projectdir=T:\conda\envs\%condaEnvName%\demo
echo username=%userName%
) > %dirPath%\geocover.ini


ECHO %time% === Copying toolbox to %ARCGIS_HOME%  ===
if not exist %ARCGIS_HOME% mkdir %ARCGIS_HOME%

REM Copy Python files while excluding .pyc files and __pycache__ directories
xcopy T:\conda\envs\%condaEnvName%\Lib\site-packages\tietoolbox  "%ARCGIS_HOME%\tietoolbox\"  /S /E /Y /EXCLUDE:exclude.txt

endlocal
