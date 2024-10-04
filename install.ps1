

# Define the drive letter and the network path
$driveLetter = "T:"
$networkPath = "\\v0t0020a.adr.admin.ch\prod\lgX\TOPGIS\TIEToolbox\conda\envs\TIE"

# Check if the drive exists
if (Get-PSDrive -Name T -ErrorAction SilentlyContinue) {
    # Remove the existing drive
    Remove-PSDrive -Name T -Force
}

# Create the new drive
New-PSDrive -Name T -PSProvider FileSystem -Root $networkPath -Persist


# Writing to the .condarc file
$condarcContent = @"
envs_dirs:
  - C:\tmp\TIE
channels:
  - defaults
ssl_verify: false
proxy_servers:
  http: prp04.admin.ch:8080
"@
$condarcPath = "H:\.condarc.TXT"
$condarcContent | Out-File -FilePath $condarcPath -Encoding utf8

# Writing to the geocover.ini file
$geocoverContent = @"
[$env:COMPUTERNAME]
proxy=prp04.admin.ch:8080
tie_conda_env=T:\conda\envs\TIE
projectdir=T:\conda\envs\TIE\demo
username=$env:USERNAME
[default]
proxy=prp04.admin.ch:8080
tie_conda_env=T:\conda\envs\TIE
projectdir=T:\conda\envs\TIE\demo
username=$env:USERNAME
"@
$geocoverPath = "H:\config\geocover\geocover.ini.TXT"
$geocoverContent | Out-File -FilePath $geocoverPath -Encoding utf8