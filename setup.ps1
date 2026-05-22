$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Get-PythonCommand {
    if (Test-Path ".venv\Scripts\python.exe") {
        return ".venv\Scripts\python.exe"
    }

    try {
        py -3.12 -c "import sys" | Out-Null
        return "py -3.12"
    } catch {
        try {
            py -3.11 -c "import sys" | Out-Null
            return "py -3.11"
        } catch {
            return "py -3"
        }
    }
}

$pythonCmd = Get-PythonCommand
Write-Host "Using $pythonCmd"
Invoke-Expression "$pythonCmd -c `"import sys; print('Python:', sys.version)`""

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host ""
    Write-Host "Creating virtual environment..."
    Invoke-Expression "$pythonCmd -m venv .venv"
    $pythonCmd = ".venv\Scripts\python.exe"
}

Write-Host ""
Write-Host "Installing core JarvisAssistant dependencies..."
Invoke-Expression "$pythonCmd -m pip install --upgrade pip"
Invoke-Expression "$pythonCmd -m pip install -r requirements.txt -r requirements-dev.txt"

$pyVersion = (Invoke-Expression "$pythonCmd -c `"import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')`"").Trim()
Write-Host ""
if ($pyVersion -in @("3.11", "3.12")) {
    Write-Host "Installing optional local voice dependencies..."
    try {
        Invoke-Expression "$pythonCmd -m pip install -r requirements-voice.txt"
        Invoke-Expression "$pythonCmd scripts\download_voice_assets.py --kokoro"
    } catch {
        Write-Warning "Optional voice dependencies failed to install. Jarvis will continue with partial voice support."
    }
} else {
    Write-Warning "Python $pyVersion detected. Full faster-whisper/openWakeWord setup is most reliable on Python 3.11 or 3.12."
    Write-Host "Skipping the full optional speech package install on this interpreter."
}

Write-Host ""
Write-Host "Probing local AI providers..."
Invoke-Expression "$pythonCmd scripts\test_ai_connection.py --probe-only"

Write-Host ""
Write-Host "Running startup smoke test..."
Invoke-Expression "$pythonCmd scripts\test_app_startup.py"

Write-Host ""
Write-Host "Setup complete."
Write-Host "If LM Studio is running, load a model and enable its local server."
Write-Host "If Ollama is running, Jarvis can use it automatically as a fallback."
Write-Host "For full speech recognition, use a Python 3.11 or 3.12 environment and rerun scripts\install_voice_stack.bat."
