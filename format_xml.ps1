$files = Get-ChildItem -Path . -Filter *.xml -Recurse 

#empty array for extensions preparation
$extensions = New-Object System.Collections.ArrayList($null)

#iterate over items= files and directories
for ($i=0; $i -lt $files.Count; $i++) {
    #print all (once by one of course)
    Write-Host $files[$i].Name
	([xml](gc $files[$i].FullName)).Save($files[$i].FullName)
    
}