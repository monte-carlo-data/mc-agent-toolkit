<#
.SYNOPSIS
  Monte Carlo Agent Toolkit — Copilot CLI Hook Installer (PowerShell port)

.DESCRIPTION
  Installs MC Prevent hooks into a target project's .github\hooks\ directory.
  Usage: .\install.ps1 [-TargetDir <path>]
#>
[CmdletBinding()]
param(
    [string]
    $TargetDir = '.'
)

$ErrorActionPreference = 'Stop'

try {
    # Resolve paths
    $TargetDir = (Resolve-Path -Path $TargetDir).Path
} catch {
    Write-Error "Error: cannot resolve target directory '$TargetDir'"
    exit 1
}

# Script/Repo layout
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginDir = (Resolve-Path -Path (Join-Path $ScriptDir '..')).Path
$RepoRoot  = (Resolve-Path -Path (Join-Path $PluginDir '..\..')).Path
$HooksSrc  = Join-Path $PluginDir 'hooks\prevent'

# Prefer plugin-local lib; fall back to repo-level hooks/prevent/lib for compatibility
$LibSrcPlugin = Join-Path $PluginDir 'hooks\prevent\lib'
if (Test-Path $LibSrcPlugin) {
    $LibSrc = $LibSrcPlugin
} else {
    $LibSrc = Join-Path $RepoRoot 'hooks\prevent\lib'
}

# --- Preflight checks ---
if (-not (Get-Command python3 -ErrorAction SilentlyContinue)) {
    Write-Error "Error: python3 is required but not installed."
    exit 1
}

if (-not (Test-Path (Join-Path $HooksSrc 'pre_edit_hook.py'))) {
    Write-Error "Error: hook scripts not found at $HooksSrc"
    exit 1
}

if (-not (Test-Path (Join-Path $LibSrc 'protocol.py'))) {
    Write-Error "Error: shared lib not found at $LibSrc"
    exit 1
}

Write-Host "Installing MC Prevent hooks for Copilot CLI into: $TargetDir"

# --- 1. Hook scripts ---
$ScriptsDest = Join-Path $TargetDir '.github\hooks\scripts'
New-Item -ItemType Directory -Path $ScriptsDest -Force | Out-Null

$scripts = @('pre_edit_hook.py','post_edit_hook.py','pre_commit_hook.py','turn_end_hook.py')
foreach ($script in $scripts) {
    $src = Join-Path $HooksSrc $script
    if (-not (Test-Path $src)) {
        Write-Error "Missing hook script: $src"
        exit 1
    }
    Copy-Item -Path $src -Destination $ScriptsDest -Force
}

# If running on a POSIX-like environment with chmod available, mark python hooks executable
if (Get-Command chmod -ErrorAction SilentlyContinue) {
    try { & chmod +x (Join-Path $ScriptsDest '*.py') } catch { }
}

Write-Host "  ✓ Hook scripts copied to .github/hooks/scripts/"

# --- 2. Shared lib (resolve symlinks) ---
$LibDest = Join-Path $ScriptsDest 'lib'
New-Item -ItemType Directory -Path $LibDest -Force | Out-Null

# Copy library files (recursively)
Copy-Item -Path (Join-Path $LibSrc '*') -Destination $LibDest -Recurse -Force -ErrorAction Stop

# Clean dev artifacts
$testsPath = Join-Path $LibDest 'tests'
if (Test-Path $testsPath) { Remove-Item -Path $testsPath -Recurse -Force -ErrorAction SilentlyContinue }

Get-ChildItem -Path $LibDest -Recurse -Directory -Force -Filter '__pycache__' -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }

Get-ChildItem -Path $LibDest -Recurse -Include '*.pyc' -File -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue }

Write-Host "  ✓ Shared lib copied to .github/hooks/scripts/lib/"

# --- 3. Hook registration ---
$HooksDest = Join-Path $TargetDir '.github\hooks'
if (-not (Test-Path $HooksDest)) { New-Item -ItemType Directory -Path $HooksDest -Force | Out-Null }
Copy-Item -Path (Join-Path $ScriptDir 'mc-prevent.json') -Destination $HooksDest -Force

Write-Host "  ✓ Hook registration copied to .github/hooks/mc-prevent.json"

Write-Host ""
Write-Host "Hook installation complete. Next steps:" -ForegroundColor Green
Write-Host "  1. Install the plugin (for skills + MCP):"
Write-Host "       copilot plugin install $PluginDir"
Write-Host "  2. Start a Copilot session:"
Write-Host "       copilot"
Write-Host "  3. The Monte Carlo MCP server will prompt for authentication on first use"
