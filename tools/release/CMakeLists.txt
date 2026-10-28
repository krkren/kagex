#---------------------------------------------------------------------------
# kagex-release: packages a KAGEX game for each platform
#
# A native app whose screen is a browser window (appserve, as in the engine's own tools), and a
# command-line tool (--cli). It reuses krkrz_tools' libraries (xp3, audio, images, .sli) from
# krkrz_dev's submodule, without changing them.
#
#   cmake --preset linux            (windows: from a Developer Command Prompt; macos: Apple Silicon)
#   cmake --build --preset linux-rel
#
# The output is build/<preset>/Release/kagex-release(.exe), one file with the screen embedded, and
# beside it kagex-lipsync(.exe) with its lipsync/ folder (../lipsync; -DKAGEX_LIPSYNC=OFF leaves it out).
# KRKRZ_TOOLS_DIR is krkrz_tools; by default the one in ../krkrz_dev next to this repository.
#---------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.21)

project(kagex_release VERSION 0.12.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# one exe without runtime DLLs (the vcpkg triplet is x64-windows-static to match)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
if(MSVC)
    add_compile_options(/utf-8 /W3)
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS NOMINMAX WIN32_LEAN_AND_MEAN)
endif()

get_filename_component(_kagex_root "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
if(DEFINED ENV{KRKRZ_BASE})
    set(_tools_default "$ENV{KRKRZ_BASE}/krkrz_dev/src/tools/krkrz_tools")
else()
    get_filename_component(_tools_default "${_kagex_root}/../krkrz_dev/src/tools/krkrz_tools" ABSOLUTE)
endif()
set(KRKRZ_TOOLS_DIR "${_tools_default}" CACHE PATH "krkrz_tools (krkrz_dev/src/tools/krkrz_tools, with its submodules)")
if(NOT EXISTS "${KRKRZ_TOOLS_DIR}/CMakeLists.txt" OR NOT EXISTS "${KRKRZ_TOOLS_DIR}/external/appserve/CMakeLists.txt")
    message(FATAL_ERROR "krkrz_tools not found at ${KRKRZ_TOOLS_DIR} (set KRKRZ_TOOLS_DIR, or KRKRZ_BASE to the folder "
                        "that holds krkrz_dev, and run git submodule update --init --recursive there)")
endif()

# krkrz_tools' libraries; its own tools are only built when asked for
add_subdirectory("${KRKRZ_TOOLS_DIR}" krkrz_tools EXCLUDE_FROM_ALL)

# xp3crypt's library (encrypted data.xp3), from the repo next to kagex. Optional: without it the
# tool builds but can't encrypt (KR_HAVE_XP3CRYPT off)
if(DEFINED ENV{KRKRZ_BASE})
    set(_xp3crypt_default "$ENV{KRKRZ_BASE}/xp3crypt")
else()
    get_filename_component(_xp3crypt_default "${_kagex_root}/../xp3crypt" ABSOLUTE)
endif()
set(XP3CRYPT_DIR "${_xp3crypt_default}" CACHE PATH "The xp3crypt repository (for encrypted archives)")
set(_have_xp3crypt OFF)
if(EXISTS "${XP3CRYPT_DIR}/lib/CMakeLists.txt")
    add_subdirectory("${XP3CRYPT_DIR}/lib" xp3crypt EXCLUDE_FROM_ALL)
    set(_have_xp3crypt ON)
    message(STATUS "xp3crypt: ${XP3CRYPT_DIR} (archive encryption on)")
else()
    message(STATUS "xp3crypt not found at ${XP3CRYPT_DIR}: archive encryption off (set XP3CRYPT_DIR)")
endif()

# Everything but the command line and the window, which kagex-lipsync (../lipsync) uses too
add_library(kagex_release_core STATIC
    src/Settings.cpp
    src/Project.cpp
    src/Host.cpp
    src/Subprocess.cpp
    src/Plan.cpp
    src/Archive.cpp
    src/Icons.cpp
    src/Engine.cpp
    src/Build.cpp
    src/Encrypt.cpp
    src/Media.cpp
    src/Layered.cpp
    src/Keys.cpp
    src/Sign.cpp
    src/Scripts.cpp
    src/Scenes.cpp
    src/LipTracks.cpp
)
add_executable(kagex-release src/main.cpp)
target_link_libraries(kagex-release PRIVATE kagex_release_core)
find_package(ZLIB REQUIRED)
# dr_flac (FLAC sources; header only)
find_path(DRLIBS_INCLUDE_DIRS "dr_flac.h" REQUIRED)
# libtomcrypt / libtommath provide no CMake config (as in krkrz_dev's sigcheck / krt_sig), so find
# them by hand; used by src/Sign.cpp to derive a public key from a private key.
find_path(LIBTOMCRYPT_INCLUDE_DIR tomcrypt.h REQUIRED)
find_library(LIBTOMCRYPT_LIBRARY tomcrypt REQUIRED)
find_library(LIBTOMMATH_LIBRARY tommath REQUIRED)
target_include_directories(kagex_release_core PUBLIC src ${DRLIBS_INCLUDE_DIRS} ${LIBTOMCRYPT_INCLUDE_DIR})
target_compile_definitions(kagex_release_core PUBLIC LTM_DESC)
# psdparse and clipparse (krkrz_tools' submodules, the libraries the psdfile and clipfile plugins
# wrap): splitting .psd and .clip files into layer pictures (src/Layered.cpp)
target_link_libraries(kagex_release_core PUBLIC krt_app krt_xp3 krt_audio krt_image krt_loop krt_sig
    psdparse clipparse ${LIBTOMCRYPT_LIBRARY} ${LIBTOMMATH_LIBRARY} ZLIB::ZLIB)
if(_have_xp3crypt)
    target_link_libraries(kagex_release_core PUBLIC xp3crypt_lib)
    target_compile_definitions(kagex_release_core PUBLIC KR_HAVE_XP3CRYPT)
endif()
target_compile_definitions(kagex_release_core PUBLIC KAGEX_RELEASE_VERSION="${PROJECT_VERSION}")
if(WIN32)
    # the exe's icon and version info (Windows resource APIs)
    target_link_libraries(kagex_release_core PUBLIC krt_release)
    target_compile_definitions(kagex_release_core PUBLIC KR_HAVE_RELEASE_LIB)
endif()
# Encrypting compiled scenarios and writing the game's key into the scnfile plugin: scnfile's own
# code (https://github.com/krkren/scnfile, plugins/scnfile), by default from ../scnfile next to
# this repository. Without it the tool still compiles scenarios, but can't encrypt them
get_filename_component(_scnfile_default "${_kagex_root}/../scnfile" ABSOLUTE)
set(SCNFILE_DIR "${_scnfile_default}" CACHE PATH "scnfile (for encrypting compiled scenarios; optional)")
if(EXISTS "${SCNFILE_DIR}/plugins/scnfile/seal.cpp")
    set(_scn "${SCNFILE_DIR}/plugins/scnfile")
    target_sources(kagex_release_core PRIVATE "${_scn}/seal.cpp" "${_scn}/seal_random.cpp" "${_scn}/psb.cpp")
    # one Monocypher in the tool: xp3crypt_core has its own copy (the same 4.x API), and two
    # copies' symbols clash at link time
    if(NOT _have_xp3crypt)
        target_sources(kagex_release_core PRIVATE "${_scn}/monocypher/monocypher.c")
    endif()
    target_include_directories(kagex_release_core PUBLIC "${_scn}")
    target_compile_definitions(kagex_release_core PUBLIC KR_HAVE_SCNFILE SCNFILE_HAVE_ZLIB)
    if(WIN32)
        target_link_libraries(kagex_release_core PUBLIC bcrypt)
    endif()
    message(STATUS "kagex-release: encrypting scenarios with scnfile from ${SCNFILE_DIR}")
else()
    message(STATUS "kagex-release: no scnfile at ${SCNFILE_DIR}: compiled scenarios can't be encrypted")
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    # runs on any distribution with the glibc it was built against or newer
    target_link_options(kagex-release PRIVATE -static-libstdc++ -static-libgcc)
endif()

# The web build's page script (platform/web/kagex-web.js: updates and Add to Home Screen),
# written into each web build, so it doesn't depend on the engine package having it
set(_webjs "${_kagex_root}/platform/web/kagex-web.js")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_webjs}")
file(READ "${_webjs}" _webjs_hex HEX)
string(REGEX REPLACE "([0-9a-f][0-9a-f])" "0x\\1," _webjs_bytes "${_webjs_hex}")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/KagexWebJs.h.tmp"
    "// generated from platform/web/kagex-web.js by CMakeLists.txt\n#pragma once\n"
    "static const unsigned char kKagexWebJs[] = { ${_webjs_bytes} };\n")
# copied only when it changed, so a configure doesn't rebuild Build.cpp for nothing
configure_file("${CMAKE_CURRENT_BINARY_DIR}/KagexWebJs.h.tmp" "${CMAKE_CURRENT_BINARY_DIR}/generated/KagexWebJs.h" COPYONLY)
target_include_directories(kagex_release_core PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")

# The screen: appserve's client library and web/, zipped into the exe
set(_stage "${CMAKE_CURRENT_BINARY_DIR}/web")
file(REMOVE_RECURSE "${_stage}")
file(GLOB_RECURSE _web RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}/web" CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/web/*")
foreach(_f IN LISTS _web)
    configure_file("${CMAKE_CURRENT_SOURCE_DIR}/web/${_f}" "${_stage}/${_f}" COPYONLY)
endforeach()
set(_lib "${KRKRZ_TOOLS_DIR}/external/appserve/web/lib")
file(GLOB_RECURSE _libfiles RELATIVE "${_lib}" CONFIGURE_DEPENDS "${_lib}/*")
foreach(_f IN LISTS _libfiles)
    configure_file("${_lib}/${_f}" "${_stage}/lib/${_f}" COPYONLY)
endforeach()
appserve_embed_web(kagex-release WEB_DIR "${_stage}" NAME kagex_release_web)

# kagex-lipsync, beside kagex-release: the mouths' vowels for the voices a game picks
option(KAGEX_LIPSYNC "Build kagex-lipsync (../lipsync) too" ON)
if(KAGEX_LIPSYNC)
    add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../lipsync" lipsync-build)
endif()
