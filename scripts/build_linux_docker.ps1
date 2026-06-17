param(
    [string]$Image = "python:3.12-slim",
    [string]$OutputName = "woke-menu-linux"
)

$ErrorActionPreference = "Stop"

$repo = (Resolve-Path "$PSScriptRoot\..").Path
$containerRepo = "/workspace"

docker run --rm `
    -v "${repo}:${containerRepo}" `
    -w $containerRepo `
    $Image `
    bash -lc "python -m pip install --upgrade pip && python -m pip install -r requirements.txt pyinstaller ebooklib && python -m PyInstaller --name woke-menu --onedir --console --clean -y --add-data 'steps:steps' --add-data 'steps_en:steps_en' --add-data 'i18n:i18n' --add-data 'assets:assets' --add-data '.menu_config.json:.' menu.py && cd dist && tar -czf ../${OutputName}.tar.gz woke-menu"

Write-Host "Linux package written to: $repo\$OutputName.tar.gz"
