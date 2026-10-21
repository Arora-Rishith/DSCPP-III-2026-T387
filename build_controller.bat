@echo off
setlocal
cd /d "%~dp0"
echo Building C++ bridge using your existing Module 2 and Module 3...
g++ -std=c++17 -O2 ModuleBridge.cpp -o ModuleBridge.exe
if errorlevel 1 (
  echo.
  echo Build failed. Install a C++ compiler such as MinGW-w64 and make sure g++ is in PATH.
  exit /b 1
)
echo Build successful: ModuleBridge.exe
endlocal
