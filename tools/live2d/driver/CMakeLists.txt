# The Live2D driver (wtnbgo/live2d) for krkrlive2d, on every platform kagex builds for.
#
# krkrlive2d's CMake adds its driver from LIVE2DLIB_FOLDER when that's set: tools/live2d/build.py
# sets it to this folder, with LIVE2D_DRIVER_SOURCE the driver's checkout (the Android and iOS
# kits get both from the environment). The driver's own CMakeLists.txt builds for Windows, Android
# and iOS only (UPSTREAM.md), and its iOS build looks for the Core's libraries where Cubism 5 R5
# no longer puts them, so on Windows it's the driver's own and elsewhere this builds the same
# library: the Cubism Core's static library from the SDK's Core folder (CUBISM_SDK_CORE), the
# Cubism Native Framework's OpenGL ES 2 renderer (through GLAD on Linux and macOS, the engine
# handing it the GL functions, GLCompositor.GLGetProcAddress, as on Windows; the system's
# GLES 2 on Android and iOS, as the driver's own build does), minizip-ng and KTX (read only).
# On Android and iOS the plugin is linked into the engine with every other plugin, so the driver
# uses the minizip-ng the engine's plugins use (vcpkg's) where there is one: two copies of it in
# one binary would clash.
cmake_minimum_required(VERSION 3.16)

# A project of its own. krkrlive2d adds this folder, then calls tp_stub's krkrz_plugin(), which
# names its own folder's project after the plugin; this folder had taken its project's name from
# the engine's above it (krkrz), so its names going up read krkrz, krkrlive2d, krkrz, and CMake's
# Xcode generator put its targets, and KTX's, into the krkrz project twice: "duplicate object ids
# not allowed" in the iOS kit (UPSTREAM.md)
project(live2ddriver LANGUAGES C CXX)

# the driver's checkout and the SDK's Core folder, from the environment the first time and kept
# in the cache, so a reconfigure (from cmake --build) finds them
set(LIVE2D_DRIVER_SOURCE "$ENV{LIVE2D_DRIVER_SOURCE}" CACHE PATH "the wtnbgo/live2d checkout")
set(CUBISM_SDK_CORE "$ENV{CUBISM_SDK_CORE}" CACHE PATH "the Cubism SDK for Native's Core folder")
if ("$ENV{CUBISM_SDK_CORE}" STREQUAL "" AND NOT CUBISM_SDK_CORE STREQUAL "")
  # the driver's own CMake (Windows, Android, iOS) reads it from the environment
  set(ENV{CUBISM_SDK_CORE} "${CUBISM_SDK_CORE}")
endif()
if (NOT EXISTS "${LIVE2D_DRIVER_SOURCE}/src/ilive2d.h")
  message(FATAL_ERROR "LIVE2D_DRIVER_SOURCE (${LIVE2D_DRIVER_SOURCE}) isn't a checkout of wtnbgo/live2d")
endif()

if (WIN32)
  add_subdirectory(${LIVE2D_DRIVER_SOURCE} ${CMAKE_CURRENT_BINARY_DIR}/upstream)
  return()
endif()

set(L2D ${LIVE2D_DRIVER_SOURCE})

# The Cubism Core: the SDK's Core folder, whose CHANGELOG.md names its version (the driver's
# own check: 06.00.0001 is the one it was made for)
if (CUBISM_SDK_CORE STREQUAL "")
  message(FATAL_ERROR "CUBISM_SDK_CORE (the Cubism SDK for Native's Core folder) isn't set")
endif()
file(TO_CMAKE_PATH "${CUBISM_SDK_CORE}" CORE_PATH)
if (NOT EXISTS ${CORE_PATH}/include/Live2DCubismCore.h)
  message(FATAL_ERROR "CUBISM_SDK_CORE=${CORE_PATH} has no include/Live2DCubismCore.h (it's the SDK's Core folder)")
endif()
file(STRINGS ${CORE_PATH}/CHANGELOG.md _core_version_lines REGEX "Upgrade Core version to [0-9]+\\.[0-9]+\\.[0-9]+")
list(GET _core_version_lines 0 _core_version_line)
string(REGEX MATCH "[0-9]+\\.[0-9]+\\.[0-9]+" CUBISM_CORE_VERSION "${_core_version_line}")
if (CUBISM_CORE_VERSION VERSION_LESS 06.00.0001)
  message(FATAL_ERROR "Cubism Core ${CUBISM_CORE_VERSION} is too old for the driver (06.00.0001 or newer)")
endif()
message(STATUS "live2d driver (kagex's build for ${CMAKE_SYSTEM_NAME}): Cubism Core ${CUBISM_CORE_VERSION}")

if (IOS)
  # the device's, or the Simulator's for the architecture (the kits configure a build for each;
  # the triplet names the Simulator, arm64-ios-simulator-krkrz)
  if (VCPKG_TARGET_TRIPLET MATCHES "simulator" OR CMAKE_OSX_SYSROOT MATCHES "[Ss]imulator")
    if (VCPKG_TARGET_TRIPLET MATCHES "^x64" OR CMAKE_OSX_ARCHITECTURES MATCHES "x86_64")
      set(CORE_LIB ${CORE_PATH}/lib/ios/Release-iphonesimulator-x86_64/libLive2DCubismCore.a)
    else()
      set(CORE_LIB ${CORE_PATH}/lib/ios/Release-iphonesimulator-arm64/libLive2DCubismCore.a)
    endif()
  else()
    set(CORE_LIB ${CORE_PATH}/lib/ios/Release-iphoneos/libLive2DCubismCore.a)
  endif()
elseif (ANDROID)
  set(CORE_LIB ${CORE_PATH}/lib/android/${ANDROID_ABI}/libLive2DCubismCore.a)
elseif (APPLE)
  if (CMAKE_OSX_ARCHITECTURES MATCHES "x86_64" OR (NOT CMAKE_OSX_ARCHITECTURES AND CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64"))
    set(CORE_LIB ${CORE_PATH}/lib/macos/x86_64/libLive2DCubismCore.a)
  else()
    set(CORE_LIB ${CORE_PATH}/lib/macos/arm64/libLive2DCubismCore.a)
  endif()
elseif (CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64|arm64")
  set(CORE_LIB ${CORE_PATH}/lib/experimental/linux/arm64/libLive2DCubismCore.a)
else()
  set(CORE_LIB ${CORE_PATH}/lib/linux/x86_64/libLive2DCubismCore.a)
endif()
if (NOT EXISTS ${CORE_LIB})
  message(FATAL_ERROR "the Cubism Core has no library for this platform: ${CORE_LIB}")
endif()

# a plugin is a shared library, and these go into it
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "Create shared libraries (static otherwise)." FORCE)

# minizip-ng: the engine's (vcpkg's) on Android and iOS when the kit has it, else as the driver
# fetches it: decompression only, with zlib-ng's objects built in
if (ANDROID OR IOS)
  find_package(minizip-ng CONFIG QUIET)
endif()
if (TARGET MINIZIP::minizip-ng)
  message(STATUS "live2d driver: the engine's minizip-ng")
else()
include(FetchContent)
set(SKIP_INSTALL_ALL ON)
set(ZLIB_TAG "2.2.4")
foreach(_opt MZ_COMPAT MZ_BZIP2 MZ_LZMA MZ_ZSTD MZ_LIBCOMP MZ_OPENSSL MZ_LIBBSD MZ_PKCRYPT MZ_WZAES
        MZ_ICONV MZ_BUILD_TESTS MZ_BUILD_UNIT_TESTS ZLIB_ENABLE_TESTS WITH_GTEST)
  set(${_opt} OFF CACHE BOOL "" FORCE)
endforeach()
foreach(_opt MZ_DECOMPRESS_ONLY MZ_ZLIB MZ_FETCH_LIBS MZ_FORCE_FETCH_LIBS)
  set(${_opt} ON CACHE BOOL "" FORCE)
endforeach()
FetchContent_Declare(minizip-ng
  GIT_REPOSITORY https://github.com/zlib-ng/minizip-ng.git
  GIT_TAG 4.1.0
)
FetchContent_MakeAvailable(minizip-ng)
foreach(ZLIB_NG_TARGET zlibstatic zlib)
  if (TARGET ${ZLIB_NG_TARGET})
    target_sources(minizip-ng PRIVATE $<TARGET_OBJECTS:${ZLIB_NG_TARGET}>)
    set_target_properties(minizip-ng PROPERTIES INTERFACE_LINK_LIBRARIES "")
    break()
  endif()
endforeach()
endif()

add_library(Live2DCubismCore STATIC IMPORTED)
set_target_properties(Live2DCubismCore PROPERTIES
  IMPORTED_LOCATION ${CORE_LIB}
  INTERFACE_INCLUDE_DIRECTORIES ${CORE_PATH}/include)

# the Cubism Native Framework (the driver's fork) with its OpenGL ES 2 renderer
set(FRAMEWORK_SOURCE OpenGL)
add_subdirectory(${L2D}/external/CubismNativeFramework ${CMAKE_CURRENT_BINARY_DIR}/Framework)
if (ANDROID)
  target_compile_definitions(Framework PUBLIC CSM_TARGET_ANDROID_ES2)
  target_link_libraries(Framework PUBLIC Live2DCubismCore GLESv2 log)
elseif (IOS)
  find_library(OPENGLES_LIBRARY OpenGLES REQUIRED)
  target_compile_definitions(Framework PUBLIC CSM_TARGET_IPHONE_ES2)
  target_link_libraries(Framework PUBLIC Live2DCubismCore ${OPENGLES_LIBRARY})
else()
  # GLAD's OpenGL ES 2 loader (the driver's copy; its CMakelists.txt is named so that only a
  # file system that ignores case finds it), with the EGL loader its own loader refers to.
  # EGL_NO_X11: the driver loads GLES through the engine's GLGetProcAddress and never touches
  # X11, whose headers eglplatform.h would want on Linux (CI's runners have none)
  if (NOT TARGET glad)
    add_library(glad STATIC ${L2D}/external/glad/src/egl.c ${L2D}/external/glad/src/gles2.c)
    target_compile_definitions(glad PUBLIC EGL_NO_X11)
    target_include_directories(glad PUBLIC ${L2D}/external/glad/include)
  endif()
  target_compile_definitions(Framework PUBLIC CSM_TARGET_GLAD_ES2)
  target_link_libraries(Framework PUBLIC Live2DCubismCore glad)
endif()

# KTX textures, read only
if (NOT TARGET ktx_read)
  set(KTX_FEATURE_TESTS OFF CACHE BOOL "" FORCE)
  set(KTX_FEATURE_TOOLS OFF CACHE BOOL "" FORCE)
  set(LIBKTX_VERSION_READ_ONLY ON CACHE BOOL "" FORCE)
  set(LIBKTX_VERSION_FULL OFF CACHE BOOL "" FORCE)
  set(KTX_INSTALL OFF CACHE BOOL "" FORCE)
  add_subdirectory(${L2D}/external/KTX-Software ${CMAKE_CURRENT_BINARY_DIR}/KTX-Software)
endif()

add_library(live2ddriver STATIC
  ${L2D}/src/MyCubismPose.cpp
  ${L2D}/src/MyCubismModel.cpp
  ${L2D}/src/LAppModel.cpp
  ${L2D}/src/plive2d.cpp
  ${L2D}/src/zipinfo.cpp
  ${L2D}/src/LAppAllocator.cpp
  ${L2D}/src/ogl/LAppModelOGL.cpp
)
target_include_directories(live2ddriver
  PUBLIC ${L2D}/src
  PRIVATE ${L2D}/src/ogl ${L2D}/external/CubismNativeSamples/Samples/OpenGL/thirdParty/stb)
target_compile_definitions(live2ddriver PUBLIC LIVE2DDRIVER_STATIC_LIBRARY)
if (ANDROID OR IOS)
  # the driver's own builds: a static library, .ktx in place of a missing .png texture
  if (IOS)
    target_compile_definitions(live2ddriver PUBLIC __IOS__)
  endif()
else()
  target_sources(live2ddriver PRIVATE ${L2D}/src/ogl/glad.cpp)
  target_compile_definitions(live2ddriver PUBLIC USE_GLAD)
endif()
target_link_libraries(live2ddriver PUBLIC Framework ktx_read MINIZIP::minizip-ng)

# the plugin shows V2Link and V2Unlink only, not the thousands of GLAD, minizip, zlib-ng, KTX
# and Cubism functions that come in with these libraries
if (CMAKE_SYSTEM_NAME STREQUAL "Linux")
  target_link_options(live2ddriver INTERFACE "LINKER:--exclude-libs,ALL")
endif()
