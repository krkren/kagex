# Included at the end of a platform kit's CMakeLists.txt (in the CI checkout) on Android and
# the web, where krkreffekseer is built into the engine. krkrz_dev stays as it is.
#
# - Effekseer's GL extension loader (EffekseerRendererGL.GLExtension.cpp) includes <EGL/egl.h>
#   on Android and Emscripten, and krkreffekseer's GLES hook renames eglGetProcAddress to its
#   own resolver with a macro, so egl.h's declaration clashed with it ("conflicting types for
#   'TVPEffekseerGLGetProcAddressGeneric'"). The file uses no other EGL symbol, so the header's
#   include guard is defined for that target and the header is skipped.
# - krkreffekseer's src/utils.cpp defines TVPUtf8ToUtf16 and TVPUtf16ToUtf8 for the plugin DLL,
#   which the engine itself defines too (CharacterSet.cpp): linked into the engine they were
#   duplicate symbols. The plugin's own copies are renamed for its sources.
# - krkreffekseer-odr.cpp defines static members Effekseer declares in its classes, which an
#   unoptimized build (the debug APK) needs.
# - Web: Effekseer maps its vertex buffers unsynchronized, which WebGL can't (Emscripten's
#   glMapBufferRange returned 0, so nothing drew): krkreffekseer-webgl.cpp maps them with
#   INVALIDATE_RANGE instead, through a renamed glad pointer in efk_renderer_gl.
if(TARGET efk_renderer_gl)
  target_compile_definitions(efk_renderer_gl PRIVATE __egl_h_=1)
  message(STATUS "kagex: <EGL/egl.h> skipped in efk_renderer_gl")
endif()
if(TARGET krkreffekseer)
  get_target_property(_kagex_efk_type krkreffekseer TYPE)
  if(_kagex_efk_type STREQUAL "STATIC_LIBRARY")
    target_compile_definitions(krkreffekseer PRIVATE
      TVPUtf8ToUtf16=kagex_efk_TVPUtf8ToUtf16 TVPUtf16ToUtf8=kagex_efk_TVPUtf16ToUtf8)
    message(STATUS "kagex: krkreffekseer's own TVPUtf8ToUtf16/TVPUtf16ToUtf8 renamed")
  endif()
endif()
if(TARGET efk_core)
  target_sources(efk_core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/krkreffekseer-odr.cpp")
  message(STATUS "kagex: Effekseer's static const members defined for unoptimized builds")
endif()
if(EMSCRIPTEN AND TARGET efk_renderer_gl AND TARGET krkreffekseer)
  target_compile_definitions(efk_renderer_gl PRIVATE glad_glMapBufferRange=kagex_efk_glMapBufferRange)
  target_sources(krkreffekseer PRIVATE "${CMAKE_CURRENT_LIST_DIR}/krkreffekseer-webgl.cpp")
  message(STATUS "kagex: Effekseer's buffer maps go through krkreffekseer-webgl.cpp")
endif()
