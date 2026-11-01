function Get-HermesContext {
    param([string]$HermesHome, [string]$HermesSource)
    if (-not $HermesHome) {
        $HermesHome = $env:HERMES_HOME
        if (-not $HermesHome) { $HermesHome = Join-Path $env:LOCALAPPDATA 'hermes' }
    }
    $HermesHome = [IO.Path]::GetFullPath($HermesHome)
    if (-not $HermesSource) { $HermesSource = Join-Path $HermesHome 'hermes-agent' }
    $HermesSource = [IO.Path]::GetFullPath($HermesSource)
    $command = Join-Path $HermesHome 'bin\hermes.exe'
    if (-not (Test-Path -LiteralPath $command)) {
        $found = Get-Command hermes -ErrorAction SilentlyContinue
        if (-not $found) { throw 'Install Hermes first and open a new PowerShell window.' }
        $command = $found.Source
    }
    if (-not (Test-Path -LiteralPath (Join-Path $HermesSource 'pm\environments.py'))) {
        throw 'This kit targets a native Windows source install. Set -HermesSource to its hermes-agent directory. For signed bundles, use the manual guide.'
    }
    [pscustomobject]@{ Home=$HermesHome; Source=$HermesSource; Command=$command }
}

function Get-LocalEndpoint {
    param([int]$Port)
    if ($Port -lt 1 -or $Port -gt 65535) { throw 'Port must be between 1 and 65535.' }
    "http://127.0.0.1:$Port"
}
