@echo off
echo Compiling FluTool project with PyInstaller starting...

pyinstaller --noconfirm --onedir --windowed ^
      --icon "logo.ico" ^
      --name "FluTool" ^
      --clean ^
      --collect-all qfluentwidgets ^
      --collect-all plugins ^
      --collect-submodules ui ^
      --collect-submodules core ^
      --collect-submodules utils ^
      --hidden-import "uuid" ^
      --hidden-import "darkdetect" ^
      --hidden-import "PyQt5.sip" ^
      --hidden-import "PyQt5.QtXml" ^
      --hidden-import "PyQt5.QtSvg" ^
      --hidden-import "requests" ^
      --hidden-import "qframelesswindow" ^
      --hidden-import "charset_normalizer" ^
      --hidden-import "bs4" ^
      --add-data "data;data/" ^
      --add-data "config;config/" ^
      --add-data "logo.ico;." ^
      --add-data "ui/resources;ui/resources/" ^
      --exclude-module "tests" ^
      "main.py"

if %errorlevel% equ 0 (
    color 0A
    echo Compilation completed!
) else (
    color 0C
    echo Compilation failed!
)
color 07
