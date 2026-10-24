# Included at the end of a platform kit's CMakeLists.txt (in the CI checkout) on Android and
# the web, where krkreffekseer is built into the engine. krkrz_dev stays as it is.
#
# - Effekseer's GL extension loader (EffekseerRendererGL.GLExtension.cpp) includes <EGL/egl.h>
#   on Android and Emscripten, and krkreffekseer's GLES hook renames eglGetProcAddress to its
#   own resolver with a macro, so egl.h's declaration clashed with it ("conflicting types for
#   'TVPEffekseerGLGetProcAddressGeneric'"). The file uses no other EGL symbol, so the header's
#   include guard is defined for that target and the header is skipped.
# - krkreffekseer's src/utils.cpp defines TVPUtf8ToUtf16 and TVPUtf16ToUtf8 for the plugin DLL,
#   which the engine itself defines (CharacterSet.cpp): linked into the engine, they were
#   duplicate symbols. The plugin is built without that file and uses the engine's.
if(TARGET efk_renderer_gl)
  target_compile_definitions(efk_renderer_gl PRIVATE __egl_h_=1)
  message(STATUS "kagex: <EGL/egl.h> skipped in efk_renderer_gl")
endif()
if(TARGET krkreffekseer)
  get_target_property(_kagex_efk_type krkreffekseer TYPE)
  get_target_property(_kagex_efk_dir krkreffekseer SOURCE_DIR)
  if(_kagex_efk_type STREQUAL "STATIC_LIBRARY")
    set_source_files_properties("${_kagex_efk_dir}/src/utils.cpp" TARGET_DIRECTORY krkreffekseer
                                PROPERTIES HEADER_FILE_ONLY ON)
    message(STATUS "kagex: krkreffekseer uses the engine's TVPUtf8ToUtf16/TVPUtf16ToUtf8")
  endif()
endif()
