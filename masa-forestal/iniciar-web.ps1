$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$mafPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $mafPython)) {
    throw 'Primero crea el entorno con: py -3.12 -m venv .venv; luego instala requirements-geospatial.txt. Consulta README.md.'
}
& $mafPython (Join-Path $PSScriptRoot 'server/http_server.py') @args
exit $LASTEXITCODE
