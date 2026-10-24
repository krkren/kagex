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

project(kagex_release VERSION 0.3.0 LANGUAGES C CXX)

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
    src/Process.cpp
    src/Plan.cpp
)
target_include_directories(kagex-release PRIVATE src)
target_link_libraries(kagex-release PRIVATE krt_app krt_xp3 krt_audio krt_image krt_loop)
target_compile_definitions(kagex-release PRIVATE KAGEX_RELEASE_VERSION="${PROJECT_VERSION}")
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    # runs on any distribution with the glibc it was built against or newer
    target_link_options(kagex-release PRIVATE -static-libstdc++ -static-libgcc)
endif()

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
