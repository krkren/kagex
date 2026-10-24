# Given to krkrz_dev's macOS configure as CMAKE_PROJECT_INCLUDE (in CI; krkrz_dev stays as it
# is). Effekseer's GLES 3 renderer on Apple maps its vertex buffers through glMapBufferRange only
# where GL_ARB_map_buffer_range is defined, and returns null otherwise; with krkreffekseer's
# GLES headers it isn't, so the first effect drawn wrote through a null pointer and the engine
# crashed (SIGSEGV). ANGLE's GLES 3 has glMapBufferRange: define the macro for efk_renderer_gl.
# CMAKE_PROJECT_INCLUDE runs after every project(); the change waits for the end of the top
# directory, when the plugins' targets exist.
get_property(_kagex_efk_apple GLOBAL PROPERTY KAGEX_EFK_APPLE)
if(NOT _kagex_efk_apple)
  set_property(GLOBAL PROPERTY KAGEX_EFK_APPLE TRUE)
  function(kagex_efk_apple)
    if(TARGET efk_renderer_gl)
      target_compile_definitions(efk_renderer_gl PRIVATE GL_ARB_map_buffer_range=1)
      message(STATUS "kagex: Effekseer maps its buffers with glMapBufferRange on Apple")
    else()
      message(WARNING "kagex: no efk_renderer_gl target (krkreffekseer isn't built)")
    endif()
  endfunction()
  cmake_language(DEFER DIRECTORY "${CMAKE_SOURCE_DIR}" CALL kagex_efk_apple)
endif()
