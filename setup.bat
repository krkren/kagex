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
:: Step 0: Administrator Check & Configuration
:: -----------------------------------------------------
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [FATAL ERROR] Administrative privileges required!
    echo To install Visual Studio, Git, or NASM, this script needs Admin rights.
    echo Please right-click this .bat file and select "Run as administrator".
    pause
    exit /b 1
)

set "ARCH=x64"
set "VCVARS_ARG=x64"
set "VCPKG_TRIPLET=x64-windows"
set "CMAKE_PRESET=x64-windows"
set "MSBUILD_PLATFORM=x64"

echo Please select the build configuration:
echo [1] Release
echo [2] Debug
choice /c 12 /n /m "Choose 1 or 2: "
if errorlevel 2 (
    set "CONFIG=Debug"
) else (
    set "CONFIG=Release"
)

echo.
echo [*] Configuration Set: %ARCH% / %CONFIG%
echo.

:: -----------------------------------------------------
:: Additional Build Variables
:: -----------------------------------------------------
set "TOOLSET=v143"
set "SDK_VER=10.0.22621.0"

:: -----------------------------------------------------
:: Step 1: Check and Install Git
:: -----------------------------------------------------
echo [*] Checking for Git...
set "GIT_EXE="
where git >nul 2>&1
if %errorlevel% equ 0 set "GIT_EXE=git"

if "!GIT_EXE!"=="" (
    if exist "%ProgramFiles%\Git\cmd\git.exe" (
        set "GIT_EXE=%ProgramFiles%\Git\cmd\git.exe"
    ) else (
        echo [*] Git not found. Downloading installer...
        curl -fL "https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe" -o "git_installer.exe" || goto :error
        echo [*] Launching Git installer. Please complete the setup wizard...
        start /wait "" git_installer.exe
        del "git_installer.exe"
        set "GIT_EXE=%ProgramFiles%\Git\cmd\git.exe"
    )
)

:: -----------------------------------------------------
:: Step 2: Skip NASM (not required for current build)

:: -----------------------------------------------------
:: Step 3: Check and Install Ninja Build System
:: -----------------------------------------------------
echo [*] Checking for Ninja build system...
set "NINJA_EXE="
where ninja >nul 2>&1
if %errorlevel% equ 0 set "NINJA_EXE=ninja"

if "!NINJA_EXE!"=="" (
    echo [*] Ninja not found. Downloading standalone executable...
    curl -fL "https://github.com/ninja-build/ninja/releases/download/v1.12.0/ninja-win.zip" -o "ninja.zip" || goto :error
    tar -xf "ninja.zip" || goto :error
    if not exist "%ROOT_DIR%\build_tools" mkdir "%ROOT_DIR%\build_tools"
    move /y "ninja.exe" "%ROOT_DIR%\build_tools\" >nul
    del "ninja.zip"
)

:: Ensure Ninja is temporarily in the PATH if we downloaded it
if exist "%ROOT_DIR%\build_tools\ninja.exe" (
    set "PATH=%ROOT_DIR%\build_tools;!PATH!"
)

:: -----------------------------------------------------
:: Step 4: Check and Install Visual Studio with ATL
:: -----------------------------------------------------
echo [*] Checking for Visual Studio and required ATL components...
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VS_INSTALL_DIR="

:: We now check explicitly for the ATL component as well
if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 Microsoft.VisualStudio.Component.VC.ATL -property installationPath`) do (
        set "VS_INSTALL_DIR=%%i"
    )
)

if "!VS_INSTALL_DIR!"=="" (
    echo [*] Visual Studio with C++ and ATL Tools not found.
    echo [*] Downloading the latest Visual Studio Community bootstrapper...
    curl -fL "https://aka.ms/vs/17/release/vs_community.exe" -o "vs_community.exe" || goto :error
    echo [*] Launching Visual Studio Installer...
    
    start "" vs_community.exe --nocache ^
        --add Microsoft.VisualStudio.Workload.NativeDesktop ^
        --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 ^
        --add Microsoft.VisualStudio.Component.Windows11SDK.22621 ^
        --add Microsoft.VisualStudio.Component.VC.ATL
        
    echo.
    echo ==========================================================
    echo IMPORTANT: WAIT FOR VISUAL STUDIO TO FINISH!
    echo The required C++ components ^(including ATL^) have been pre-selected.
    echo Please click "Modify" or "Install" in the Visual Studio window.
    echo.
    echo DO NOT PRESS ANY KEY HERE UNTIL VISUAL STUDIO IS 100%% DONE!
    echo ==========================================================
    pause
    del "vs_community.exe"

    if exist "%VSWHERE%" (
        for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 Microsoft.VisualStudio.Component.VC.ATL -property installationPath`) do (
            set "VS_INSTALL_DIR=%%i"
        )
    )
    
    if "!VS_INSTALL_DIR!"=="" (
        echo [ERROR] Visual Studio installation failed or ATL tools not found.
        goto :error
    )
)

set "VCVARS=!VS_INSTALL_DIR!\VC\Auxiliary\Build\vcvarsall.bat"
echo [*] Loading Visual Studio Environment for %VCVARS_ARG%...
call "%VCVARS%" %VCVARS_ARG% >nul

:: -----------------------------------------------------
:: Step 5: Setup vcpkg and Audio Dependencies
:: -----------------------------------------------------
echo.
echo [*] Checking vcpkg...
set "VCPKG_DIR=%ROOT_DIR%\vcpkg"

if not exist "%VCPKG_DIR%\vcpkg.exe" (
    echo [*] Installing vcpkg...
    if not exist "%VCPKG_DIR%" "!GIT_EXE!" clone https://github.com/microsoft/vcpkg.git "%VCPKG_DIR%" || goto :error
    pushd "%VCPKG_DIR%"
    call .\bootstrap-vcpkg.bat || goto :error
    popd
)

echo [*] Installing vcpkg dependencies (%VCPKG_TRIPLET%)...
call "%VCPKG_DIR%\vcpkg.exe" integrate install
call "%VCPKG_DIR%\vcpkg.exe" install libogg:%VCPKG_TRIPLET% libvorbis:%VCPKG_TRIPLET% || goto :error

set "VCPKG_ROOT=%VCPKG_DIR%"

:: -----------------------------------------------------
:: Step 6: Clone Repositories
:: -----------------------------------------------------
echo.
echo [*] Checking Repositories...
set "REPO_DIR=%ROOT_DIR%\krkrz_dev"
set "SAMPLE_DIR=%ROOT_DIR%\SamplePlugin"

if not exist "%REPO_DIR%" "!GIT_EXE!" clone --recursive https://github.com/wamsoft/krkrz_dev.git "%REPO_DIR%" || goto :error
if not exist "%SAMPLE_DIR%" "!GIT_EXE!" clone https://github.com/krkren/SamplePlugin.git "%SAMPLE_DIR%" || goto :error

:: -----------------------------------------------------
:: Step 7: Download and Place Legacy Stubs
:: -----------------------------------------------------
echo.
:: -----------------------------------------------------
:: Step 8: Initialize Git Submodules
:: -----------------------------------------------------
echo.
echo [*] Initializing git submodules (tp_stub)...
cd "%SAMPLE_DIR%"
"!GIT_EXE!" submodule update --init --recursive || goto :error
cd "%ROOT_DIR%"

:: -----------------------------------------------------
echo.
echo [*] Building krkrz_dev (%CMAKE_PRESET% / %CONFIG%)...
pushd "%REPO_DIR%"
if exist "build" rmdir /s /q "build"

cmake --preset %CMAKE_PRESET% || goto :error
cmake --build --preset %CMAKE_PRESET% --config %CONFIG% || goto :error
popd

:: -----------------------------------------------------
:: Step 11: Build extrans (CMake)
:: -----------------------------------------------------
echo.
echo [*] Building extrans (CMake)... 
pushd "%SAMPLE_DIR%"

set "EXTRANS_PRESET=x64"

if exist "build" rmdir /s /q "build"
cmake --preset %EXTRANS_PRESET% || goto :error
cmake --build build --config %CONFIG% || goto :error
popd

:: -----------------------------------------------------
:: Step 12: Move Files to Output
:: -----------------------------------------------------
echo.
echo [*] Moving required artifacts to final folder...


if not exist "plugin" mkdir "plugin"

set "BLD=krkrz_dev\build\%CMAKE_PRESET%"

:: Move krmovie.dll to plugin folder
move /y "!BLD!\%CONFIG%\krmovie.dll" "plugin" >nul 2>&1

:: Copy all plugin DLLs from build output (recursive) - TO PLUGIN FOLDER
:: Format: krkrz_dev/build/x64-windows/core/plugins/PLUGINNAME/CONFIG/PLUGINNAME.dll
for /d %%G in ("!BLD!\core\plugins\*") do copy /y "%%G\%CONFIG%\*.dll" "plugin" >nul 2>&1

:: Copy extrans.dll to plugin folder
move /y "SamplePlugin\build\%CONFIG%\extrans.dll" "plugin" >nul 2>&1

:: Move krkrz.exe and SDL3.dll (overwrite if they exist)
move /y "!BLD!\core\%CONFIG%\krkrz64.exe" "krkrz.exe" >nul 2>&1
move /y "!BLD!\core\%CONFIG%\SDL3.dll" "SDL3.dll" >nul 2>&1
move /y "!BLD!\core\%CONFIG%\krkrz64d.exe" "krkrz.exe" >nul 2>&1

:: -----------------------------------------------------
:: Step 13: Cleanup
:: -----------------------------------------------------
echo.
echo [*] Cleaning up source code, vcpkg, and legacy stubs for distribution...
if exist "%VCPKG_DIR%" rmdir /s /q "%VCPKG_DIR%"
if exist "%SAMPLE_DIR%" rmdir /s /q "%SAMPLE_DIR%"
if exist "%REPO_DIR%" rmdir /s /q "%REPO_DIR%"
if exist "%ROOT_DIR%\build_tools" rmdir /s /q "%ROOT_DIR%\build_tools"

if exist "tp_stub.h" del "tp_stub.h"
if exist "tp_stub.cpp" del "tp_stub.cpp"

echo.
echo ===================================================
echo [SUCCESS] Engine and plugins compiled successfully.
echo Output configured for: x64 %CONFIG%
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