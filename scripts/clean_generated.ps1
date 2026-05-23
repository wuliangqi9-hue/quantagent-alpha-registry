$root = Split-Path -Parent $PSScriptRoot

$targets = @(
  "$root\apps\web\dist",
  "$root\contracts\cache",
  "$root\contracts\artifacts\build-info"
)

foreach ($target in $targets) {
  if (Test-Path $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
    Write-Host "Removed $target"
  }
}

Write-Host "Generated files cleaned. Keep source files, sample data, and compact ABI artifacts."
