param(
    [string]$HermesHome = '',
    [string]$HermesSource = '',
    [string]$Endpoint = 'http://127.0.0.1:8080/v1',
    [string]$Model = 'local-hermes',
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Common.ps1')
$context = Get-HermesContext -HermesHome $HermesHome -HermesSource $HermesSource
$arguments = @('--hermes-home', $context.Home, '--endpoint', $Endpoint, '--model', $Model)
if ($DryRun) { $arguments += '--dry-run' }
& (Join-Path $PSScriptRoot 'Invoke-HermesPython.ps1') -HermesHome $context.Home -HermesSource $context.Source -Script (Join-Path $PSScriptRoot 'install.py') -ScriptArgs $arguments
