# krkrlive2d on the web: the driver's CMake reads these as CMake variables, while the web build
# configures with them in the environment. web-plugins.py includes this at the top of the shared
# binary's CMakeLists.txt so that the plugin, added below, sees them. The Core is the one
# from tools/live2d (kagex's web/csm_web.cpp over the live2dcubismcore.js the page loads);
# the environment is the place build.py and CI point at it.
if(DEFINED ENV{CUBISM_SDK_CORE})
  set(CUBISM_SDK_CORE "$ENV{CUBISM_SDK_CORE}")
  message(STATUS "krkrlive2d: the Cubism Core's headers from $ENV{CUBISM_SDK_CORE}, the Core itself in live2dcubismcore.js")
  include_directories("$ENV{CUBISM_SDK_CORE}/include")
endif()
if(DEFINED ENV{LIVE2DLIB_FOLDER})
  set(LIVE2DLIB_FOLDER "$ENV{LIVE2DLIB_FOLDER}")
endif()
if(DEFINED ENV{LIVE2D_DRIVER_SOURCE})
  set(LIVE2D_DRIVER_SOURCE "$ENV{LIVE2D_DRIVER_SOURCE}")
endif()
