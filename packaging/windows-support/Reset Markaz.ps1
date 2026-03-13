$ErrorActionPreference = "SilentlyContinue"

Get-Process Markaz, python | Stop-Process -Force

Remove-Item "$env:USERPROFILE\.markaz_blocked" -Force
Remove-Item "$env:USERPROFILE\.markaz_session.json" -Force
Remove-Item "$env:USERPROFILE\.markaz_restart.json" -Force
Remove-Item "$env:APPDATA\MarkazSentinel" -Recurse -Force

schtasks /Delete /TN "MarkazSentinel" /F 2>$null | Out-Null
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v MarkazSentinel /f 2>$null | Out-Null
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\MarkazSentinel.bat" -Force

Write-Host ""
Write-Host "Markaz reset complete."
Write-Host "You can now reopen Markaz.exe."
