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
# The output is build/<preset>/Release/kagex-release(.exe), one file with the screen embedded.
# KRKRZ_TOOLS_DIR is krkrz_tools; by default the one in ../krkrz_dev next to this repository.
#---------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.21)

project(kagex_release VERSION 0.7.0 LANGUAGES C CXX)

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

add_executable(kagex-release
    src/main.cpp
    src/Settings.cpp
    src/Project.cpp
    src/Host.cpp
    src/Subprocess.cpp
    src/Plan.cpp
    src/Archive.cpp
    src/Icons.cpp
    src/Engine.cpp
    src/Build.cpp
    src/Media.cpp
)
find_package(ZLIB REQUIRED)
# dr_flac (FLAC sources; header only)
find_path(DRLIBS_INCLUDE_DIRS "dr_flac.h" REQUIRED)
target_include_directories(kagex-release PRIVATE src ${DRLIBS_INCLUDE_DIRS})
target_link_libraries(kagex-release PRIVATE krt_app krt_xp3 krt_audio krt_image krt_loop ZLIB::ZLIB)
target_compile_definitions(kagex-release PRIVATE KAGEX_RELEASE_VERSION="${PROJECT_VERSION}")
if(WIN32)
    # the exe's icon and version info (Windows resource APIs)
    target_link_libraries(kagex-release PRIVATE krt_release)
    target_compile_definitions(kagex-release PRIVATE KR_HAVE_RELEASE_LIB)
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
target_include_directories(kagex-release PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")

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
