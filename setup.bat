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
    echo To automatically install Visual Studio, Git, or NASM, this script needs Admin rights.
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
    set "CMAKE_PRESET=x86-windows"
    set "MSBUILD_PLATFORM=Win32"
    set "WUV_PROJ=wuvorbis.vcxproj"
) else (
    set "ARCH=x64"
    set "VCVARS_ARG=x64"
    set "VCPKG_TRIPLET=x64-windows"
    set "CMAKE_PRESET=x64-windows"
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
        echo [*] Git not found. Downloading standalone installer...
        curl -fL "https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe" -o "git_installer.exe" || goto :error
        echo [*] Installing Git silently...
        start /wait "" git_installer.exe /VERYSILENT /NORESTART /NOCANCEL /SP- /SUPPRESSMSGBOXES
        del "git_installer.exe"
        set "GIT_EXE=%ProgramFiles%\Git\cmd\git.exe"
    )
)

:: -----------------------------------------------------
:: Step 2: Check and Install NASM (Downgraded to 2.14.02)
:: -----------------------------------------------------
echo [*] Checking for NASM...
set "NASM_EXE="
where nasm >nul 2>&1
if %errorlevel% equ 0 (
    :: Grab the version to ensure it isn't the broken 2.15+
    for /f "tokens=3" %%v in ('nasm -v') do set "NASM_VER=%%v"
    set "NASM_EXE=nasm"
)

:: Force install NASM 2.14.02 if NASM isn't found OR if a newer breaking version is found
if "!NASM_EXE!"=="" (set "FORCE_NASM=1") else if "!NASM_VER:~0,4!"=="2.15" (set "FORCE_NASM=1") else if "!NASM_VER:~0,4!"=="2.16" (set "FORCE_NASM=1") else (set "FORCE_NASM=0")

if "!FORCE_NASM!"=="1" (
    echo [*] Compatible NASM not found or incompatible version detected.
    echo [*] Downloading NASM 2.14.02 installer ^(required for krkrz macro support^)...
    curl -fL "https://www.nasm.us/pub/nasm/releasebuilds/2.14.02/win64/nasm-2.14.02-installer-x64.exe" -o "nasm_installer.exe" || goto :error
    echo [*] Installing NASM silently...
    start /wait "" nasm_installer.exe /S
    del "nasm_installer.exe"
    
    if exist "%ProgramFiles%\NASM\nasm.exe" (
        set "NASM_EXE=%ProgramFiles%\NASM\nasm.exe"
    ) else if exist "%LocalAppData%\bin\NASM\nasm.exe" (
        set "NASM_EXE=%LocalAppData%\bin\NASM\nasm.exe"
    )
)

:: Fallback direct path check if `where` failed but it exists
if "!NASM_EXE!"=="" (
    if exist "%ProgramFiles%\NASM\nasm.exe" set "NASM_EXE=%ProgramFiles%\NASM\nasm.exe"
)

:: -----------------------------------------------------
:: Step 3: Check and Install Visual Studio C++ Tools
:: -----------------------------------------------------
echo [*] Checking for Visual Studio C++ Build Tools...
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VS_INSTALL_DIR="

if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
        set "VS_INSTALL_DIR=%%i"
    )
)

if "!VS_INSTALL_DIR!"=="" (
    echo [*] VS C++ Tools not found. Downloading VS Build Tools bootstrapper...
    curl -fL "https://aka.ms/vs/17/release/vs_BuildTools.exe" -o "vs_buildtools.exe" || goto :error
    echo [*] Installing Visual Studio C++ Workload...
    echo [!] WARNING: This is running silently and may take 5-15 minutes. Do not close this window.
    start /wait "" vs_buildtools.exe --quiet --wait --norestart --nocache ^
        --add Microsoft.VisualStudio.Workload.VCTools ^
        --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 ^
        --add Microsoft.VisualStudio.Component.Windows11SDK.22621
    del "vs_buildtools.exe"

    :: Re-check installation path after install
    if exist "%VSWHERE%" (
        for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
            set "VS_INSTALL_DIR=%%i"
        )
    )
    
    if "!VS_INSTALL_DIR!"=="" (
        echo [ERROR] Visual Studio installation failed or tools not found.
        goto :error
    )
)

:: Load the environment
set "VCVARS=!VS_INSTALL_DIR!\VC\Auxiliary\Build\vcvarsall.bat"
echo [*] Loading Visual Studio Environment for %VCVARS_ARG%...
call "%VCVARS%" %VCVARS_ARG% >nul

:: -----------------------------------------------------
:: Step 4: Setup vcpkg and Audio Dependencies
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

:: -----------------------------------------------------
:: Step 5: Clone Repositories
:: -----------------------------------------------------
echo.
echo [*] Checking Repositories...
set "REPO_DIR=%ROOT_DIR%\krkrz_dev"
set "WUV_DIR=%ROOT_DIR%\wuvorbis"
set "SAMPLE_DIR=%ROOT_DIR%\SamplePlugin"

if not exist "%REPO_DIR%" "!GIT_EXE!" clone --recursive https://github.com/wamsoft/krkrz_dev.git "%REPO_DIR%" || goto :error
if not exist "%WUV_DIR%" "!GIT_EXE!" clone https://github.com/krkrz/wuvorbis.git "%WUV_DIR%" || goto :error
if not exist "%SAMPLE_DIR%" "!GIT_EXE!" clone https://github.com/krkrz/SamplePlugin.git "%SAMPLE_DIR%" || goto :error

:: -----------------------------------------------------
:: Step 6: Download and Place Legacy Stubs
:: -----------------------------------------------------
echo.
echo [*] Downloading legacy stubs for plugin compatibility...
curl -fL "https://raw.githubusercontent.com/krkrz/krkrz_dev/master/src/plugins/win32/tp_stub.h" -o "tp_stub.h" || goto :error
curl -fL "https://raw.githubusercontent.com/krkrz/krkrz_dev/master/src/plugins/win32/tp_stub.cpp" -o "tp_stub.cpp" || goto :error

:: extrans expects stubs at ..\ so we put them in the SamplePlugin root
copy /y "tp_stub.*" "%SAMPLE_DIR%\" >nul

:: -----------------------------------------------------
:: Step 7: Patch Legacy MSBuild Projects
:: -----------------------------------------------------
echo.
echo [*] Patching legacy .vcxproj files for modern MSVC compatibility...
:: Replaces hardcoded EditAndContinue (/ZI) with ProgramDatabase (/Zi) and disables deprecated MinimalRebuild (/Gm)
powershell -Command "(Get-Content '%WUV_DIR%\wuvorbis.vcxproj') -replace 'EditAndContinue', 'ProgramDatabase' -replace '<MinimalRebuild>true</MinimalRebuild>', '<MinimalRebuild>false</MinimalRebuild>' | Set-Content '%WUV_DIR%\wuvorbis.vcxproj'"
powershell -Command "(Get-Content '%WUV_DIR%\wuvorbis64.vcxproj') -replace 'EditAndContinue', 'ProgramDatabase' -replace '<MinimalRebuild>true</MinimalRebuild>', '<MinimalRebuild>false</MinimalRebuild>' | Set-Content '%WUV_DIR%\wuvorbis64.vcxproj'"
powershell -Command "(Get-Content '%SAMPLE_DIR%\extrans\extrans.vcxproj') -replace 'EditAndContinue', 'ProgramDatabase' -replace '<MinimalRebuild>true</MinimalRebuild>', '<MinimalRebuild>false</MinimalRebuild>' | Set-Content '%SAMPLE_DIR%\extrans\extrans.vcxproj'"

:: -----------------------------------------------------
:: Step 8: Build krkrz_dev (CMake)
:: -----------------------------------------------------
echo.
echo [*] Building krkrz_dev (%CMAKE_PRESET% / %CONFIG%)...
pushd "%REPO_DIR%"
if exist "build" rmdir /s /q "build"

:: We explicitly pass NASM to ensure CMake ignores yasm and any broken NASM 2.15+ instances
cmake --preset %CMAKE_PRESET% -DCMAKE_ASM_NASM_COMPILER="!NASM_EXE!" || goto :error
cmake --build --preset %CMAKE_PRESET% --config %CONFIG% || goto :error
popd

:: -----------------------------------------------------
:: Step 9: Build wuvorbis (MSBuild)
:: -----------------------------------------------------
echo.
echo [*] Building wuvorbis (%MSBUILD_PLATFORM% / %CONFIG%)...
pushd "%WUV_DIR%"

set "TOOLSET=v%VCToolsVersion:~0,2%%VCToolsVersion:~3,1%"
set "SDK_VER=%WindowsSDKVersion:~0,-1%"

msbuild %WUV_PROJ% -m /p:Configuration=%CONFIG% /p:Platform=%MSBUILD_PLATFORM% /p:WindowsTargetPlatformVersion=%SDK_VER% /p:PlatformToolset=%TOOLSET% /p:OutDir="%WUV_DIR%\%MSBUILD_PLATFORM%\%CONFIG%\\" || goto :error
popd

:: -----------------------------------------------------
:: Step 10: Build extrans (MSBuild)
:: -----------------------------------------------------
echo.
echo [*] Building extrans (%MSBUILD_PLATFORM% / %CONFIG%)...
pushd "%SAMPLE_DIR%\extrans"

msbuild extrans.vcxproj -m /p:Configuration=%CONFIG% /p:Platform=%MSBUILD_PLATFORM% /p:WindowsTargetPlatformVersion=%SDK_VER% /p:PlatformToolset=%TOOLSET% /p:OutDir="bin\%MSBUILD_PLATFORM%\%CONFIG%\\" || goto :error
popd

:: -----------------------------------------------------
:: Step 11: Move Files to Output
:: -----------------------------------------------------
echo.
echo [*] Moving required artifacts to final folder...
if not exist "plugin" mkdir "plugin"

set "BLD=krkrz_dev\build\%CMAKE_PRESET%"

:: Engine 
if "%ARCH%"=="x64" (
    move /y "!BLD!\core\%CONFIG%\krkrz64.exe" "krkrz.exe" >nul 2>&1
    move /y "!BLD!\core\%CONFIG%\krkrz64d.exe" "krkrz.exe" >nul 2>&1
) else (
    move /y "!BLD!\core\%CONFIG%\krkrz.exe" "krkrz.exe" >nul 2>&1
    move /y "!BLD!\core\%CONFIG%\krkrzd.exe" "krkrz.exe" >nul 2>&1
)

:: Explicit Standard Plugins
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

:: Custom Built Plugins
move /y "wuvorbis\%MSBUILD_PLATFORM%\%CONFIG%\wuvorbis.dll" "plugin\" >nul
move /y "SamplePlugin\extrans\bin\%MSBUILD_PLATFORM%\%CONFIG%\extrans.dll" "plugin\" >nul

:: -----------------------------------------------------
:: Step 12: Cleanup
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