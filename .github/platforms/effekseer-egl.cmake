# Included at the end of a platform kit's CMakeLists.txt (in the CI checkout) on Android and
# the web. Effekseer's GL extension loader (EffekseerRendererGL.GLExtension.cpp) includes
# <EGL/egl.h> on Android and Emscripten, and krkreffekseer's GLES hook renames eglGetProcAddress
# to its own resolver with a macro, so egl.h's declaration clashed with it ("conflicting types
# for 'TVPEffekseerGLGetProcAddressGeneric'"). The file uses no other EGL symbol, so its include
# guard is defined for that target and the header is skipped. krkrz_dev stays as it is.
if(TARGET efk_renderer_gl)
  target_compile_definitions(efk_renderer_gl PRIVATE __egl_h_=1)
  message(STATUS "kagex: <EGL/egl.h> skipped in efk_renderer_gl")
endif()
