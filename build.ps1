$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    $python = Join-Path $PSScriptRoot ".venv312/Scripts/python.exe"
    $stage = Join-Path ([IO.Path]::GetTempPath()) ("ledger-build-" + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $stage | Out-Null
    & $python -m PyInstaller --noconfirm --onedir --windowed --name "个人账本" --distpath "$stage/dist" --workpath "$stage/work" --specpath $stage --exclude-module pandas --exclude-module numpy --exclude-module matplotlib --exclude-module PIL --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets main.py
    if ($LASTEXITCODE) { throw "PyInstaller build failed" }
    $releaseRoot = Join-Path $PSScriptRoot "releases"
    New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
    $dest = Join-Path $releaseRoot ("个人账本-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
    Move-Item -LiteralPath "$stage/dist/个人账本" -Destination $dest
    foreach ($dll in "icuuc.dll", "icudt78.dll") {
        $path = Join-Path $dest "_internal/$dll"
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
    }
    Write-Host "干净发布目录：$dest"
} finally {
    Pop-Location
}
