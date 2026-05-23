$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\apps\web"
if (-not (Test-Path "node_modules")) {
  npm.cmd install
}
npm.cmd run dev
