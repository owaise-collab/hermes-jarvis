param([Parameter(Mandatory=$true)][string]$Backup, [string]$HermesHome = '', [string]$HermesSource = '')
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'Invoke-HermesPython.ps1') -HermesHome $HermesHome -HermesSource $HermesSource -Script (Join-Path $PSScriptRoot 'install.py') -ScriptArgs @('--restore', $Backup)
