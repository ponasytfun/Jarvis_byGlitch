param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$targets = @(
    ".venv",
    ".venv-py314-backup",
    "build",
    "dist",
    "logs",
    "__pycache__",
    "jarvis_assistant\__pycache__",
    "scripts\__pycache__"
)

foreach ($target in $targets) {
    $resolved = Join-Path $root $target
    if (Test-Path -LiteralPath $resolved) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
        Write-Host "Removed $target"
    }
}

Get-ChildItem -LiteralPath $root -Filter "jarvis_ui_capture*.png" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Force
    Write-Host "Removed $($_.Name)"
}

Write-Host ""
Write-Host "Developer copy cleanup complete."
Write-Host "Local runtime data in %APPDATA%\JarvisAssistant is not part of the repo."
