param(
    [Parameter(Mandatory=$true)][string]$Script,
    [string[]]$ScriptArgs = @(),
    [string]$HermesHome = '',
    [string]$HermesSource = ''
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Common.ps1')
$context = Get-HermesContext -HermesHome $HermesHome -HermesSource $HermesSource
$saved = @{}
function Save-ProcessVariable([string]$Name) {
    if (-not $saved.ContainsKey($Name)) { $saved[$Name] = [Environment]::GetEnvironmentVariable($Name, 'Process') }
}
foreach ($name in @('HERMES_HOME','PYTHONPATH','PYTHONHOME')) { Save-ProcessVariable $name }
try {
    $env:HERMES_HOME = $context.Home
    $exports = ((& $context.Command pm env python) -join "`n") | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot discover Hermes Python. Run hermes pm repair.' }
    $bootstrap = $null
    foreach ($directory in ($exports.PATH -split [IO.Path]::PathSeparator)) {
        $candidate = Join-Path $directory 'python.exe'
        if (Test-Path -LiteralPath $candidate) { $bootstrap = $candidate; break }
    }
    if (-not $bootstrap) { throw 'Hermes did not return a usable Python tool path.' }
    $env:PYTHONPATH = $context.Source
    Remove-Item env:PYTHONHOME -ErrorAction SilentlyContinue
    $activation = ((& $bootstrap -X utf8 -m pm.environments) -join "`n") | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the selected Hermes environment. Run hermes pm repair.' }
    foreach ($property in $activation.PSObject.Properties) {
        Save-ProcessVariable $property.Name
        [Environment]::SetEnvironmentVariable($property.Name, [string]$property.Value, 'Process')
    }
    & $bootstrap -X utf8 $Script @ScriptArgs
    if ($LASTEXITCODE -ne 0) { throw "Python check failed with exit code $LASTEXITCODE." }
} finally {
    foreach ($name in $saved.Keys) { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
}
