# Included at the end of a platform kit's CMakeLists.txt (in the CI checkout) on the web, Android
# and iOS, where every plugin is built into the engine: what krkrthreepp (3D) needs there.
#
# - Static plugins are linked whole (--whole-archive / -force_load), and krkrthreepp's main.cpp
#   and layerExVector's both define a global IsArray(const tTJSVariant &): a duplicate symbol
#   (the iOS link stopped at it). krkrthreepp's is renamed for its own sources.
# - threepp links pthread and dl on every UNIX, and Android has no libpthread (its libc has the
#   functions): ld.lld stopped at -lpthread. They're taken off threepp's link there.
# - With Emscripten threepp draws with the browser's GLES 3 directly and leaves its glad out, but
#   its generic canvas includes glad/glad.h all the same, and krkrthreepp calls threepp::initGlad
#   (utils/LoadGlad.cpp, also left out): the glad folder goes on threepp's include path and
#   LoadGlad.cpp into its sources, with the GLES guards the other platforms build it with. The
#   glad functions themselves are the engine's (it has its own glad, as on Android and iOS,
#   where threepp's archive is linked as needed and its gles2.c isn't pulled in).
if(TARGET krkrthreepp)
  get_target_property(_kagex_3d_type krkrthreepp TYPE)
  if(_kagex_3d_type STREQUAL "STATIC_LIBRARY")
    target_compile_definitions(krkrthreepp PRIVATE IsArray=krkrthreepp_IsArray)
    message(STATUS "kagex: krkrthreepp's IsArray renamed (static plugins are linked whole)")
  endif()
endif()
if(TARGET threepp)
  if(ANDROID)
    foreach(_kagex_prop LINK_LIBRARIES INTERFACE_LINK_LIBRARIES)
      get_target_property(_kagex_libs threepp ${_kagex_prop})
      if(_kagex_libs)
        list(REMOVE_ITEM _kagex_libs pthread "$<LINK_ONLY:pthread>")
        set_target_properties(threepp PROPERTIES ${_kagex_prop} "${_kagex_libs}")
      endif()
    endforeach()
    message(STATUS "kagex: threepp links no libpthread on Android")
  endif()
  if(EMSCRIPTEN)
    get_target_property(_kagex_threepp_src threepp SOURCE_DIR)
    target_include_directories(threepp PRIVATE "${_kagex_threepp_src}/external/glad")
    target_sources(threepp PRIVATE "${_kagex_threepp_src}/threepp/utils/LoadGlad.cpp")
    set_source_files_properties(
      "${_kagex_threepp_src}/threepp/utils/LoadGlad.cpp"
      "${_kagex_threepp_src}/threepp/canvas/Canvas_generic.cpp"
      TARGET_DIRECTORY threepp
      PROPERTIES COMPILE_DEFINITIONS "GLAD_NO_STANDALONE_LOADER;THREEPP_GLES")
    message(STATUS "kagex: threepp's glad shim and loader on the web")
  endif()
endif()
