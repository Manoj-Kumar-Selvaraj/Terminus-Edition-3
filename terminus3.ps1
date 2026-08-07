# Terminus Edition 3 — Windows wrapper for terminus3.sh (runs via WSL).
# Usage (from PowerShell):
#   .\terminus3.ps1 help
#   .\terminus3.ps1 list
#   .\terminus3.ps1 oracle ansible-ci-control-plane
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $Root "terminus3.sh"

# D:\foo\bar -> /mnt/d/foo/bar
$drive = $Script.Substring(0, 1).ToLower()
$rest = ($Script.Substring(2) -replace '\\', '/')
$WslPath = "/mnt/$drive$rest"

if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Error "WSL not found. Install WSL or run terminus3.sh directly in a Linux shell."
}

if (-not $CommandArgs -or $CommandArgs.Count -eq 0) {
    wsl -d Ubuntu-22.04 -- bash "$WslPath" help
} else {
    wsl -d Ubuntu-22.04 -- bash "$WslPath" @CommandArgs
}
