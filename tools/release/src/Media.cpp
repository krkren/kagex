#include "Media.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstring>
#include <functional>
#include <map>
#include <mutex>
#include <regex>
#include <set>
#include <thread>

#include "Archive.h"
#include "Host.h"
#include "krt/app/Progress.h"
#include "krt/app/Text.h"
#include "krt/audio/Audio.h"
#include "krt/image/Image.h"
#include "krt/loop/Sli.h"

#define DR_FLAC_IMPLEMENTATION
#include <dr_flac.h>

namespace fs = std::filesystem;

namespace kr {

namespace {

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

std::string leafOf(const std::string& name)
{
	const size_t sl = name.rfind('/');
	return sl == std::string::npos ? name : name.substr(sl + 1);
}

bool isAudioSource(const std::string& ext) { return ext == ".wav" || ext == ".flac"; }
bool isImageSource(const std::string& ext) { return ext == ".png" || ext == ".bmp" || ext == ".tlg"; }
bool isScript(const std::string& ext)
{
	return ext == ".ks" || ext == ".tjs" || ext == ".csv" || ext == ".txt" || ext == ".asd" || ext == ".json" || ext == ".func";
}

//---------------------------------------------------------------------------
// Scripts: finding (and rewriting) file names written with their extension, in UTF-8,
// UTF-16LE (with a BOM) or Shift_JIS, without matching inside a double-byte character
//---------------------------------------------------------------------------
struct ScriptText {
	bool utf16 = false;
	std::string text;   // UTF-8 when utf16, else the bytes as they are
};

bool validUtf8(const std::string& s)
{
	size_t i = 0;
	while (i < s.size()) {
		const unsigned char c = (unsigned char)s[i];
		size_t n = c < 0x80 ? 1 : (c >> 5) == 6 ? 2 : (c >> 4) == 14 ? 3 : (c >> 3) == 30 ? 4 : 0;
		if (!n || i + n > s.size()) return false;
		for (size_t k = 1; k < n; ++k) if (((unsigned char)s[i + k] >> 6) != 2) return false;
		i += n;
	}
	return true;
}

std::string utf16ToUtf8(const std::string& in, size_t from)
{
	std::string out;
	for (size_t i = from; i + 1 < in.size(); i += 2) {
		uint32_t c = (unsigned char)in[i] | ((unsigned char)in[i + 1] << 8);
		if (c >= 0xD800 && c < 0xDC00 && i + 3 < in.size()) {
			const uint32_t lo = (unsigned char)in[i + 2] | ((unsigned char)in[i + 3] << 8);
			if (lo >= 0xDC00 && lo < 0xE000) { c = 0x10000 + ((c - 0xD800) << 10) + (lo - 0xDC00); i += 2; }
		}
		if (c < 0x80) out += (char)c;
		else if (c < 0x800) { out += (char)(0xC0 | c >> 6); out += (char)(0x80 | (c & 63)); }
		else if (c < 0x10000) { out += (char)(0xE0 | c >> 12); out += (char)(0x80 | ((c >> 6) & 63)); out += (char)(0x80 | (c & 63)); }
		else { out += (char)(0xF0 | c >> 18); out += (char)(0x80 | ((c >> 12) & 63)); out += (char)(0x80 | ((c >> 6) & 63)); out += (char)(0x80 | (c & 63)); }
	}
	return out;
}

//---------------------------------------------------------------------------
// Effekseer effects (.efk, and .efkefc, whose first BIN_ chunk is the same binary) name their
// textures, sounds, models and materials at the start of the binary, and the runtime opens them
// by those names (relative to the effect, or by the bare name on the auto path)
//---------------------------------------------------------------------------
bool isEffect(const std::string& ext) { return ext == ".efk" || ext == ".efkefc"; }

uint32_t le32(const std::string& s, size_t at)
{
	return (unsigned char)s[at] | ((unsigned char)s[at + 1] << 8) | ((unsigned char)s[at + 2] << 16) | ((uint32_t)(unsigned char)s[at + 3] << 24);
}

std::vector<std::string> effectResources(const std::string& raw)
{
	std::string body;
	if (raw.size() >= 8 && raw.compare(0, 4, "EFKE") == 0) {
		for (size_t at = 8; at + 8 <= raw.size();) {
			const size_t size = le32(raw, at + 4);
			if (raw.compare(at, 4, "BIN_") == 0) {
				if (at + 8 + size <= raw.size()) body = raw.substr(at + 8, size);
				break;
			}
			at += 8 + size;
		}
	} else {
		body = raw;
	}
	std::vector<std::string> names;
	if (body.size() < 8 || body.compare(0, 4, "SKFE") != 0) return names;
	const int32_t version = (int32_t)le32(body, 4);
	// colour images, then normal and distortion images (9+), sounds (1+), models (6+), materials (15+)
	const int lists = 1 + (version >= 9 ? 2 : 0) + (version >= 1 ? 1 : 0) + (version >= 6 ? 1 : 0) + (version >= 15 ? 1 : 0);
	size_t at = 8;
	for (int l = 0; l < lists; ++l) {
		if (at + 4 > body.size()) break;
		const uint32_t count = le32(body, at);
		at += 4;
		if (count > 1024) break;
		for (uint32_t i = 0; i < count; ++i) {
			if (at + 4 > body.size()) return names;
			const uint32_t chars = le32(body, at);   // with the terminating 0
			at += 4;
			if (chars > 1024 || at + chars * 2 > body.size()) return names;
			std::string name = utf16ToUtf8(body.substr(at, chars ? (chars - 1) * 2 : 0), 0);
			std::replace(name.begin(), name.end(), '\\', '/');
			if (!name.empty()) names.push_back(name);
			at += chars * 2;
		}
	}
	return names;
}

std::string utf8ToUtf16(const std::string& s)
{
	std::string out = "\xFF\xFE";
	size_t i = 0;
	while (i < s.size()) {
		const unsigned char c = (unsigned char)s[i];
		uint32_t cp;
		size_t n = c < 0x80 ? 1 : (c >> 5) == 6 ? 2 : (c >> 4) == 14 ? 3 : 4;
		cp = n == 1 ? c : n == 2 ? (c & 31) : n == 3 ? (c & 15) : (c & 7);
		for (size_t k = 1; k < n && i + k < s.size(); ++k) cp = (cp << 6) | ((unsigned char)s[i + k] & 63);
		i += n;
		auto put = [&](uint32_t u) { out += (char)(u & 0xff); out += (char)(u >> 8); };
		if (cp >= 0x10000) { cp -= 0x10000; put(0xD800 + (cp >> 10)); put(0xDC00 + (cp & 0x3ff)); }
		else put(cp);
	}
	return out;
}

ScriptText readScript(const std::string& raw)
{
	ScriptText t;
	if (raw.size() >= 2 && (unsigned char)raw[0] == 0xFF && (unsigned char)raw[1] == 0xFE) {
		t.utf16 = true;
		t.text = utf16ToUtf8(raw, 2);
	} else {
		t.text = raw;
	}
	return t;
}

// Where characters start: false for the second byte of a Shift_JIS double-byte character
std::vector<bool> charStarts(const std::string& s, bool sjis)
{
	std::vector<bool> start(s.size(), true);
	if (!sjis) return start;
	for (size_t i = 0; i < s.size(); ++i) {
		const unsigned char c = (unsigned char)s[i];
		if (((c >= 0x81 && c <= 0x9F) || (c >= 0xE0 && c <= 0xFC)) && i + 1 < s.size()) start[++i] = false;
	}
	return start;
}

bool nameChar(unsigned char c) { return std::isalnum(c) || c == '_' || c == '-'; }
// names can be printf patterns too ("voiceFile" => "ai%s%06d.wav" in envinit.tjs)
bool patternChar(unsigned char c) { return nameChar(c) || c == '%' || c == '.'; }

struct Reference {
	size_t extAt;      // where ".ext" starts
	size_t extLen;     // with the dot
	std::string leaf;  // lower case name.ext, or a printf pattern ("ai%s%06d.wav")
	bool pattern() const { return leaf.find('%') != std::string::npos; }
};

// The files a printf pattern names: each %d, %s, %06d... matches anything
std::regex patternRegex(const std::string& leaf)
{
	std::string re;
	for (size_t i = 0; i < leaf.size(); ++i) {
		const char c = leaf[i];
		if (c == '%') {
			size_t j = i + 1;
			while (j < leaf.size() && std::strchr("-+ #0123456789.", leaf[j])) ++j;
			if (j < leaf.size() && std::isalpha((unsigned char)leaf[j])) { re += ".*"; i = j; continue; }
			if (j < leaf.size() && leaf[j] == '%') { re += "%"; i = j; continue; }
		}
		if (std::strchr(".^$|()[]{}*+?\\", c)) re += '\\';
		re += c;
	}
	return std::regex(re, std::regex::icase);
}

std::vector<Reference> findReferences(const std::string& s, bool sjis, const std::function<bool(const std::string&)>& known)
{
	static const char* exts[] = { ".wav", ".flac", ".png", ".bmp", ".tlg" };
	std::vector<Reference> refs;
	const auto start = charStarts(s, sjis);
	for (size_t i = 0; i < s.size(); ++i) {
		if (s[i] != '.' || !start[i]) continue;
		for (const char* e : exts) {
			const size_t n = std::strlen(e);
			if (i + n > s.size()) continue;
			bool match = true;
			for (size_t k = 1; k < n; ++k) if (std::tolower((unsigned char)s[i + k]) != e[k] || !start[i + k]) match = false;
			if (!match) continue;
			if (i + n < s.size() && start[i + n] && nameChar((unsigned char)s[i + n])) continue;
			size_t b = i;
			while (b > 0 && start[b - 1] && (unsigned char)s[b - 1] < 0x80 && patternChar((unsigned char)s[b - 1])) --b;
			while (b < i && s[b] == '.') ++b;
			if (b == i) continue;
			if (b > 0 && !start[b - 1]) continue;
			std::string leaf = lower(s.substr(b, i - b + n));
			// "e.g.title.png": the longest tail that names a file
			if (leaf.find('%') == std::string::npos && !known(leaf)) {
				for (size_t dot = leaf.find('.'); dot != std::string::npos && dot + 1 < leaf.size() - n; dot = leaf.find('.', dot + 1)) {
					if (known(leaf.substr(dot + 1))) { leaf = leaf.substr(dot + 1); break; }
				}
			}
			refs.push_back({ i, n, std::move(leaf) });
		}
	}
	return refs;
}

//---------------------------------------------------------------------------
// Conversion jobs
//---------------------------------------------------------------------------
struct Job {
	fs::path    source;
	std::string name;      // in data/
	std::string ext;       // lower case, with the dot
	bool        audio = false;
	bool        mask = false;      // the mask of a main/mask pair
	bool        rule = false;      // a transition's rule image (data/rule): its exact values count
	std::string params;            // what decides the output
	// results
	bool        ok = false;
	bool        skipped = false;   // nothing to do for this file (it is in its target format)
	bool        cached = false;
	std::string error;
	std::vector<std::pair<std::string, fs::path>> outputs;   // suffix+ext ("" ".tlg", "_m" ".png") -> file
	int         sourceRate = 0, outputRate = 0;
};

std::string cacheKey(const fs::path& file, const std::string& params, std::string& error)
{
	std::string hex;
	if (!sha256File(file, hex, error)) return "";
	Sha256 h;
	const std::string k = hex + "|" + params + "|" + KAGEX_RELEASE_VERSION;
	h.update(k.data(), k.size());
	return h.hex();
}

bool decodeFlac(const fs::path& file, krt::audio::Pcm& pcm, int& bits, std::string& error)
{
	std::string data;
	if (!krt::readFile(file, data)) { error = "Can't read " + krt::fromPath(file); return false; }
	drflac* f = drflac_open_memory(data.data(), data.size(), nullptr);
	if (!f) { error = "Not a FLAC file the decoder understands"; return false; }
	pcm.sampleRate = (int)f->sampleRate;
	pcm.channels = f->channels;
	bits = f->bitsPerSample;
	pcm.data.resize((size_t)f->totalPCMFrameCount * f->channels);
	const drflac_uint64 got = drflac_read_pcm_frames_f32(f, f->totalPCMFrameCount, pcm.data.data());
	pcm.data.resize((size_t)got * f->channels);
	drflac_close(f);
	if (got == 0) { error = "The FLAC file has no samples"; return false; }
	return true;
}

// Converts one file into dir (out.<ext>, out_m.png), per job.params
void convert(Job& j, const fs::path& dir, const Json& s)
{
	std::string err;
	if (j.audio) {
		namespace au = krt::audio;
		au::Pcm pcm;
		au::Info info;
		int bits = 16;
		if (j.ext == ".flac") {
			if (!decodeFlac(j.source, pcm, bits, err)) { j.error = err; return; }
		} else {
			if (!au::decode(j.source, pcm, info, err)) { j.error = err; return; }
			bits = info.bitsPerSample;
		}
		j.sourceRate = pcm.sampleRate;
		const std::string to = str(s, "media.audio.convert");
		au::EncodeOptions eo;
		std::string ext;
		if (to == "opus") {
			eo.format = au::Format::Opus;
			eo.opusBitrateKbps = std::stoi(j.params.substr(j.params.find("kbps=") + 5));
			ext = ".opus";
			j.outputRate = 48000;
		} else if (to == "vorbis") {
			eo.format = au::Format::Vorbis;
			eo.vorbisQuality = (float)at(s, "media.audio.vorbisQuality").asInt(5) / 10.0f;
			ext = ".ogg";
			j.outputRate = pcm.sampleRate;
		} else {
			eo.format = au::Format::Wav;
			eo.wavBits = bits > 16 ? 24 : 16;
			ext = ".wav";
			j.outputRate = pcm.sampleRate;
		}
		const fs::path out = dir / ("out" + ext);
		if (!au::encode(pcm, out, eo, nullptr, err)) { j.error = err; return; }
		j.outputs.push_back({ ext, out });
		j.ok = true;
		return;
	}
	namespace im = krt::image;
	im::Image img;
	im::LoadInfo li;
	if (!im::load(j.source, img, err, &li)) { j.error = err; return; }
	const bool alpha = im::hasTransparency(img);
	std::string target = alpha ? str(s, "media.images.alpha") : str(s, "media.images.opaque");
	// masks of main/mask pairs and rule images stay lossless: a rule's values are each pixel's
	// timing (universal, imagewipe) or its timing, speed and direction (3duniversal), which
	// JPEG's artifacts would scatter
	if ((j.mask || j.rule) && (target == "jpeg" || target == "jpeg-mask")) target = "tlg6";
	if (target == "keep") { j.skipped = true; return; }
	const im::Format have = li.format;
	if ((target == "tlg6" && have == im::Format::Tlg6) || (target == "tlg5" && have == im::Format::Tlg5) || (target == "png" && have == im::Format::Png)) {
		j.skipped = true;
		return;
	}
	im::SaveOptions so;
	so.jpegQuality = (int)at(s, "media.images.jpegQuality").asInt(90);
	so.withAlpha = alpha;
	if (target == "jpeg-mask" || target == "jpeg") {
		so.withAlpha = false;
		const fs::path out = dir / "out.jpg";
		if (!im::save(out, img, im::Format::Jpeg, so, err)) { j.error = err; return; }
		j.outputs.push_back({ ".jpg", out });
		if (target == "jpeg-mask") {
			const im::Image mask = im::extractMask(img);
			im::SaveOptions mo;
			mo.withAlpha = false;
			mo.grayscale = true;
			const fs::path mout = dir / "out_m.png";
			if (!im::save(mout, mask, im::Format::Png, mo, err)) { j.error = err; return; }
			j.outputs.push_back({ "_m.png", mout });
		}
		j.ok = true;
		return;
	}
	const im::Format f = target == "tlg5" ? im::Format::Tlg5 : target == "png" ? im::Format::Png : im::Format::Tlg6;
	const std::string ext = f == im::Format::Png ? ".png" : ".tlg";
	const fs::path out = dir / ("out" + ext);
	if (!im::save(out, img, f, so, err)) { j.error = err; return; }
	j.outputs.push_back({ ext, out });
	j.ok = true;
}

// Runs one job through the cache
void runJob(Job& j, const Json& s, const fs::path& cache)
{
	std::string err;
	const std::string key = cacheKey(j.source, j.params, err);
	if (key.empty()) { j.error = err; return; }
	const fs::path entry = cache / key.substr(0, 2) / key;
	std::error_code ec;
	std::string manifest;
	if (krt::readFile(entry / "done", manifest)) {
		// "skipped", or one output per line: <suffix+ext>\t<file>, then rate lines
		if (manifest == "skipped\n") { j.skipped = true; return; }
		size_t pos = 0;
		while (pos < manifest.size()) {
			size_t end = manifest.find('\n', pos);
			if (end == std::string::npos) end = manifest.size();
			const std::string line = manifest.substr(pos, end - pos);
			pos = end + 1;
			const size_t tab = line.find('\t');
			if (tab == std::string::npos) continue;
			const std::string k = line.substr(0, tab), v = line.substr(tab + 1);
			if (k == "rate") { const size_t sp = v.find(' '); j.sourceRate = std::stoi(v.substr(0, sp)); j.outputRate = std::stoi(v.substr(sp + 1)); }
			else j.outputs.push_back({ k, entry / krt::toPath(v) });
		}
		bool all = !j.outputs.empty();
		for (const auto& o : j.outputs) if (!fs::is_regular_file(o.second, ec)) all = false;
		if (all) { j.ok = j.cached = true; return; }
		j.outputs.clear();
	}
	const fs::path tmp = cache / key.substr(0, 2) / (key + ".part" + std::to_string(std::hash<std::thread::id>()(std::this_thread::get_id()) % 100000));
	fs::remove_all(tmp, ec);
	fs::create_directories(tmp, ec);
	convert(j, tmp, s);
	if (!j.ok && !j.skipped) { fs::remove_all(tmp, ec); return; }
	std::string m;
	if (j.skipped) m = "skipped\n";
	for (auto& o : j.outputs) {
		m += o.first + "\t" + krt::fromPath(o.second.filename()) + "\n";
		o.second = entry / o.second.filename();
	}
	if (j.audio) m += "rate\t" + std::to_string(j.sourceRate) + " " + std::to_string(j.outputRate) + "\n";
	krt::writeFile(tmp / "done", m);
	fs::remove_all(entry, ec);
	fs::rename(tmp, entry, ec);
	if (ec) {
		// another build got there first: use its entry
		fs::remove_all(tmp, ec);
	}
}

// Replaces a staged file (a hard link to the source) without writing to it
bool replaceStaged(const fs::path& staged, const fs::path& from, std::string& error)
{
	std::error_code ec;
	fs::remove(staged, ec);
	fs::copy_file(from, staged, fs::copy_options::overwrite_existing, ec);
	if (ec) { error = "Can't write " + krt::fromPath(staged) + ": " + ec.message(); return false; }
	return true;
}

} // namespace

bool frameworkPlaysOpus(const fs::path& framework)
{
	std::string text;
	if (!krt::readFile(framework / "BGM.tjs", text)) return true;   // not KAGEX's framework: can't tell
	return text.find("\"opus\"") != std::string::npos;
}

bool frameworkFindsConvertedImages(const fs::path& framework)
{
	std::string text;
	if (!krt::readFile(framework / "MessageLayer.tjs", text)) return true;   // not KAGEX's framework: can't tell
	const size_t at = text.find("function getExistName");
	if (at == std::string::npos) return true;
	const size_t next = text.find("function ", at + 1);
	const std::string body = text.substr(at, next == std::string::npos ? std::string::npos : next - at);
	return body.find("global.Layer.SupportedExtensions") != std::string::npos || body.find("\".tlg\"") != std::string::npos;
}

bool frameworkSupportsSigning(const fs::path& framework)
{
	std::error_code ec;
	return fs::is_regular_file(framework / "SignatureCheck.tjs", ec);
}

bool frameworkHidesNamesInXp3(const fs::path& framework)
{
	std::string init, check, boot;
	if (!krt::readFile(framework / "Initialize.tjs", init) || !krt::readFile(framework / "SignatureCheck.tjs", check) ||
	    !krt::readFile(framework / "hashed-bootstrap.tjs", boot)) return false;
	return boot.find("kagexHashedLayout") != std::string::npos && init.find("KAGMountHashedArchive") != std::string::npos &&
	       check.find("KAGSignedUseHashedArchive") != std::string::npos;
}

bool frameworkFindsSplitArchives(const fs::path& framework)
{
	std::string init;
	return krt::readFile(framework / "Initialize.tjs", init) && init.find("KAGArchivePath") != std::string::npos;
}

bool convertMedia(const Json& s, const fs::path& stage, krt::Progress& progress, MediaResult& result, std::string& error)
{
	const std::string audioTo = str(s, "media.audio.convert");
	const bool imagesKept = str(s, "media.images.opaque") == "keep" && str(s, "media.images.alpha") == "keep";
	const bool rewrite = str(s, "media.references") == "rewrite";
	std::error_code ec;

	// the staged files
	struct File { std::string name, leaf, ext; fs::path path; };
	std::vector<File> files;
	std::map<std::string, std::string> byLeaf;   // lower leaf -> name
	for (fs::recursive_directory_iterator it(stage, ec), end; it != end; it.increment(ec)) {
		if (ec || !it->is_regular_file(ec)) continue;
		File f;
		f.name = krt::fromPath(fs::relative(it->path(), stage, ec));
		f.leaf = leafOf(f.name);
		f.ext = extOf(f.leaf);
		f.path = it->path();
		byLeaf[lower(f.leaf)] = f.name;
		files.push_back(std::move(f));
	}
	std::sort(files.begin(), files.end(), [](const File& a, const File& b) { return a.name < b.name; });
	std::set<std::string> imageStems;
	for (const auto& f : files) if (isImageSource(f.ext) || f.ext == ".jpg" || f.ext == ".jpeg") imageStems.insert(lower(stemOf(f.leaf)));

	// names the scripts write with their extension
	std::map<std::string, std::vector<std::string>> referencedBy;   // lower leaf -> scripts
	std::vector<const File*> scripts;
	for (const auto& f : files) {
		if (!isScript(f.ext)) continue;
		std::string raw;
		if (!krt::readFile(f.path, raw)) continue;
		const ScriptText t = readScript(raw);
		const bool sjis = !t.utf16 && !validUtf8(t.text);
		bool any = false;
		const auto known = [&](const std::string& l) { return byLeaf.count(l) > 0; };
		for (const auto& r : findReferences(t.text, sjis, known)) {
			if (r.pattern()) {
				const std::regex re = patternRegex(r.leaf);
				for (const auto& [leaf, name] : byLeaf) {
					if (!std::regex_match(leaf, re)) continue;
					referencedBy[leaf].push_back(f.name);
					any = true;
				}
				continue;
			}
			if (!byLeaf.count(r.leaf)) continue;
			referencedBy[r.leaf].push_back(f.name);
			any = true;
		}
		if (any) scripts.push_back(&f);
	}

	// files Effekseer effects name: an effect can't be rewritten, so they always keep their format
	// (by leaf, as the runtime also looks a name up on the auto path)
	std::set<std::string> forEffects;   // lower leaves
	for (const auto& f : files) {
		if (!isEffect(f.ext)) continue;
		std::string raw;
		if (!krt::readFile(f.path, raw)) continue;
		for (const auto& name : effectResources(raw)) forEffects.insert(lower(leafOf(name)));
	}

	// the jobs
	std::vector<Job> jobs;
	for (const auto& f : files) {
		Job j;
		j.source = f.path;
		j.name = f.name;
		j.ext = f.ext;
		const std::string leaf = lower(f.leaf);
		const bool referenced = referencedBy.count(leaf) > 0;
		if (isAudioSource(f.ext)) {
			if (audioTo == "keep" && f.ext == ".wav") continue;
			if (forEffects.count(leaf)) { ++result.keptForEffects; continue; }
			// FLAC can't be played, so it is converted (and its references rewritten) either way
			if (referenced && !rewrite && f.ext != ".flac") { ++result.keptByReference; continue; }
			j.audio = true;
			if (audioTo == "opus") {
				const size_t sl = f.name.find('/');
				const std::string folder = sl == std::string::npos ? std::string() : f.name.substr(0, sl);
				const Json& kbps = at(s, "media.audio.opusKbps");
				long long rate = kbps.has(folder) ? kbps[folder].asInt() : kbps.has("*") ? kbps["*"].asInt() : 96;
				j.params = "audio|opus|kbps=" + std::to_string(rate);
			} else if (audioTo == "vorbis") {
				j.params = "audio|vorbis|q=" + std::to_string(at(s, "media.audio.vorbisQuality").asInt(5));
			} else {
				j.params = "audio|wav";
			}
		} else if (isImageSource(f.ext) && !imagesKept) {
			if (forEffects.count(leaf)) { ++result.keptForEffects; continue; }
			if (referenced && !rewrite) { ++result.keptByReference; continue; }
			const std::string stem = lower(stemOf(f.leaf));
			j.mask = stem.size() > 2 && stem.compare(stem.size() - 2, 2, "_m") == 0 && imageStems.count(stem.substr(0, stem.size() - 2));
			const size_t sl = f.name.find('/');
			j.rule = sl != std::string::npos && lower(f.name.substr(0, sl)) == "rule";
			j.params = "image|opaque=" + str(s, "media.images.opaque") + "|alpha=" + str(s, "media.images.alpha") +
			           "|q=" + std::to_string(at(s, "media.images.jpegQuality").asInt(90)) + "|mask=" + (j.mask ? "1" : "0") +
			           (j.rule ? "|rule=1" : "");
		} else {
			continue;
		}
		jobs.push_back(std::move(j));
	}
	if (result.keptByReference)
		result.notes.push_back(std::to_string(result.keptByReference) + " files weren't converted because scripts name them with their extension (Media > Names with extensions)");
	if (result.keptForEffects)
		result.notes.push_back(std::to_string(result.keptForEffects) + " files weren't converted because Effekseer effects use them");
	if (jobs.empty()) return true;

	// convert, in parallel
	const fs::path cache = cacheDir() / "media";
	fs::create_directories(cache, ec);
	std::atomic<size_t> next{ 0 }, done{ 0 };
	const unsigned workers = std::max(1u, std::min<unsigned>(std::thread::hardware_concurrency(), 16));
	std::vector<std::thread> threads;
	for (unsigned w = 0; w < workers; ++w) {
		threads.emplace_back([&]() {
			for (;;) {
				const size_t i = next++;
				if (i >= jobs.size() || progress.canceled()) break;
				try {
					runJob(jobs[i], s, cache);
				} catch (const std::exception& e) {
					jobs[i].error = e.what();
				}
				++done;
			}
		});
	}
	while (done < jobs.size()) {
		progress.progress((double)done / jobs.size(), "Converting media (" + std::to_string(done.load()) + " of " + std::to_string(jobs.size()) + ")");
		if (progress.canceled()) break;
		std::this_thread::sleep_for(std::chrono::milliseconds(200));
	}
	for (auto& t : threads) t.join();
	if (progress.canceled()) { error = "Canceled"; return false; }

	// put the results in place of the sources, first come first served for each name. Files of the
	// same name in different folders (a language's folder, lang/<code>/, standing in for
	// image/'s) become the same new name, as they had the same name before
	std::map<std::string, std::string> renamed;   // lower old leaf -> new leaf (for the scripts)
	std::map<std::string, int> taken;             // lower leaves in the stage after this, and how many have each
	std::map<std::string, std::map<std::string, int>> made;   // lower new leaf -> the lower old leaves made into it, how many each
	for (const auto& f : files) ++taken[lower(f.leaf)];
	int failed = 0;
	for (auto& j : jobs) {
		if (j.skipped) continue;
		if (!j.ok) {
			++failed;
			if (failed <= 20) result.notes.push_back(j.name + " was kept as it is: " + j.error);
			continue;
		}
		if (j.cached) ++result.fromCache;
		const std::string leaf = leafOf(j.name), stem = stemOf(leaf);
		const fs::path dir = j.source.parent_path();
		// names the outputs would take, which no other file may have (but one converted from a
		// file of the same name)
		bool clash = false;
		for (const auto& o : j.outputs) {
			const std::string nl = lower(stem + o.first);
			if (nl == lower(leaf)) continue;
			const auto t = taken.find(nl);
			const int same = made.count(nl) && made[nl].count(lower(leaf)) ? made[nl][lower(leaf)] : 0;
			if (t != taken.end() && t->second > same) clash = true;
		}
		if (clash) {
			result.notes.push_back(j.name + " was kept as it is: another file already has the name it would get");
			continue;
		}
		const uint64_t before = fs::file_size(j.source, ec);
		fs::remove(j.source, ec);
		if (--taken[lower(leaf)] <= 0) taken.erase(lower(leaf));
		uint64_t after = 0;
		for (const auto& o : j.outputs) {
			const fs::path to = dir / krt::toPath(stem + o.first);
			if (!replaceStaged(to, o.second, error)) return false;
			after += fs::file_size(to, ec);
			++taken[lower(stem + o.first)];
			++made[lower(stem + o.first)][lower(leaf)];
		}
		result.bytesBefore += before;
		result.bytesAfter += after;
		renamed[lower(leaf)] = stem + j.outputs.front().first;
		(j.audio ? result.sounds : result.images)++;

		// loop points go along, at the new sample rate
		const fs::path sli = dir / krt::toPath(leaf + ".sli");
		if (j.audio && fs::is_regular_file(sli, ec)) {
			std::string text, perr;
			krt::loop::Sli data;
			if (krt::readFile(sli, text) && krt::loop::parse(text, data, perr)) {
				if (j.sourceRate && j.outputRate && j.sourceRate != j.outputRate) krt::loop::rescale(data, j.sourceRate, j.outputRate);
				fs::remove(sli, ec);
				const fs::path newSli = dir / krt::toPath(stem + j.outputs.front().first + ".sli");
				if (!krt::writeFile(newSli, krt::loop::write(data))) { error = "Can't write " + krt::fromPath(newSli); return false; }
			} else {
				result.notes.push_back(krt::fromPath(sli.filename()) + " couldn't be read (" + perr + "); it was left as it is");
			}
		}
	}
	if (failed > 20) result.notes.push_back(std::to_string(failed - 20) + " more files were kept as they are");

	// rewrite the names in the scripts
	if (!renamed.empty()) {
		for (const File* f : scripts) {
			std::string raw;
			if (!krt::readFile(f->path, raw)) continue;
			ScriptText t = readScript(raw);
			const bool sjis = !t.utf16 && !validUtf8(t.text);
			auto refs = findReferences(t.text, sjis, [&](const std::string& l) { return byLeaf.count(l) > 0; });
			bool changed = false;
			// from the end, so the positions stay right
			for (auto it = refs.rbegin(); it != refs.rend(); ++it) {
				if (!rewrite && extOf(it->leaf) != ".flac") continue;
				std::string newExt;
				if (it->pattern()) {
					// every file the pattern names must have become the same type
					const std::regex re = patternRegex(it->leaf);
					bool mixed = false;
					for (const auto& [leaf, name] : byLeaf) {
						if (!std::regex_match(leaf, re)) continue;
						auto m = renamed.find(leaf);
						const std::string e = m == renamed.end() ? extOf(leaf) : extOf(m->second);
						if (newExt.empty()) newExt = e;
						else if (e != newExt) mixed = true;
					}
					if (mixed) {
						result.notes.push_back(f->name + ": the files \"" + it->leaf + "\" names didn't all become the same type, so it wasn't changed");
						continue;
					}
					if (newExt.empty() || newExt == extOf(it->leaf)) continue;
				} else {
					auto m = renamed.find(it->leaf);
					if (m == renamed.end()) continue;
					newExt = m->second.substr(stemOf(m->second).size());
				}
				t.text.replace(it->extAt, it->extLen, newExt);
				changed = true;
			}
			if (!changed) continue;
			const std::string out = t.utf16 ? utf8ToUtf16(t.text) : t.text;
			std::error_code e2;
			fs::remove(f->path, e2);   // a hard link to the source: not written to
			if (!krt::writeFile(f->path, out)) { error = "Can't write " + krt::fromPath(f->path); return false; }
			++result.rewrittenScripts;
		}
	}
	return true;
}

} // namespace kr
