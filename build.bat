@echo off
echo Compiling FluTool project with PyInstaller starting...

REM 删除旧的打包文件以避免缓存
if exist "dist\FluTool" rmdir /s /q "dist\FluTool"
if exist "build" rmdir /s /q "build"

pyinstaller --noconfirm --onedir --windowed ^
      --icon "logo.ico" ^
      --name "FluTool" ^
      --clean ^
      --collect-all qfluentwidgets ^
      --collect-all qframelesswindow ^
      --collect-all plugins ^
      --collect-submodules ui ^
      --collect-submodules core ^
      --collect-submodules utils ^
      --hidden-import "uuid" ^
      --hidden-import "darkdetect" ^
      --hidden-import "PyQt5.sip" ^
      --hidden-import "PyQt5.QtXml" ^
      --hidden-import "PyQt5.QtSvg" ^
      --hidden-import "PyQt5.QtNetwork" ^
      --hidden-import "requests" ^
      --hidden-import "qframelesswindow" ^
      --hidden-import "charset_normalizer" ^
      --hidden-import "bs4" ^
      --hidden-import "loguru" ^
      --add-data "data;data/" ^
      --add-data "config;config/" ^
      --add-data "logo.ico;." ^
      --add-data "ui/resources;ui/resources/" ^
      --add-data "plugins_sourcecode;plugins_sourcecode/" ^
      --exclude-module "tests" ^
      --exclude-module "WebEngineWidgets" ^
      --exclude-module "WebEngineCore" ^
      --exclude-module "numpy" ^
      --exclude-module "scipy" ^
      --exclude-module "PyQt5.QtWebEngineWidgets" ^
      --exclude-module "PyQt5.QtWebEngineCore" ^
      --exclude-module "PyQt5.QtBluetooth" ^
      --exclude-module "PyQt5.QtNfc" ^
      --exclude-module "PyQt5.QtSerialPort" ^
      --exclude-module "PyQt5.QtLocation" ^
      --exclude-module "PyQt5.QtPositioning" ^
      --exclude-module "PyQt5.QtMultimedia" ^
      --exclude-module "PyQt5.QtTextToSpeech" ^
      --exclude-module "PyQt5.QtQuick3D" ^
      --exclude-module "PyQt5.QtSensors" ^
      --exclude-module "PyQt5.Qt3DCore" ^
      --exclude-module "PyQt5.Qt3DRender" ^
      --exclude-module "PyQt5.Qt3DInput" ^
      --exclude-module "PyQt5.Qt3DLogic" ^
      --exclude-module "PyQt5.Qt3DAnimation" ^
      --exclude-module "PyQt5.Qt3DExtras" ^
      "main.py"

if %errorlevel% equ 0 (
    color 0A
    echo Compilation completed!
) else (
    color 0C
    echo Compilation failed!
)
color 07
