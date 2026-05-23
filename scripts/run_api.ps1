$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\services\api"
if (-not (Test-Path ".venv")) {
  $python = (Get-Command python -ErrorAction SilentlyContinue)
  if (-not $python) {
    $python = (Get-Command py -ErrorAction SilentlyContinue)
  }
  if (-not $python) {
    throw "Python was not found. Install Python or run with an existing services/api/.venv."
  }
  & $python.Source -m venv .venv
}
$venvPython = ".\.venv\Scripts\python.exe"
& $venvPython -m pip install -q -r requirements.txt
$env:PYTHONPATH = "$root\packages\factor-engine;$root\packages\strategy-selector"
& $venvPython -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
