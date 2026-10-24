// WebGL 2 has no unsynchronized buffer mapping, and Emscripten's glMapBufferRange returns 0 for
// GL_MAP_UNSYNCHRONIZED_BIT (it also wants an INVALIDATE bit). Effekseer's GLES 3 renderer maps
// its vertex buffers with WRITE | UNSYNCHRONIZED and memcpy'd into the null result, so nothing
// drew and the engine's memory got overwritten. krkreffekseer-kit.cmake renames the renderer's
// glad_glMapBufferRange to this pointer (efk_renderer_gl only) on the web, so its maps ask for
// WRITE | INVALIDATE_RANGE instead: Effekseer writes the whole range it maps.
#include <glad/gles2.h>

extern "C" {

static void* GLAD_API_PTR kagexMapBufferRange(GLenum target, GLintptr offset, GLsizeiptr length, GLbitfield access)
{
	if (access & GL_MAP_UNSYNCHRONIZED_BIT)
		access = (access & ~GL_MAP_UNSYNCHRONIZED_BIT) | GL_MAP_INVALIDATE_RANGE_BIT;
	return glad_glMapBufferRange(target, offset, length, access);
}

PFNGLMAPBUFFERRANGEPROC kagex_efk_glMapBufferRange = kagexMapBufferRange;

}
