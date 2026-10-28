$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'MSVC x64 build tools required' }
$vcvars = Join-Path $vs 'VC/Auxiliary/Build/vcvars64.bat'
$lines = & cmd.exe /d /c "call `"$vcvars`" >nul && set"
if ($LASTEXITCODE) { throw 'MSVC environment setup failed' }
foreach ($line in $lines) {
    if ($line -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') }
}
python -m pip install maturin==1.9.6
if ($LASTEXITCODE) { throw 'Maturin setup failed' }
python -m maturin build --release --locked --interpreter python --out dist
if ($LASTEXITCODE) { throw 'Wheel build failed' }
