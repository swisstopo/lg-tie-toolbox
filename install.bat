@echo off

REM Define the drive letter and the network path
set driveLetter=T:
set networkPath=\\v0t0020a.adr.admin.ch\prod\lgX\TOPGIS\TIEToolbox
set dirPath=H:\config\geocover
set condarcPath=H:\.condarc

REM Check if the drive exists and remove it if it does
if exist %driveLetter%\ (
    net use %driveLetter% /delete /yes
)

REM Create the new drive
net use %driveLetter% %networkPath% /persistent:yes


REM Define the directory path


REM Check if the directory exists
if not exist "%dirPath%" (
    REM Create the directory and all necessary subdirectories
    mkdir "%dirPath%"
    echo Directory %dirPath% created.
) else (
    echo Directory %dirPath% already exists.
)

REM Writing to the .condarc file
echo envs_dirs: > %condarcPath%
echo   - C:\tmp\TIE >> %condarcPath%
echo   - T:\conda\envs\TIE >> %condarcPath%
echo channels: >> %condarcPath%
echo   - defaults >> %condarcPath%
echo ssl_verify: false >> %condarcPath%
echo proxy_servers: >> %condarcPath%
echo   http: prp04.admin.ch:8080 >> %condarcPath%

REM Writing to the geocover.ini file
setlocal enabledelayedexpansion
set "computerName=%COMPUTERNAME%"
set "userName=%USERNAME%"

(
echo [%computerName%]
echo proxy=prp04.admin.ch:8080
echo tie_conda_env=T:\conda\envs\TIE
echo projectdir=T:\conda\envs\TIE\demo
echo username=%userName%
echo [default]
echo proxy=prp04.admin.ch:8080
echo tie_conda_env=T:\conda\envs\TIE
echo projectdir=T:\conda\envs\TIE\demo
echo username=%userName%
) > %dirPath%\geocover.ini

endlocal
