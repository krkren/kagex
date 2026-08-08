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

echo Please select the build architecture:
echo [1] 64-bit (x64)
echo [2] 32-bit (x86)
choice /c 12 /n /m "Choose 1 or 2: "
if errorlevel 2 (
    set "ARCH=x86"
    set "VCVARS_ARG=x86"
    set "VCPKG_TRIPLET=x86-windows"
    set "CMAKE_PRESET=x86-windows-win"
    set "MSBUILD_PLATFORM=Win32"
    set "WUV_PROJ=wuvorbis.vcxproj"
) else (
    set "ARCH=x64"
    set "VCVARS_ARG=x64"
    set "VCPKG_TRIPLET=x64-windows"
    set "CMAKE_PRESET=x64-windows-win"
    set "MSBUILD_PLATFORM=x64"
    set "WUV_PROJ=wuvorbis64.vcxproj"
)

echo.
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
:: Step 2: Check and Install NASM (Downgraded to 2.14.02)
:: -----------------------------------------------------
echo [*] Checking for NASM...
set "NASM_EXE="

:: 1. Check explicit folders FIRST to bypass devkitPro/MSYS2 PATH pollution
if exist "%ProgramFiles%\NASM\nasm.exe" set "NASM_EXE=%ProgramFiles%\NASM\nasm.exe"
if "!NASM_EXE!"=="" if exist "%ProgramFiles(x86)%\NASM\nasm.exe" set "NASM_EXE=%ProgramFiles(x86)%\NASM\nasm.exe"
if "!NASM_EXE!"=="" if exist "%LocalAppData%\NASM\nasm.exe" set "NASM_EXE=%LocalAppData%\NASM\nasm.exe"
if "!NASM_EXE!"=="" if exist "%LocalAppData%\Programs\NASM\nasm.exe" set "NASM_EXE=%LocalAppData%\Programs\NASM\nasm.exe"
if "!NASM_EXE!"=="" if exist "%LocalAppData%\bin\NASM\nasm.exe" set "NASM_EXE=%LocalAppData%\bin\NASM\nasm.exe"

:: 2. Only check system PATH as a fallback
if "!NASM_EXE!"=="" (
    where nasm >nul 2>&1
    if !errorlevel! equ 0 set "NASM_EXE=nasm"
)

:: 3. If found, safely check the version
if not "!NASM_EXE!"=="" (
    for /f "usebackq tokens=3" %%v in (`"!NASM_EXE!" -v`) do set "NASM_VER=%%v"
    echo [*] Found NASM version: !NASM_VER!
)

:: 4. Determine if we need to force an install
if "!NASM_EXE!"=="" (
    set "FORCE_NASM=1"
) else if "!NASM_VER:~0,4!"=="2.15" (
    set "FORCE_NASM=1"
) else if "!NASM_VER:~0,4!"=="2.16" (
    set "FORCE_NASM=1"
) else if "!NASM_VER:~0,4!"=="2.17" (
    set "FORCE_NASM=1"
) else (
    set "FORCE_NASM=0"
)

:: 5. Install if missing or incompatible
if "!FORCE_NASM!"=="1" (
    echo [*] Incompatible NASM version detected. Forcing 2.14.02 install...
    curl -fL "https://www.nasm.us/pub/nasm/releasebuilds/2.14.02/win64/nasm-2.14.02-installer-x64.exe" -o "nasm_installer.exe" || goto :error
    echo [*] Launching NASM installer. Please complete the setup wizard...
    start /wait "" nasm_installer.exe
    del "nasm_installer.exe"
    
    :: Re-acquire the exact executable path to guarantee we use the fresh install
    if exist "%ProgramFiles%\NASM\nasm.exe" set "NASM_EXE=%ProgramFiles%\NASM\nasm.exe"
    if "!NASM_EXE!"=="" if exist "%LocalAppData%\NASM\nasm.exe" set "NASM_EXE=%LocalAppData%\NASM\nasm.exe"
    if "!NASM_EXE!"=="" if exist "%LocalAppData%\bin\NASM\nasm.exe" set "NASM_EXE=%LocalAppData%\bin\NASM\nasm.exe"
)

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
:: Step 4: Check and Install Visual Studio with ATL & CMake
:: -----------------------------------------------------
echo [*] Checking for Visual Studio and required C++ components...
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VS_INSTALL_DIR="

:: Check explicitly for the C++ tools, ATL, and CMake components
if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 Microsoft.VisualStudio.Component.VC.ATL Microsoft.VisualStudio.Component.VC.CMake.Project -property installationPath`) do (
        set "VS_INSTALL_DIR=%%i"
    )
)

if "!VS_INSTALL_DIR!"=="" (
    echo [*] Visual Studio with required components ^(C++, ATL, CMake^) not found.
    echo [*] Downloading the latest Visual Studio Community bootstrapper...
    curl -fL "https://aka.ms/vs/17/release/vs_community.exe" -o "vs_community.exe" || goto :error
    echo [*] Launching Visual Studio Installer...
    
    start "" vs_community.exe --nocache ^
        --add Microsoft.VisualStudio.Workload.NativeDesktop ^
        --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 ^
        --add Microsoft.VisualStudio.Component.Windows11SDK.22621 ^
        --add Microsoft.VisualStudio.Component.VC.ATL ^
        --add Microsoft.VisualStudio.Component.VC.CMake.Project
        
    echo.
    echo ==========================================================
    echo IMPORTANT: WAIT FOR VISUAL STUDIO TO FINISH!
    echo The required C++ components ^(including ATL and CMake^) have been pre-selected.
    echo Please click "Modify" or "Install" in the Visual Studio window.
    echo.
    echo DO NOT PRESS ANY KEY HERE UNTIL VISUAL STUDIO IS 100%% DONE!
    echo ==========================================================
    pause
    del "vs_community.exe"

    :: Re-verify installation after the user finishes the prompt
    if exist "%VSWHERE%" (
        for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 Microsoft.VisualStudio.Component.VC.ATL Microsoft.VisualStudio.Component.VC.CMake.Project -property installationPath`) do (
            set "VS_INSTALL_DIR=%%i"
        )
    )
    
    if "!VS_INSTALL_DIR!"=="" (
        echo [ERROR] Visual Studio installation failed or components are still missing.
        goto :error
    )
)

set "VCVARS=!VS_INSTALL_DIR!\VC\Auxiliary\Build\vcvarsall.bat"
echo [*] Loading Visual Studio Environment for %VCVARS_ARG%...
call "%VCVARS%" %VCVARS_ARG% >nul

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
:: Step 6: Clone Repositories (Shallow)
:: -----------------------------------------------------
echo.
echo [*] Checking Repositories...
set "REPO_DIR=%ROOT_DIR%\krkrz_dev"
set "WUV_DIR=%ROOT_DIR%\wuvorbis"
set "SAMPLE_DIR=%ROOT_DIR%\SamplePlugin"

:: Use --depth 1 and --shallow-submodules to drastically reduce download size and time
if not exist "%REPO_DIR%" "!GIT_EXE!" clone --depth 1 --shallow-submodules --recursive https://github.com/wamsoft/krkrz_dev.git "%REPO_DIR%" || goto :error
if not exist "%WUV_DIR%" "!GIT_EXE!" clone --depth 1 https://github.com/krkrz/wuvorbis.git "%WUV_DIR%" || goto :error
if not exist "%SAMPLE_DIR%" "!GIT_EXE!" clone --depth 1 https://github.com/krkrz/SamplePlugin.git "%SAMPLE_DIR%" || goto :error

:: -----------------------------------------------------
:: Step 7: Download and Place Legacy Stubs
:: -----------------------------------------------------
echo.
echo [*] Downloading legacy stubs for plugin compatibility...
curl -fL "https://raw.githubusercontent.com/krkrz/krkrz_dev/master/src/plugins/win32/tp_stub.h" -o "tp_stub.h" || goto :error
curl -fL "https://raw.githubusercontent.com/krkrz/krkrz_dev/master/src/plugins/win32/tp_stub.cpp" -o "tp_stub.cpp" || goto :error

copy /y "tp_stub.*" "%SAMPLE_DIR%\" >nul

:: -----------------------------------------------------
:: Step 8: Patch Legacy MSBuild Projects
:: -----------------------------------------------------
echo.
echo [*] Patching legacy .vcxproj files for modern MSVC compatibility...
powershell -Command "(Get-Content '%WUV_DIR%\wuvorbis.vcxproj') -replace 'EditAndContinue', 'ProgramDatabase' -replace '<MinimalRebuild>true</MinimalRebuild>', '<MinimalRebuild>false</MinimalRebuild>' | Set-Content '%WUV_DIR%\wuvorbis.vcxproj'"
powershell -Command "(Get-Content '%WUV_DIR%\wuvorbis64.vcxproj') -replace 'EditAndContinue', 'ProgramDatabase' -replace '<MinimalRebuild>true</MinimalRebuild>', '<MinimalRebuild>false</MinimalRebuild>' | Set-Content '%WUV_DIR%\wuvorbis64.vcxproj'"
powershell -Command "(Get-Content '%SAMPLE_DIR%\extrans\extrans.vcxproj') -replace 'EditAndContinue', 'ProgramDatabase' -replace '<MinimalRebuild>true</MinimalRebuild>', '<MinimalRebuild>false</MinimalRebuild>' | Set-Content '%SAMPLE_DIR%\extrans\extrans.vcxproj'"

:: -----------------------------------------------------
:: Step 9: Build krkrz_dev (CMake)
:: -----------------------------------------------------
echo.
echo [*] Building krkrz_dev (%CMAKE_PRESET% / %CONFIG%)...
pushd "%REPO_DIR%"
if exist "build" rmdir /s /q "build"

:: Force the use of Visual Studio's bundled CMake to prevent MSYS2/MinGW conflicts
set "VS_CMAKE=!VS_INSTALL_DIR!\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"

:: Verify that the CMake component is actually installed
if not exist "!VS_CMAKE!" (
    echo [ERROR] Visual Studio CMake not found!
    echo Please open the Visual Studio Installer, click Modify, and add "C++ CMake tools for Windows".
    popd
    goto :error
)

"!VS_CMAKE!" --preset %CMAKE_PRESET% -DCMAKE_ASM_NASM_COMPILER="!NASM_EXE!" || goto :error
"!VS_CMAKE!" --build --preset %CMAKE_PRESET% --config %CONFIG% || goto :error
popd

:: -----------------------------------------------------
:: Step 10: Build wuvorbis (MSBuild)
:: -----------------------------------------------------
echo.
echo [*] Building wuvorbis (%MSBUILD_PLATFORM% / %CONFIG%)...
pushd "%WUV_DIR%"

:: Securely determine the correct PlatformToolset based on VS version
set "TOOLSET=v143"
if "%VisualStudioVersion%"=="16.0" set "TOOLSET=v142"
if "%VisualStudioVersion%"=="15.0" set "TOOLSET=v141"
set "SDK_VER=%WindowsSDKVersion:~0,-1%"

msbuild %WUV_PROJ% -m /p:Configuration=%CONFIG% /p:Platform=%MSBUILD_PLATFORM% /p:WindowsTargetPlatformVersion=%SDK_VER% /p:PlatformToolset=%TOOLSET% /p:OutDir="%WUV_DIR%\%MSBUILD_PLATFORM%\%CONFIG%\\" || goto :error
popd

:: -----------------------------------------------------
:: Step 11: Build extrans (MSBuild)
:: -----------------------------------------------------
echo.
echo [*] Building extrans (%MSBUILD_PLATFORM% / %CONFIG%)...
pushd "%SAMPLE_DIR%\extrans"

msbuild extrans.vcxproj -m /p:Configuration=%CONFIG% /p:Platform=%MSBUILD_PLATFORM% /p:WindowsTargetPlatformVersion=%SDK_VER% /p:PlatformToolset=%TOOLSET% /p:OutDir="bin\%MSBUILD_PLATFORM%\%CONFIG%\\" || goto :error
popd

:: -----------------------------------------------------
:: Step 12: Move Files to Output
:: -----------------------------------------------------
echo.
echo [*] Moving required artifacts to final folder...
if not exist "plugin" mkdir "plugin"

set "BLD=krkrz_dev\build\%CMAKE_PRESET%"

if "%ARCH%"=="x64" (
    move /y "!BLD!\core\%CONFIG%\krkrz64.exe" "krkrz.exe" >nul 2>&1
    move /y "!BLD!\core\%CONFIG%\krkrz64d.exe" "krkrz.exe" >nul 2>&1
) else (
    move /y "!BLD!\core\%CONFIG%\krkrz.exe" "krkrz.exe" >nul 2>&1
    move /y "!BLD!\core\%CONFIG%\krkrzd.exe" "krkrz.exe" >nul 2>&1
)

move /y "!BLD!\%CONFIG%\krmovie.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\KAGParserEx\%CONFIG%\KAGParserEx.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\csvParser\%CONFIG%\csvParser.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\fstat\%CONFIG%\fstat.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\LayerExBTOA\%CONFIG%\LayerExBTOA.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\LayerExDraw\%CONFIG%\LayerExDraw.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\LayerExImage\%CONFIG%\LayerExImage.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\LayerExRaster\%CONFIG%\LayerExRaster.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\menu\%CONFIG%\menu.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\saveStruct\%CONFIG%\saveStruct.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\scriptsEx\%CONFIG%\scriptsEx.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\shrinkCopy\%CONFIG%\shrinkCopy.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\win32dialog\%CONFIG%\win32dialog.dll" "plugin\" >nul
move /y "!BLD!\core\plugins\windowEx\%CONFIG%\windowEx.dll" "plugin\" >nul

move /y "wuvorbis\%MSBUILD_PLATFORM%\%CONFIG%\wuvorbis.dll" "plugin\" >nul
move /y "SamplePlugin\extrans\bin\%MSBUILD_PLATFORM%\%CONFIG%\extrans.dll" "plugin\" >nul

:: -----------------------------------------------------
:: Step 13: Cleanup
:: -----------------------------------------------------
echo.
echo [*] Cleaning up source code, vcpkg, and legacy stubs for distribution...
if exist "%VCPKG_DIR%" rmdir /s /q "%VCPKG_DIR%"
if exist "%REPO_DIR%" rmdir /s /q "%REPO_DIR%"
if exist "%WUV_DIR%" rmdir /s /q "%WUV_DIR%"
if exist "%SAMPLE_DIR%" rmdir /s /q "%SAMPLE_DIR%"
if exist "%ROOT_DIR%\build_tools" rmdir /s /q "%ROOT_DIR%\build_tools"

if exist "tp_stub.h" del "tp_stub.h"
if exist "tp_stub.cpp" del "tp_stub.cpp"

echo.
echo ===================================================
echo [SUCCESS] Engine and plugins compiled successfully.
echo Output configured for: %ARCH% %CONFIG%
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