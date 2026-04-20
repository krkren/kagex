@echo off
setlocal enabledelayedexpansion

:: Force the script to run in the directory where the .bat file is located
pushd "%~dp0"
set "ROOT_DIR=%cd%"

echo ===================================================
echo   Automated Master Build: krkrz_dev + Plugins
echo ===================================================
echo.

:: -----------------------------------------------------
:: Step 1: Find and Load the Visual Studio Environment
:: -----------------------------------------------------
echo [*] Locating Visual Studio installation...
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"

if not exist "%VSWHERE%" (
    echo [ERROR] Visual Studio Installer not found.
    goto :error
)

for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
    set "VS_INSTALL_DIR=%%i"
)

if "%VS_INSTALL_DIR%"=="" (
    echo [ERROR] Could not find a Visual Studio installation with C++ tools.
    goto :error
)

set "VCVARS=%VS_INSTALL_DIR%\VC\Auxiliary\Build\vcvars64.bat"
echo [*] Loading Visual Studio Environment...
call "%VCVARS%" >nul

:: -----------------------------------------------------
:: Step 2: Setup vcpkg and Audio Dependencies
:: -----------------------------------------------------
echo.
echo [*] Checking vcpkg...
set "VCPKG_DIR=%ROOT_DIR%\vcpkg"

if not exist "%VCPKG_DIR%\vcpkg.exe" (
    echo [*] Installing vcpkg...
    if not exist "%VCPKG_DIR%" git clone https://github.com/microsoft/vcpkg.git "%VCPKG_DIR%" || goto :error
    pushd "%VCPKG_DIR%"
    call .\bootstrap-vcpkg.bat || goto :error
    popd
)

echo [*] Installing vcpkg dependencies...
call "%VCPKG_DIR%\vcpkg.exe" integrate install
call "%VCPKG_DIR%\vcpkg.exe" install libogg:x64-windows libvorbis:x64-windows || goto :error

:: -----------------------------------------------------
:: Step 3: Clone Repositories
:: -----------------------------------------------------
echo.
echo [*] Checking Repositories...
set "REPO_DIR=%ROOT_DIR%\krkrz_dev"
set "WUV_DIR=%ROOT_DIR%\wuvorbis"
set "SAMPLE_DIR=%ROOT_DIR%\SamplePlugin"

if not exist "%REPO_DIR%" git clone --recursive https://github.com/wamsoft/krkrz_dev.git "%REPO_DIR%" || goto :error
if not exist "%WUV_DIR%" git clone https://github.com/krkrz/wuvorbis.git "%WUV_DIR%" || goto :error
if not exist "%SAMPLE_DIR%" git clone https://github.com/krkrz/SamplePlugin.git "%SAMPLE_DIR%" || goto :error

:: -----------------------------------------------------
:: Step 4: Download and Place Legacy Stubs
:: -----------------------------------------------------
echo.
echo [*] Downloading legacy stubs for plugin compatibility...
curl -fL "https://raw.githubusercontent.com/krkrz/krkrz_dev/master/src/plugins/win32/tp_stub.h" -o "tp_stub.h" || goto :error
curl -fL "https://raw.githubusercontent.com/krkrz/krkrz_dev/master/src/plugins/win32/tp_stub.cpp" -o "tp_stub.cpp" || goto :error

:: extrans expects stubs at ..\ so we put them in the SamplePlugin root
copy /y "tp_stub.*" "%SAMPLE_DIR%\" >nul

:: -----------------------------------------------------
:: Step 5: Build krkrz_dev (CMake)
:: -----------------------------------------------------
echo.
echo [*] Building krkrz_dev...
pushd "%REPO_DIR%"
if exist "build" rmdir /s /q "build"

cmake --preset x64-windows || goto :error
cmake --build --preset x64-windows --config Release || goto :error
popd

:: -----------------------------------------------------
:: Step 6: Build wuvorbis (MSBuild)
:: -----------------------------------------------------
echo.
echo [*] Building wuvorbis...
pushd "%WUV_DIR%"

set "TOOLSET=v%VCToolsVersion:~0,2%%VCToolsVersion:~3,1%"
set "SDK_VER=%WindowsSDKVersion:~0,-1%"

:: Using -m for multi-processor compilation (faster build)
msbuild wuvorbis64.vcxproj -m /p:Configuration=Release /p:Platform=x64 /p:WindowsTargetPlatformVersion=%SDK_VER% /p:PlatformToolset=%TOOLSET% /p:OutDir="%WUV_DIR%\x64\Release\\" || goto :error
popd

:: -----------------------------------------------------
:: Step 7: Build extrans (MSBuild)
:: -----------------------------------------------------
echo.
echo [*] Building extrans...
pushd "%SAMPLE_DIR%\extrans"

msbuild extrans.vcxproj -m /p:Configuration=Release /p:Platform=x64 /p:WindowsTargetPlatformVersion=%SDK_VER% /p:PlatformToolset=%TOOLSET% /p:OutDir="bin\\" || goto :error
popd

:: -----------------------------------------------------
:: Step 8: Move Files to Output
:: -----------------------------------------------------
echo.
echo [*] Moving required artifacts to final folder...
if not exist "plugin" mkdir "plugin"

:: Engine
move /y "krkrz_dev\build\x64-windows\core\Release\krkrz64.exe" "krkrz.exe" >nul

:: Explicit Standard Plugins (Minimalism)
move /y "krkrz_dev\build\x64-windows\Release\krmovie.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\KAGParserEx\Release\KAGParserEx.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\csvParser\Release\csvParser.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\fstat\Release\fstat.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\LayerExBTOA\Release\LayerExBTOA.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\LayerExDraw\Release\LayerExDraw.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\LayerExImage\Release\LayerExImage.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\LayerExRaster\Release\LayerExRaster.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\menu\Release\menu.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\saveStruct\Release\saveStruct.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\scriptsEx\Release\scriptsEx.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\shrinkCopy\Release\shrinkCopy.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\win32dialog\Release\win32dialog.dll" "plugin\" >nul
move /y "krkrz_dev\build\x64-windows\core\plugins\windowEx\Release\windowEx.dll" "plugin\" >nul

:: Custom Built Plugins
move /y "wuvorbis\x64\Release\wuvorbis.dll" "plugin\" >nul
move /y "SamplePlugin\extrans\bin\extrans.dll" "plugin\" >nul

:: -----------------------------------------------------
:: Step 9: Cleanup
:: -----------------------------------------------------
echo.
echo [*] Cleaning up source code, vcpkg, and legacy stubs for distribution...
if exist "%VCPKG_DIR%" rmdir /s /q "%VCPKG_DIR%"
if exist "%REPO_DIR%" rmdir /s /q "%REPO_DIR%"
if exist "%WUV_DIR%" rmdir /s /q "%WUV_DIR%"
if exist "%SAMPLE_DIR%" rmdir /s /q "%SAMPLE_DIR%"

:: Wipe the root stubs
if exist "tp_stub.h" del "tp_stub.h"
if exist "tp_stub.cpp" del "tp_stub.cpp"

echo.
echo ===================================================
echo [SUCCESS] Engine and plugins compiled successfully.
echo ===================================================
popd
pause
exit /b 0

:error
echo.
echo ===================================================
echo [FATAL ERROR] The build process encountered an error!
echo ===================================================
popd
pause
exit /b 1