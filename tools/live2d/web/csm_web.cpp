// The Cubism Core for the web.  The Core's wasm is closed source and its own
// link binary, so it can't go into the engine's: instead Live2D's own Web Core
// (live2dcubismcore.js, which the page loads before the engine) runs it, and
// this file gives the driver the very C API it already includes
// (Live2DCubismCore.h, 56 functions), implemented over the Core's JavaScript
// class API.  Everything above it — the driver, the Cubism Native Framework,
// krkrlive2d — stays exactly as on the other platforms.
//
// The native Core answers its getters with pointers into its own memory.  These
// return mirror buffers allocated here in the engine's memory instead, filled
// from the Core's typed arrays at csmUpdateModel and csmResetDrawableDynamicFlags
// — the times the native Core would have updated them — and csmGetParameterValues
// answers with a mirror the engine writes into, which is pushed into the Core
// before update().
//
// csmMoc* and csmModel* are opaque to everyone: each is the address the caller
// passed to csmReviveMocInPlace / csmInitializeModelInPlace, where a handle
// below is constructed.  The handles hold C++ (emscripten::val); csmGetSizeofModel
// gives the caller the size so its own buffer fits.
//
// One model at a time in flight would not do; many models are the driver's
// everyday case.  A handle per model, no global state.

#include <emscripten/emscripten.h>
#include <emscripten/val.h>

#include <cstring>
#include <cstdlib>
#include <new>
#include <string>

#include "Live2DCubismCore.h"

using emscripten::val;

// ---------- the marshalling layer ----------
// EM_JS with emscripten::val in its signature does NOT marshal: JS gets raw
// emval ids and C++ gets a number (verified: LEN=0 probe, emscripten 6.0.13).
// So nothing here uses EM_JS: everything crosses through the plain emval C++
// path, with typed_memory_view handing the Core real typed-array views over
// engine memory, and Uint8Array built via val for the byte copies.

namespace {

// a Uint8Array view over engine memory of engine-allocated bytes
val bytes_view(void* p, int bytes)
{
    return val(emscripten::typed_memory_view(bytes, static_cast<uint8_t*>(p)));
}

// copy one of the Core's typed arrays into engine memory: byte transport,
// so the array's element type does not matter
void pull_into(const val& ta, void* dst, int bytes)
{
    if (bytes <= 0) {
        return;
    }
    val src = val::global("Uint8Array").new_(ta["buffer"], ta["byteOffset"], ta["byteLength"]);
    bytes_view(dst, bytes).call<void>("set", src);
}

// the moc bytes as an ArrayBuffer that outlives the engine buffer it was
// read from: copied (slice), then handed its own buffer
val heap_to_ab_copy(const void* p, int bytes)
{
    val view = val(emscripten::typed_memory_view(bytes, static_cast<const uint8_t*>(p)));
    val copy = view.call<val>("slice");
    return copy["buffer"];
}

val l2dcore()
{
    static val core = val::global("Live2DCubismCore");
    return core;
}

val moc_class()
{
    static val c = l2dcore()["Moc"];
    return c;
}

val model_class()
{
    static val c = l2dcore()["Model"];
    return c;
}

char* dup_string(const std::string& s)
{
    char* out = static_cast<char*>(std::malloc(s.size() + 1));
    std::memcpy(out, s.c_str(), s.size() + 1);
    return out;
}

char** dup_strings(const val& ids)
{
    const int n = ids["length"].as<int>();
    char** out = static_cast<char**>(std::malloc(sizeof(char*) * (n > 0 ? n : 1)));
    for (int i = 0; i < n; ++i) {
        out[i] = dup_string(ids[i].as<std::string>());
    }
    return out;
}

void* pull_ta(const val& ta)
{
    const int bytes = ta["byteLength"].as<int>();
    void* p = std::malloc(bytes ? bytes : 1);
    pull_into(ta, p, bytes);
    return p;
}

template <typename T>
T* pull_ta_as(const val& ta)
{
    return static_cast<T*>(pull_ta(ta));
}

// an array of typed arrays (parameter key values, drawable masks, per-drawable
// vertices/uvs/indices): one engine buffer each, plus a pointer table
template <typename T>
T** pull_ta_array(const val& arrays)
{
    const int n = arrays["length"].as<int>();
    T** out = static_cast<T**>(std::malloc(sizeof(T*) * (n > 0 ? n : 1)));
    for (int i = 0; i < n; ++i) {
        out[i] = static_cast<T*>(pull_ta(arrays[i]));
    }
    return out;
}

// the refresh of one array-of-typed-arrays group at update time

struct WebMoc {
    val moc;
    val bytes;          // the ArrayBuffer, kept for version queries
    unsigned int version;
};

// every array the C getters answer with, in engine memory
struct Mirror {
    int pcount = 0;
    char** pids = nullptr;
    int* ptypes = nullptr;
    float *pmin = nullptr, *pmax = nullptr, *pdef = nullptr, *pvalues = nullptr;
    int* prepeats = nullptr;
    int* pkeyCounts = nullptr;
    float** pkeyValues = nullptr;

    int ocount = 0;
    char** oids = nullptr;
    float* opacities = nullptr;
    int* parent = nullptr, *offscreenIdx = nullptr;

    int dcount = 0;
    char** dids = nullptr;
    unsigned char *iconst = nullptr, *idyn = nullptr;
    int *blend = nullptr, *tex = nullptr, *drawOrder = nullptr;
    float *dopacity = nullptr;
    int *maskCounts = nullptr;
    int** masks = nullptr;
    int *vcounts = nullptr, *icounts = nullptr;
    float **verts = nullptr, **uvs = nullptr;
    unsigned short** indices = nullptr;
    float *mul = nullptr, *screen = nullptr;
    int* dparent = nullptr;

    int oocount = 0;
    int *ooBlend = nullptr, *ooOwner = nullptr, *ooMaskCounts = nullptr;
    float *ooOpacity = nullptr, *ooMul = nullptr, *ooScreen = nullptr;
    int** ooMasks = nullptr;
    unsigned char* ooConst = nullptr;

    int* renderOrders = nullptr;
};

struct WebModel {
    val model;
    Mirror m;

    void refresh_in()
    {
        if (m.pcount > 0) {
            model["parameters"]["values"].call<void>("set",
                         val(emscripten::typed_memory_view(m.pcount, m.pvalues)));
        }
    }

    void refresh_out()
    {
        val p = model["parameters"];
        pull_into(p["values"], m.pvalues, m.pcount * 4);
        val parts = model["parts"];
        pull_into(parts["opacities"], m.opacities, m.ocount * 4);
        val d = model["drawables"];
        pull_into(d["dynamicFlags"], m.idyn, m.dcount);
        pull_into(d["opacities"], m.dopacity, m.dcount * 4);
        pull_into(d["multiplyColors"], m.mul, m.dcount * 16);
        pull_into(d["screenColors"], m.screen, m.dcount * 16);
        for (int i = 0; i < m.dcount; ++i) {
            pull_into(d["vertexPositions"][i], m.verts[i],
                     d["vertexPositions"][i]["byteLength"].as<int>());
            pull_into(d["vertexUvs"][i], m.uvs[i],
                     d["vertexUvs"][i]["byteLength"].as<int>());
            pull_into(d["indices"][i], m.indices[i],
                     d["indices"][i]["byteLength"].as<int>());
            if (m.masks != nullptr && i < d["masks"]["length"].as<int>()) {
                pull_into(d["masks"][i], m.masks[i],
                         d["masks"][i]["byteLength"].as<int>());
            }
        }
        val oo = model["offscreens"];
        pull_into(oo["opacities"], m.ooOpacity, m.oocount * 4);
        pull_into(oo["multiplyColors"], m.ooMul, m.oocount * 16);
        pull_into(oo["screenColors"], m.ooScreen, m.oocount * 16);
        pull_into(model.call<val>("getRenderOrders"), m.renderOrders,
                 m.dcount * 4);
    }

    void build_mirror()
    {
        val p = model["parameters"];
        m.pcount = p["count"].as<int>();
        if (m.pcount > 0) {
            m.pids = dup_strings(p["ids"]);
            m.ptypes = pull_ta_as<int>(p["types"]);
            m.pmin = pull_ta_as<float>(p["minimumValues"]);
            m.pmax = pull_ta_as<float>(p["maximumValues"]);
            m.pdef = pull_ta_as<float>(p["defaultValues"]);
            m.pvalues = pull_ta_as<float>(p["values"]);
            m.prepeats = pull_ta_as<int>(p["repeats"]);
            m.pkeyCounts = pull_ta_as<int>(p["keyCounts"]);
            m.pkeyValues = pull_ta_array<float>(p["keyValues"]);
        }
        val parts = model["parts"];
        m.ocount = parts["count"].as<int>();
        if (m.ocount > 0) {
            m.oids = dup_strings(parts["ids"]);
            m.opacities = pull_ta_as<float>(parts["opacities"]);
            m.parent = pull_ta_as<int>(parts["parentIndices"]);
            m.offscreenIdx = pull_ta_as<int>(parts["offscreenIndices"]);
        }
        val d = model["drawables"];
        m.dcount = d["count"].as<int>();
        if (m.dcount > 0) {
            m.dids = dup_strings(d["ids"]);
            m.iconst = pull_ta_as<unsigned char>(d["constantFlags"]);
            m.idyn = pull_ta_as<unsigned char>(d["dynamicFlags"]);
            m.blend = pull_ta_as<int>(d["blendModes"]);
            m.tex = pull_ta_as<int>(d["textureIndices"]);
            m.drawOrder = pull_ta_as<int>(d["drawOrders"]);
            m.dopacity = pull_ta_as<float>(d["opacities"]);
            m.maskCounts = pull_ta_as<int>(d["maskCounts"]);
            m.masks = pull_ta_array<int>(d["masks"]);
            m.vcounts = pull_ta_as<int>(d["vertexCounts"]);
            m.verts = pull_ta_array<float>(d["vertexPositions"]);
            m.uvs = pull_ta_array<float>(d["vertexUvs"]);
            m.icounts = pull_ta_as<int>(d["indexCounts"]);
            m.indices = pull_ta_array<unsigned short>(d["indices"]);
            m.mul = pull_ta_as<float>(d["multiplyColors"]);
            m.screen = pull_ta_as<float>(d["screenColors"]);
            m.dparent = pull_ta_as<int>(d["parentPartIndices"]);
            m.renderOrders = static_cast<int*>(std::malloc(m.dcount * sizeof(int)));
        }
        val oo = model["offscreens"];
        m.oocount = oo["count"].as<int>();
        if (m.oocount > 0) {
            m.ooBlend = pull_ta_as<int>(oo["blendModes"]);
            m.ooOpacity = pull_ta_as<float>(oo["opacities"]);
            m.ooOwner = pull_ta_as<int>(oo["ownerIndices"]);
            m.ooMul = pull_ta_as<float>(oo["multiplyColors"]);
            m.ooScreen = pull_ta_as<float>(oo["screenColors"]);
            m.ooMaskCounts = pull_ta_as<int>(oo["maskCounts"]);
            m.ooMasks = pull_ta_array<int>(oo["masks"]);
            m.ooConst = pull_ta_as<unsigned char>(oo["constantFlags"]);
        }
    }
};

} // namespace

extern "C" {

csmVersion csmGetVersion()
{
    return static_cast<csmVersion>(l2dcore()["Version"].call<int>("csmGetVersion"));
}

csmMocVersion csmGetLatestMocVersion()
{
    return static_cast<csmMocVersion>(l2dcore()["Version"].call<int>("csmGetLatestMocVersion"));
}

csmMocVersion csmGetMocVersion(const void* address, const unsigned int size)
{
    val ab = heap_to_ab_copy(address, (int)size);
    return static_cast<csmMocVersion>(
        l2dcore()["Version"].call<int>("csmGetMocVersion", ab));
}

int csmHasMocConsistency(void* address, const unsigned int size)
{
    try {
        val ab = heap_to_ab_copy(address, (int)size);
        val moc = moc_class().call<val>("fromArrayBuffer", ab);
        const int ok = moc.call<int>("hasMocConsistency", ab);
        moc.call<void>("_release");
        return ok;
    } catch (...) {
        return 0;
    }
}

csmLogFunction csmGetLogFunction()
{
    return nullptr;
}

void csmSetLogFunction(csmLogFunction handler)
{
    // the driver installs a log function to report its own model errors, and
    // never reads one back; keep it here in C++ to hand to nothing. The Core's
    // logging stays in its own JS.
    (void)handler;
}

csmMoc* csmReviveMocInPlace(void* address, const unsigned int size)
{
    // snapshot the moc bytes before the handle lands on the buffer head:
    // the placement WebMoc carries val members, and their ids would
    // clobber the moc header in place
    val bytes = heap_to_ab_copy(address, (int)size);
    WebMoc* handle = new (address) WebMoc();
    handle->bytes = bytes;
    handle->version = l2dcore()["Version"].call<int>("csmGetMocVersion", bytes);
    handle->moc = moc_class().call<val>("fromArrayBuffer", bytes);
    return static_cast<csmMoc*>(address);
}

unsigned int csmGetSizeofModel(const csmMoc* /*moc*/)
{
    return sizeof(WebModel);
}

csmModel* csmInitializeModelInPlace(const csmMoc* moc, void* address, const unsigned int size)
{
    if (size < sizeof(WebModel)) {
        return nullptr;
    }
    WebMoc* mh = reinterpret_cast<WebMoc*>(const_cast<csmMoc*>(moc));
    WebModel* model = new (address) WebModel();
    model->model = model_class().call<val>("fromMoc", mh->moc);
    model->build_mirror();
    return static_cast<csmModel*>(address);
}

void csmUpdateModel(csmModel* model_)
{
    WebModel* model = reinterpret_cast<WebModel*>(model_);
    model->refresh_in();
    model->model.call<void>("update");
    model->refresh_out();
}

const int* csmGetRenderOrders(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.renderOrders;
}

void csmReadCanvasInfo(const csmModel* model_, csmVector2* outSizeInPixels,
                       csmVector2* outOriginInPixels, float* outPixelsPerUnit)
{
    const WebModel* model = reinterpret_cast<const WebModel*>(model_);
    val info = model->model["canvasinfo"];
    if (outSizeInPixels) {
        outSizeInPixels->X = info["CanvasWidth"].as<float>();
        outSizeInPixels->Y = info["CanvasHeight"].as<float>();
    }
    if (outOriginInPixels) {
        outOriginInPixels->X = info["CanvasOriginX"].as<float>();
        outOriginInPixels->Y = info["CanvasOriginY"].as<float>();
    }
    if (outPixelsPerUnit) {
        *outPixelsPerUnit = info["PixelsPerUnit"].as<float>();
    }
}

int csmGetParameterCount(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.pcount;
}

const char** csmGetParameterIds(const csmModel* model_)
{
    return (const char**)reinterpret_cast<const WebModel*>(model_)->m.pids;
}

const csmParameterType* csmGetParameterTypes(const csmModel* model_)
{
    return reinterpret_cast<const csmParameterType*>(
        reinterpret_cast<const WebModel*>(model_)->m.ptypes);
}

const float* csmGetParameterMinimumValues(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.pmin;
}

const float* csmGetParameterMaximumValues(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.pmax;
}

const float* csmGetParameterDefaultValues(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.pdef;
}

float* csmGetParameterValues(csmModel* model_)
{
    return reinterpret_cast<WebModel*>(model_)->m.pvalues;
}

const int* csmGetParameterRepeats(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.prepeats;
}

const int* csmGetParameterKeyCounts(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.pkeyCounts;
}

const float** csmGetParameterKeyValues(const csmModel* model_)
{
    return const_cast<const float**>(reinterpret_cast<const WebModel*>(model_)->m.pkeyValues);
}

int csmGetPartCount(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.ocount;
}

const char** csmGetPartIds(const csmModel* model_)
{
    return (const char**)reinterpret_cast<const WebModel*>(model_)->m.oids;
}

float* csmGetPartOpacities(csmModel* model_)
{
    return reinterpret_cast<WebModel*>(model_)->m.opacities;
}

const int* csmGetPartParentPartIndices(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.parent;
}

const int* csmGetPartOffscreenIndices(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.offscreenIdx;
}

int csmGetDrawableCount(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.dcount;
}

const char** csmGetDrawableIds(const csmModel* model_)
{
    return (const char**)reinterpret_cast<const WebModel*>(model_)->m.dids;
}

const csmFlags* csmGetDrawableConstantFlags(const csmModel* model_)
{
    return reinterpret_cast<const csmFlags*>(
        reinterpret_cast<const WebModel*>(model_)->m.iconst);
}

const csmFlags* csmGetDrawableDynamicFlags(const csmModel* model_)
{
    return reinterpret_cast<const csmFlags*>(
        reinterpret_cast<const WebModel*>(model_)->m.idyn);
}

const int* csmGetDrawableBlendModes(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.blend;
}

const int* csmGetDrawableTextureIndices(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.tex;
}

const int* csmGetDrawableDrawOrders(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.drawOrder;
}

const float* csmGetDrawableOpacities(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.dopacity;
}

const int* csmGetDrawableMaskCounts(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.maskCounts;
}

const int** csmGetDrawableMasks(const csmModel* model_)
{
    return const_cast<const int**>(reinterpret_cast<const WebModel*>(model_)->m.masks);
}

const int* csmGetDrawableVertexCounts(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.vcounts;
}

const csmVector2** csmGetDrawableVertexPositions(const csmModel* model_)
{
    return (const csmVector2**)reinterpret_cast<const WebModel*>(model_)->m.verts;
}

const csmVector2** csmGetDrawableVertexUvs(const csmModel* model_)
{
    return (const csmVector2**)reinterpret_cast<const WebModel*>(model_)->m.uvs;
}

const int* csmGetDrawableIndexCounts(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.icounts;
}

const unsigned short** csmGetDrawableIndices(const csmModel* model_)
{
    return const_cast<const unsigned short**>(
        reinterpret_cast<const WebModel*>(model_)->m.indices);
}

const csmVector4* csmGetDrawableMultiplyColors(const csmModel* model_)
{
    return reinterpret_cast<const csmVector4*>(
        reinterpret_cast<const WebModel*>(model_)->m.mul);
}

const csmVector4* csmGetDrawableScreenColors(const csmModel* model_)
{
    return reinterpret_cast<const csmVector4*>(
        reinterpret_cast<const WebModel*>(model_)->m.screen);
}

const int* csmGetDrawableParentPartIndices(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.dparent;
}

void csmResetDrawableDynamicFlags(csmModel* model_)
{
    WebModel* model = reinterpret_cast<WebModel*>(model_);
    model->model["drawables"].call<void>("resetDynamicFlags");
    // the Core's flags are now all dynamic; refresh the mirror to match
    pull_into(model->model["drawables"]["dynamicFlags"],
              model->m.idyn, model->m.dcount);
}

int csmGetOffscreenCount(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.oocount;
}

const int* csmGetOffscreenBlendModes(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.ooBlend;
}

const float* csmGetOffscreenOpacities(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.ooOpacity;
}

const int* csmGetOffscreenOwnerIndices(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.ooOwner;
}

const csmVector4* csmGetOffscreenMultiplyColors(const csmModel* model_)
{
    return reinterpret_cast<const csmVector4*>(
        reinterpret_cast<const WebModel*>(model_)->m.ooMul);
}

const csmVector4* csmGetOffscreenScreenColors(const csmModel* model_)
{
    return reinterpret_cast<const csmVector4*>(
        reinterpret_cast<const WebModel*>(model_)->m.ooScreen);
}

const int* csmGetOffscreenMaskCounts(const csmModel* model_)
{
    return reinterpret_cast<const WebModel*>(model_)->m.ooMaskCounts;
}

const int** csmGetOffscreenMasks(const csmModel* model_)
{
    return const_cast<const int**>(reinterpret_cast<const WebModel*>(model_)->m.ooMasks);
}

const csmFlags* csmGetOffscreenConstantFlags(const csmModel* model_)
{
    return reinterpret_cast<const csmFlags*>(
        reinterpret_cast<const WebModel*>(model_)->m.ooConst);
}

} // extern "C"