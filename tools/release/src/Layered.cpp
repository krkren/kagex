#include "Layered.h"

#include <algorithm>
#include <atomic>
#include <cctype>
#include <chrono>
#include <functional>
#include <map>
#include <optional>
#include <set>
#include <thread>

#include <clipfile.h>
#include <psdfile.h>

#include "Archive.h"
#include "Host.h"
#include "krt/app/Progress.h"
#include "krt/app/Text.h"
#include "krt/image/Image.h"

namespace fs = std::filesystem;

namespace kr {

namespace {

// the engine's layer types (tp_stub.h tTVPLayerType), as the plugins report them
enum {
	ltPsNormal = 13, ltPsAdditive = 14, ltPsSubtractive = 15, ltPsMultiplicative = 16, ltPsScreen = 17,
	ltPsOverlay = 18, ltPsHardLight = 19, ltPsSoftLight = 20, ltPsColorDodge = 21, ltPsColorBurn = 23,
	ltPsLighten = 24, ltPsDarken = 25, ltPsDifference = 26, ltPsExclusion = 28,
};

// psdfile's convBlendMode
int psdLayerType(psd::BlendMode mode)
{
	switch (mode) {
	case psd::BLEND_MODE_NORMAL:       return ltPsNormal;
	case psd::BLEND_MODE_DARKEN:       return ltPsDarken;
	case psd::BLEND_MODE_MULTIPLY:     return ltPsMultiplicative;
	case psd::BLEND_MODE_COLOR_BURN:   return ltPsColorBurn;
	case psd::BLEND_MODE_LINEAR_BURN:  return ltPsSubtractive;
	case psd::BLEND_MODE_LIGHTEN:      return ltPsLighten;
	case psd::BLEND_MODE_SCREEN:       return ltPsScreen;
	case psd::BLEND_MODE_COLOR_DODGE:  return ltPsColorDodge;
	case psd::BLEND_MODE_LINEAR_DODGE: return ltPsAdditive;
	case psd::BLEND_MODE_OVERLAY:      return ltPsOverlay;
	case psd::BLEND_MODE_SOFT_LIGHT:   return ltPsSoftLight;
	case psd::BLEND_MODE_HARD_LIGHT:   return ltPsHardLight;
	case psd::BLEND_MODE_DIFFERENCE:   return ltPsDifference;
	case psd::BLEND_MODE_EXCLUSION:    return ltPsExclusion;
	default:                           return ltPsNormal;
	}
}

// clipfile's clipCompositeToTjsType and clipOpacityToTjs
int clipLayerType(int composite)
{
	switch (composite) {
	case 1: return ltPsDarken;
	case 2: return ltPsMultiplicative;
	case 3: return ltPsColorBurn;
	case 4: return ltPsSubtractive;
	case 7: return ltPsLighten;
	case 8: return ltPsScreen;
	case 9: case 10: return ltPsColorDodge;
	case 11: case 12: return ltPsAdditive;
	case 14: return ltPsOverlay;
	case 15: return ltPsSoftLight;
	case 16: return ltPsHardLight;
	case 21: return ltPsDifference;
	case 22: return ltPsExclusion;
	default: return ltPsNormal;
	}
}

int clipOpacity(int64_t opacity)
{
	const int v = (int)(opacity * 255 / 256);
	return v > 255 ? 255 : v < 0 ? 0 : v;
}

std::string lower(std::string s)
{
	for (auto& c : s) c = (char)std::tolower((unsigned char)c);
	return s;
}

std::string extOf(const std::string& leaf)
{
	const size_t dot = leaf.rfind('.');
	return dot == std::string::npos ? std::string() : lower(leaf.substr(dot));
}

std::string stemOf(const std::string& leaf)
{
	const size_t dot = leaf.rfind('.');
	return dot == std::string::npos ? leaf : leaf.substr(0, dot);
}

bool isLayered(const std::string& ext) { return ext == ".psd" || ext == ".clip"; }

std::string utf16ToUtf8(const std::u16string& s)
{
	std::string o;
	for (size_t i = 0; i < s.size(); ++i) {
		uint32_t c = s[i];
		if (c >= 0xd800 && c < 0xdc00 && i + 1 < s.size() && s[i + 1] >= 0xdc00 && s[i + 1] < 0xe000)
			c = 0x10000 + ((c - 0xd800) << 10) + (s[++i] - 0xdc00);
		if (c < 0x80) o += (char)c;
		else if (c < 0x800) { o += (char)(0xc0 | (c >> 6)); o += (char)(0x80 | (c & 0x3f)); }
		else if (c < 0x10000) { o += (char)(0xe0 | (c >> 12)); o += (char)(0x80 | ((c >> 6) & 0x3f)); o += (char)(0x80 | (c & 0x3f)); }
		else { o += (char)(0xf0 | (c >> 18)); o += (char)(0x80 | ((c >> 12) & 0x3f)); o += (char)(0x80 | ((c >> 6) & 0x3f)); o += (char)(0x80 | (c & 0x3f)); }
	}
	return o;
}

// A name as psdlayer.tjs keeps it ("/" as "_"), and one line of the text format can hold
std::string layerName(std::string name)
{
	for (auto& c : name) {
		if (c == '/') c = '_';
		else if (c == '\t' || c == '\r' || c == '\n') c = ' ';
	}
	return name;
}

// A Pascal name without a Unicode one: its bytes, unless they aren't UTF-8
std::string narrowName(const std::string& raw)
{
	std::string o;
	size_t i = 0;
	while (i < raw.size()) {
		const unsigned char c = (unsigned char)raw[i];
		size_t n = c < 0x80 ? 1 : (c >> 5) == 6 ? 2 : (c >> 4) == 14 ? 3 : (c >> 3) == 30 ? 4 : 0;
		bool ok = n && i + n <= raw.size();
		for (size_t k = 1; ok && k < n; ++k) ok = ((unsigned char)raw[i + k] >> 6) == 2;
		if (!ok) { o += '?'; ++i; continue; }
		o += raw.substr(i, n);
		i += n;
	}
	return o;
}

// One line of the layer structure, and the picture of a layer that draws something
struct Entry {
	int kind = 0;   // 0 a layer, 2 a folder (psdfile's layer_type)
	std::string name;
	int left = 0, top = 0, width = 0, height = 0, type = ltPsNormal, opacity = 255;
	bool visible = true;
	int64_t id = 0;
	std::optional<int64_t> group;
	krt::image::Image picture;
};

struct Structure {
	int width = 0, height = 0;
	std::vector<Entry> entries;   // the top first, as psdlayer.tjs's loadPSD reads them
};

bool readPsd(const std::string& buf, Structure& out, std::string& error)
{
	psd::PSDFile psd;
	if (!psd.loadFromMemory((const uint8_t*)buf.data(), buf.size())) { error = "not a Photoshop file it can read"; return false; }
	out.width = psd.header.width;
	out.height = psd.header.height;
	// psdparse takes a file cut short after its signature as one without layers
	if (out.width <= 0 || out.height <= 0) { error = "not a Photoshop file it can read (it has no picture size)"; return false; }
	auto& list = psd.layerList;
	// psdfile's assignAutoIds (psdlayer.tjs's loadPSD calls it): the layers without an ID are
	// numbered on from the largest ID, in the file's order
	int base = 0;
	for (const auto& l : list) base = std::max(base, l.layerId);
	for (auto& l : list) if (l.layerId == -1) l.layerId = ++base;
	for (int i = (int)list.size() - 1; i >= 0; --i) {
		const psd::LayerInfo& l = list[i];
		if (l.layerType != psd::LAYER_TYPE_NORMAL && l.layerType != psd::LAYER_TYPE_FOLDER) continue;
		Entry e;
		e.kind = l.layerType == psd::LAYER_TYPE_FOLDER ? 2 : 0;
		e.name = layerName(l.layerNameUnicode.empty() ? narrowName(l.layerName) : utf16ToUtf8(l.layerNameUnicode));
		e.left = l.left;
		e.top = l.top;
		e.width = l.width;
		e.height = l.height;
		e.type = psdLayerType(l.blendMode);
		e.opacity = l.opacity;
		e.visible = l.isVisible();
		e.id = l.layerId;
		if (l.parent) e.group = l.parent->layerId;
		if (e.kind == 0) {
			if (l.width <= 0 || l.height <= 0) continue;   // an empty layer: no picture (psdlayer.tjs leaves it out too)
			e.picture.width = l.width;
			e.picture.height = l.height;
			e.picture.bgra.assign((size_t)l.width * l.height * 4, 0);
			// psdfile's getLayerData: the image with its mask in the alpha
			if (!psd.getLayerImage(l, e.picture.bgra.data(), psd::BGRA_LE, l.width * 4, psd::IMAGE_MODE_MASKEDIMAGE)) {
				error = "the picture of layer \"" + e.name + "\" can't be read";
				return false;
			}
		}
		out.entries.push_back(std::move(e));
	}
	return true;
}

bool readClip(const std::string& buf, Structure& out, std::string& error)
{
	clip::ClipFile cf;
	if (!cf.loadFromMemory((const uint8_t*)buf.data(), (int64_t)buf.size())) {
		error = "not a CLIP STUDIO PAINT file it can read" + (cf.error().empty() ? std::string() : ": " + cf.error());
		return false;
	}
	out.width = (int)cf.canvasWidth();
	out.height = (int)cf.canvasHeight();
	if (out.width <= 0 || out.height <= 0) { error = "not a CLIP STUDIO PAINT file it can read (it has no canvas size)"; return false; }
	const auto& list = cf.layers();
	for (int i = (int)list.size() - 1; i >= 0; --i) {
		const clip::LayerInfo& l = list[i];
		if (l.isFilter) continue;   // adjustment layers have no picture
		Entry e;
		e.kind = l.isGroup ? 2 : 0;
		e.name = layerName(l.name);
		e.left = (int)l.bounds.x;
		e.top = (int)l.bounds.y;
		e.width = (int)l.bounds.w;
		e.height = (int)l.bounds.h;
		e.type = clipLayerType((int)l.composite);
		e.opacity = clipOpacity(l.opacity);
		e.visible = l.visibility != 0;
		e.id = l.mainId;
		if (l.parent >= 0) e.group = list[l.parent].mainId;
		if (e.kind == 0) {
			if (e.width <= 0 || e.height <= 0) continue;
			clip::Image img;
			if (!cf.layerImage(i, clip::IMAGE_MODE_MASKED, img)) {
				error = "the picture of layer \"" + e.name + "\" can't be read";
				return false;
			}
			if (img.width == 0 || img.height == 0) continue;
			e.width = (int)img.width;
			e.height = (int)img.height;
			e.picture.width = e.width;
			e.picture.height = e.height;
			e.picture.bgra.resize(img.rgba.size());
			for (size_t k = 0; k + 3 < img.rgba.size(); k += 4) {
				e.picture.bgra[k] = img.rgba[k + 2];
				e.picture.bgra[k + 1] = img.rgba[k + 1];
				e.picture.bgra[k + 2] = img.rgba[k];
				e.picture.bgra[k + 3] = img.rgba[k + 3];
			}
		}
		out.entries.push_back(std::move(e));
	}
	return true;
}

// psdlayer.tjs's text format, UTF-8 with a BOM (so a game reading Shift_JIS reads it right).
// kind is ".psd" or ".clip" (not the file's name: the cache shares a split by content)
std::string structureText(const std::string& kind, const Structure& st)
{
	std::string t = "\xEF\xBB\xBF# The layers of a " + kind + " file, split by kagex-release (psdlayer.tjs's layer structure)\n";
	t += "#layer_type\tname\tleft\ttop\twidth\theight\ttype\topacity\tvisible\tlayer_id\tgroup_layer_id\tbase\timages\n";
	t += "\t\t\t\t" + std::to_string(st.width) + "\t" + std::to_string(st.height) + "\n";
	for (const auto& e : st.entries) {
		t += std::to_string(e.kind) + "\t" + e.name + "\t" + std::to_string(e.left) + "\t" + std::to_string(e.top) + "\t" +
		     std::to_string(e.width) + "\t" + std::to_string(e.height) + "\t" + std::to_string(e.type) + "\t" +
		     std::to_string(e.opacity) + "\t" + (e.visible ? "1" : "0") + "\t" + std::to_string(e.id) + "\t" +
		     (e.group ? std::to_string(*e.group) : std::string()) + "\n";
	}
	return t;
}

// The format a picture is written in: the one the media settings convert to when it's lossless
// (TLG6, TLG5, PNG), else TLG6, which the media conversion turns into JPEG when that's asked for
krt::image::Format pictureFormat(const Json& s, bool alpha)
{
	const std::string to = str(s, alpha ? "media.images.alpha" : "media.images.opaque");
	if (to == "png") return krt::image::Format::Png;
	if (to == "tlg5") return krt::image::Format::Tlg5;
	return krt::image::Format::Tlg6;
}

// Reads file and writes its structure and pictures into dir as layers.txt and <id><ext>
// (a cache entry); names lists what it wrote, "layers.txt" first
bool split(const fs::path& file, const fs::path& dir, const Json& s,
           std::vector<std::string>& names, int& pictures, std::string& error)
{
	std::string buf;
	if (!krt::readFile(file, buf)) { error = "can't be read"; return false; }
	Structure st;
	const std::string ext = extOf(krt::fromPath(file.filename()));
	if (!(ext == ".clip" ? readClip(buf, st, error) : readPsd(buf, st, error))) return false;
	std::set<int64_t> ids;
	for (const auto& e : st.entries) {
		if (e.kind != 0) continue;
		if (!ids.insert(e.id).second) { error = "two layers have the ID " + std::to_string(e.id); return false; }
	}
	if (!krt::writeFile(dir / "layers.txt", structureText(ext, st))) { error = "can't write its layer structure"; return false; }
	names.push_back("layers.txt");
	for (const auto& e : st.entries) {
		if (e.kind != 0) continue;
		const bool alpha = krt::image::hasTransparency(e.picture);
		const krt::image::Format f = pictureFormat(s, alpha);
		krt::image::SaveOptions so;
		so.withAlpha = alpha;
		const std::string name = std::to_string(e.id) + krt::image::formatExtension(f);
		std::string err;
		if (!krt::image::save(dir / krt::toPath(name), e.picture, f, so, err)) {
			error = "can't write the picture of layer \"" + e.name + "\": " + err;
			return false;
		}
		names.push_back(name);
		++pictures;
	}
	return true;
}

std::string cacheKey(const fs::path& file, const Json& s, std::string& error)
{
	std::string hex;
	if (!sha256File(file, hex, error)) return "";
	Sha256 h;
	const std::string k = hex + "|layers|" + krt::fromPath(file.extension()) + "|" + str(s, "media.images.opaque") + "|" +
	                      str(s, "media.images.alpha") + "|" + KAGEX_RELEASE_VERSION;
	h.update(k.data(), k.size());
	return h.hex();
}

// A file through the cache: entry is the cache folder holding layers.txt and the pictures
bool splitCached(const fs::path& file, const Json& s, const fs::path& cache,
                 fs::path& entry, std::vector<std::string>& names, bool& cached, std::string& error)
{
	const std::string key = cacheKey(file, s, error);
	if (key.empty()) return false;
	entry = cache / key.substr(0, 2) / key;
	std::error_code ec;
	std::string manifest;
	if (krt::readFile(entry / "done", manifest)) {
		names.clear();
		size_t pos = 0;
		bool all = true;
		while (pos < manifest.size()) {
			size_t end = manifest.find('\n', pos);
			if (end == std::string::npos) end = manifest.size();
			const std::string n = manifest.substr(pos, end - pos);
			pos = end + 1;
			if (n.empty()) continue;
			if (!fs::is_regular_file(entry / krt::toPath(n), ec)) all = false;
			names.push_back(n);
		}
		if (all && !names.empty() && names.front() == "layers.txt") { cached = true; return true; }
		names.clear();
	}
	const fs::path tmp = cache / key.substr(0, 2) / (key + ".part" + std::to_string(std::hash<std::thread::id>()(std::this_thread::get_id()) % 100000));
	fs::remove_all(tmp, ec);
	fs::create_directories(tmp, ec);
	int pictures = 0;
	if (!split(file, tmp, s, names, pictures, error)) { fs::remove_all(tmp, ec); return false; }
	std::string m;
	for (const auto& n : names) m += n + "\n";
	krt::writeFile(tmp / "done", m);
	fs::remove_all(entry, ec);
	fs::rename(tmp, entry, ec);
	if (ec) fs::remove_all(tmp, ec);   // another build got there first: use its entry
	return true;
}

bool copyOut(const fs::path& from, const fs::path& to, std::string& error)
{
	std::error_code ec;
	fs::remove(to, ec);
	fs::copy_file(from, to, fs::copy_options::overwrite_existing, ec);
	if (ec) { error = "Can't write " + krt::fromPath(to) + ": " + ec.message(); return false; }
	return true;
}

} // namespace

bool frameworkReadsSplitLayers(const fs::path& framework)
{
	std::string affine, character;
	if (!krt::readFile(framework / "AffineLayer.tjs", affine) || !krt::readFile(framework / "KAGEnvCharacterEx.tjs", character))
		return false;
	return affine.find("affineLayeredFromPieces") != std::string::npos && character.find("findStandLayerFile") != std::string::npos;
}

bool isLayerStructure(const fs::path& txt)
{
	std::string raw;
	if (!krt::readFile(txt, raw)) return false;
	if (raw.size() > 65536) raw.resize(65536);
	std::string text;
	if (raw.size() >= 2 && (unsigned char)raw[0] == 0xFF && (unsigned char)raw[1] == 0xFE) {
		// UTF-16LE (Array.save): the canvas line is ASCII, so every other byte will do
		for (size_t i = 2; i + 1 < raw.size(); i += 2) text += raw[i + 1] ? '?' : raw[i];
	} else {
		text = raw.compare(0, 3, "\xEF\xBB\xBF") == 0 ? raw.substr(3) : raw;
	}
	size_t pos = 0;
	while (pos < text.size()) {
		size_t end = text.find('\n', pos);
		if (end == std::string::npos) end = text.size();
		std::string line = text.substr(pos, end - pos);
		pos = end + 1;
		if (!line.empty() && line.back() == '\r') line.pop_back();
		if (line.empty() || line[0] == '#') continue;
		std::vector<std::string> f;
		size_t a = 0;
		for (;;) {
			const size_t t = line.find('\t', a);
			f.push_back(line.substr(a, t == std::string::npos ? std::string::npos : t - a));
			if (t == std::string::npos) break;
			a = t + 1;
		}
		const auto number = [](const std::string& v) { return !v.empty() && v.find_first_not_of("0123456789") == std::string::npos; };
		return f.size() >= 6 && f[0].empty() && f[1].empty() && f[2].empty() && f[3].empty() && number(f[4]) && number(f[5]);
	}
	return false;
}

bool splitLayeredFile(const fs::path& file, const fs::path& dir, const Json& s, std::vector<fs::path>& written, std::string& error)
{
	std::error_code ec;
	const fs::path tmp = dir / ".kagex-split";
	fs::remove_all(tmp, ec);
	fs::create_directories(tmp, ec);
	std::vector<std::string> names;
	int pictures = 0;
	const std::string leaf = krt::fromPath(file.filename()), stem = stemOf(leaf);
	bool ok = split(file, tmp, s, names, pictures, error);
	for (const auto& n : names) {
		if (!ok) break;
		const fs::path to = dir / krt::toPath(n == "layers.txt" ? stem + ".txt" : stem + "_" + n);
		ok = copyOut(tmp / krt::toPath(n), to, error);
		if (ok) written.push_back(to);
	}
	fs::remove_all(tmp, ec);
	return ok;
}

bool splitLayeredFiles(const Json& s, const fs::path& stage, krt::Progress& progress, LayeredResult& result, std::string& error)
{
	std::error_code ec;
	struct File { fs::path path; std::string name, leaf, stem; };
	std::vector<File> files;
	std::set<std::string> leaves;   // every staged file's leaf, lower case (the auto path finds files by it)
	for (fs::recursive_directory_iterator it(stage, ec), end; it != end; it.increment(ec)) {
		if (ec || !it->is_regular_file(ec)) continue;
		File f;
		f.path = it->path();
		f.name = krt::fromPath(fs::relative(it->path(), stage, ec));
		f.leaf = krt::fromPath(it->path().filename());
		f.stem = stemOf(f.leaf);
		leaves.insert(lower(f.leaf));
		if (isLayered(extOf(f.leaf))) files.push_back(std::move(f));
	}
	if (files.empty()) return true;
	std::sort(files.begin(), files.end(), [](const File& a, const File& b) { return a.name < b.name; });

	// what the files would be split into must be names no other file has: <stem>.txt, and
	// <stem>_<number> pictures in any format
	std::set<std::string> stems;
	for (const auto& f : files) {
		const std::string st = lower(f.stem);
		if (!stems.insert(st).second) {
			error = f.name + ": another .psd or .clip file is also called " + f.stem + ", and they would be split into the same names";
			return false;
		}
		if (leaves.count(st + ".txt")) {
			error = f.name + ": the game already has " + f.stem + ".txt, the name its layer structure would be written to (rename one of them)";
			return false;
		}
	}
	static const std::set<std::string> pictureExts = { ".png", ".tlg", ".tlg5", ".tlg6", ".bmp", ".jpg", ".jpeg", ".webp", ".svg" };
	for (const auto& l : leaves) {
		const size_t us = l.rfind('_');
		if (us == std::string::npos || !pictureExts.count(extOf(l))) continue;
		const std::string head = l.substr(0, us), tail = stemOf(l.substr(us + 1));
		if (tail.empty() || tail.find_first_not_of("0123456789") != std::string::npos || !stems.count(head)) continue;
		error = "The game already has " + l + ", a name the layer pictures of " + head + ".psd or .clip would take (rename one of them)";
		return false;
	}

	// split, in parallel
	const fs::path cache = cacheDir() / "layers";
	fs::create_directories(cache, ec);
	struct Job { fs::path entry; std::vector<std::string> names; bool cached = false, ok = false; std::string error; };
	std::vector<Job> jobs(files.size());
	std::atomic<size_t> next{ 0 }, done{ 0 };
	// a few at a time: each file is read whole, and a PSD can be hundreds of megabytes
	const unsigned workers = std::max(1u, std::min<unsigned>({ std::thread::hardware_concurrency(), 4u, (unsigned)files.size() }));
	std::vector<std::thread> threads;
	for (unsigned w = 0; w < workers; ++w) {
		threads.emplace_back([&]() {
			for (;;) {
				const size_t i = next++;
				if (i >= files.size() || progress.canceled()) break;
				try {
					jobs[i].ok = splitCached(files[i].path, s, cache, jobs[i].entry, jobs[i].names, jobs[i].cached, jobs[i].error);
				} catch (const std::exception& e) {
					jobs[i].error = e.what();
				}
				++done;
			}
		});
	}
	while (done < files.size()) {
		progress.progress((double)done / files.size(), "Splitting PSD and CLIP files into layers (" + std::to_string(done.load()) + " of " + std::to_string(files.size()) + ")");
		if (progress.canceled()) break;
		std::this_thread::sleep_for(std::chrono::milliseconds(100));
	}
	for (auto& t : threads) t.join();
	if (progress.canceled()) { error = "Canceled"; return false; }

	for (size_t i = 0; i < files.size(); ++i) {
		const File& f = files[i];
		const Job& j = jobs[i];
		if (!j.ok) {
			// as the media conversion keeps a picture it can't read: the game reads it as it did
			// during development (on the desktop engines, through the plugin)
			result.notes.push_back(f.name + " couldn't be split into its layers (" + j.error + "), so it went in as it is");
			continue;
		}
		const fs::path dir = f.path.parent_path();
		result.bytesBefore += fs::file_size(f.path, ec);
		fs::remove(f.path, ec);   // a hard link to the game's file: removed, not written to
		for (const auto& n : j.names) {
			const fs::path to = dir / krt::toPath(n == "layers.txt" ? f.stem + ".txt" : f.stem + "_" + n);
			if (!copyOut(j.entry / krt::toPath(n), to, error)) return false;
			result.bytesAfter += fs::file_size(to, ec);
			if (n != "layers.txt") ++result.pictures;
		}
		++result.files;
	}
	return true;
}

} // namespace kr
