param(
    [string]$HermesHome = '',
    [string]$HermesSource = '',
    [int]$Port = 9120,
    [switch]$NoOpen
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Common.ps1')
$context = Get-HermesContext -HermesHome $HermesHome -HermesSource $HermesSource
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Choose a local port from 1024 to 65535.' }
$settingsPath = Join-Path $context.Home 'jarvis-data\settings.json'
if (-not (Test-Path -LiteralPath $settingsPath)) { throw 'Run scripts\Install-Jarvis.ps1 first.' }
$settings = Get-Content -Raw -LiteralPath $settingsPath | ConvertFrom-Json
$modelLauncher = Join-Path $context.Home 'Start-LocalServer.ps1'
if (Test-Path -LiteralPath $modelLauncher) { & $modelLauncher }
Write-Host 'Starting Jarvis locally. Keep this window open; Ctrl+C stops the panel.'
$serverArguments = @('--hermes-home', $context.Home, '--data-dir', (Join-Path $context.Home 'jarvis-data'), '--port', [string]$Port, '--endpoint', $settings.endpoint, '--model', $settings.model)
if (-not $NoOpen) { $serverArguments += '--open-browser' }
& (Join-Path $PSScriptRoot 'Invoke-HermesPython.ps1') -HermesHome $context.Home -HermesSource $context.Source -Script (Join-Path $PSScriptRoot '..\jarvis\server.py') -ScriptArgs $serverArguments
