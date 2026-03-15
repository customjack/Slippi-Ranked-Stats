@echo off
title Slippi Ranked Stats - Setup
cd /d "%~dp0"

:: Check Python is available
py --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

:: First run: create venv and install dependencies
if not exist ".venv\Scripts\streamlit.exe" (
    echo First run: setting up environment. This takes about a minute...
    echo.
    py -m venv .venv
    .venv\Scripts\pip install -q -r requirements.txt
    echo.
    echo Setup complete!
    echo.
)

:: Convert crest.jpg to crest.ico for the shortcut icon (once)
if not exist "crest.ico" (
    .venv\Scripts\python -c "import numpy as np; from PIL import Image; img=Image.open('Slippi Ranked Stats Crest.png').convert('RGBA'); d=np.array(img); d[(d[:,:,0]>220)&(d[:,:,1]>220)&(d[:,:,2]>220),3]=0; Image.fromarray(d).resize((256,256)).save('crest.ico')"
)

:: Create a Desktop shortcut on first run so users never need this file again
if not exist "%USERPROFILE%\Desktop\Slippi Ranked Stats.lnk" (
    powershell -Command ^
        "$ws = New-Object -ComObject WScript.Shell;" ^
        "$s = $ws.CreateShortcut('%USERPROFILE%\Desktop\Slippi Ranked Stats.lnk');" ^
        "$s.TargetPath = 'wscript.exe';" ^
        "$s.Arguments = '\"%~dp0Slippi Ranked Stats.vbs\"';" ^
        "$s.WorkingDirectory = '%~dp0';" ^
        "$s.IconLocation = '%~dp0crest.ico';" ^
        "$s.Description = 'Slippi Ranked Stats';" ^
        "$s.Save()"
    echo Desktop shortcut created! You can use that from now on.
    echo.
)

:: Hand off to the silent VBS launcher and close this window
echo Launching Slippi Ranked Stats...
start "" wscript.exe "%~dp0Slippi Ranked Stats.vbs"
exit
