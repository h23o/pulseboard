# setup_venv.ps1 – Create a Python 3.12 venv and install all dependencies
Set-Location "C:\Users\harri\Documents\pulse\pulseboard"

Write-Host "Creating Python 3.12 virtual environment..."
uv venv .venv --python 3.12

Write-Host "Installing dependencies..."
uv pip install --python .venv\Scripts\python.exe -r requirements.txt

Write-Host "Done! Venv is at .venv\"
Write-Host "dbt is at: .venv\Scripts\dbt.exe"
