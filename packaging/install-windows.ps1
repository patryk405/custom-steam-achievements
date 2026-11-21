$ErrorActionPreference = 'Stop'
$steam = (Get-ItemProperty -Path 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
if (!$steam) { $steam = Read-Host 'Enter your Steam installation folder' }
if (!(Test-Path (Join-Path $steam 'millennium'))) { throw 'Install Millennium first: https://steambrew.app/' }
if (Get-Process steam -ErrorAction SilentlyContinue) { throw 'Exit Steam, then run Install.cmd again.' }
$dest = Join-Path $env:LOCALAPPDATA 'custom-achievements\app'
$exe = Join-Path $dest 'csa-tracker.exe'
Get-CimInstance Win32_Process -Filter "name='csa-tracker.exe'" | Where-Object { $_.ExecutablePath -eq $exe } | ForEach-Object { Stop-Process -Id $_.ProcessId }
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path (Join-Path $PSScriptRoot 'tracker\*') -Destination $dest -Recurse -Force
$plugins = Join-Path $steam 'millennium\plugin'
if (Test-Path (Join-Path $steam 'millennium\plugins')) { $plugins = Join-Path $steam 'millennium\plugins' }
New-Item -ItemType Directory -Force -Path $plugins | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'local.custom-achievements.star') $plugins -Force
# A small per-user launcher keeps the tracker console out of the way.
$launcher = Join-Path $dest 'start-tracker.vbs'
$quoted = $exe.Replace('"','""')
'Set shell = CreateObject("WScript.Shell")' + "`r`n" + 'shell.Run Chr(34) & "' + $quoted + '" & Chr(34), 0, False' | Set-Content $launcher
New-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'CustomSteamAchievements' -Value ('wscript.exe "' + $launcher + '"') -PropertyType String -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Programs')) 'Custom Steam Achievements Setup.lnk'))
$link.TargetPath = $exe; $link.Arguments = '--configure'; $link.WorkingDirectory = $dest; $link.Save()
Start-Process wscript.exe -ArgumentList ('"' + $launcher + '"')
Write-Host 'Installed. Start Steam and enable Custom Achievements in Millennium.'
Write-Host 'Open Custom Steam Achievements Setup from Start to select your game saves.'
