@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
 echo 未检测到 Python，请使用 GitHub Actions 自动构建，说明见 README.md
 pause
 exit /b 1
)
py -m pip install -r requirements.txt
if errorlevel 1 (pause & exit /b 1)
py -m PyInstaller --noconfirm --clean --windowed --onefile --name "oycy-PDF-Toolbox" --collect-all fitz --collect-all keyring --hidden-import keyring.backends.Windows app.py
if errorlevel 1 (pause & exit /b 1)
echo 构建完成：dist\oycy-PDF-Toolbox.exe
pause
