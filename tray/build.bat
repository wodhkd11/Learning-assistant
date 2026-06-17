@echo off
cd /d C:\Users\wodhk\Desktop\Learning
echo [KALF] PyInstaller 빌드 시작...

pyinstaller --onefile --windowed --noconsole ^
  --name "KALF" ^
  --icon "tray\icon_green.png" ^
  --add-data "tray\icon_green.png;tray" ^
  --add-data "tray\icon_gray.png;tray" ^
  --add-data ".env;." ^
  --hidden-import "pystray._win32" ^
  --hidden-import "dotenv" ^
  tray\tray.py

echo.
if exist dist\KALF.exe (
    echo [KALF] 빌드 완료. dist\KALF.exe 를 실행하세요.
) else (
    echo [KALF] 빌드 실패. 로그를 확인하세요.
)
pause
