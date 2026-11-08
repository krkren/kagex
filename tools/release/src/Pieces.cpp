#include "Pieces.h"

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <cstring>
#include <map>
#include <set>

#include "Archive.h"
#include "Host.h"
#include "Layered.h"
#include "krt/app/Progress.h"
#include "krt/app/Text.h"
#include "krt/image/Image.h"

namespace fs = std::filesystem;

namespace kr {

namespace {

// a picture that differs from its base in more than this share of its area is kept whole
constexpr double kMaxShare = 0.5;

std::string lowered(std::string s)
{
	for (auto& c : s) c = (char)std::tolower((unsigned char)c);
	return s;
}

bool isImageExt(const std::string& e)
{
	return e == ".png" || e == ".bmp" || e == ".tlg" || e == ".tlg5" || e == ".tlg6" || e == ".jpg" || e == ".jpeg" || e == ".webp";
}
bool isLosslessExt(const std::string& e) { return e == ".png" || e == ".bmp" || e == ".tlg" || e == ".tlg5" || e == ".tlg6"; }

std::string stemOf(const fs::path& p) { return krt::fromPath(p.stem()); }
std::string extOf(const fs::path& p) { return lowered(krt::fromPath(p.extension())); }

// the first column of a tab-separated table's lines (# comments and empty lines left out), in lower case
std::set<std::string> firstColumn(const fs::path& file)
{
	std::set<std::string> out;
	std::string text;
	if (!krt::readFile(file, text)) return out;
	if (text.compare(0, 3, "\xEF\xBB\xBF") == 0) text.erase(0, 3);
	size_t pos = 0;
	while (pos < text.size()) {
		size_t nl = text.find('\n', pos);
		if (nl == std::string::npos) nl = text.size();
		std::string line = text.substr(pos, nl - pos);
		pos = nl + 1;
		if (!line.empty() && line.back() == '\r') line.pop_back();
		if (line.empty() || line[0] == '#') continue;
		const std::string name = krt::trim(line.substr(0, line.find('\t')));
		if (!name.empty()) out.insert(lowered(name));
	}
	return out;
}

struct Pic {
	fs::path path;
	std::string leaf, stem, hash;
};

bool sameText(const std::string& a, const std::string& b) { return lowered(a) == lowered(b); }

// whether a folder (relative to the stage) is a CG folder: one of its parts is a listed name
bool isCgFolder(const fs::path& rel, const std::set<std::string>& names)
{
	for (const auto& part : rel) if (names.count(lowered(krt::fromPath(part)))) return true;
	return false;
}

// what the piece of a picture is saved as: its own format, which the engine tells by the extension
bool pieceFormat(const fs::path& file, krt::image::Format& f)
{
	std::string head;
	if (!krt::readFile(file, head)) return false;
	f = krt::image::detect((const uint8_t*)head.data(), head.size());
	return f == krt::image::Format::Png || f == krt::image::Format::Bmp || f == krt::image::Format::Tlg5 || f == krt::image::Format::Tlg6;
}

} // namespace

bool differingRect(const krt::image::Image& a, const krt::image::Image& b, int& x, int& y, int& w, int& h)
{
	int l = a.width, t = a.height, r = -1, btm = -1;
	for (int yy = 0; yy < a.height; ++yy) {
		const uint32_t* pa = (const uint32_t*)a.row(yy);
		const uint32_t* pb = (const uint32_t*)b.row(yy);
		if (std::memcmp(pa, pb, (size_t)a.width * 4) == 0) continue;
		int first = 0, last = a.width - 1;
		while (pa[first] == pb[first]) ++first;
		while (pa[last] == pb[last]) --last;
		l = std::min(l, first);
		r = std::max(r, last);
		t = std::min(t, yy);
		btm = yy;
	}
	if (r < 0) return false;
	x = l, y = t, w = r - l + 1, h = btm - t + 1;
	return true;
}

bool frameworkDrawsCgPieces(const fs::path& framework)
{
	std::string text;
	return krt::readFile(framework / "CGVariations.tjs", text) && text.find("cgpieces.txt") != std::string::npos;
}

bool makeCgPieces(const Json& settings, const fs::path& stage, krt::Progress& pr, PiecesResult& result, std::string& error)
{
	std::set<std::string> folders;
	for (const auto& f : at(settings, "media.images.cgPieces").elements())
		if (f.isStr() && !f.asStr().empty()) folders.insert(lowered(f.asStr()));
	if (folders.empty()) return true;
	const std::string opaque = str(settings, "media.images.opaque"), alpha = str(settings, "media.images.alpha");

	// every picture's name, the tables that name pictures, and the CG folders' pictures
	std::map<std::string, int> stems;          // lower case -> pictures of that name in the game
	std::set<std::string> listed;              // names cgvariations.txt or a game's cgpieces.txt has
	fs::path ownTable;                         // the game's own cgpieces.txt
	std::map<fs::path, std::vector<Pic>> byFolder;
	std::error_code ec;
	for (fs::recursive_directory_iterator it(stage, ec), end; it != end; it.increment(ec)) {
		if (ec) break;
		if (!it->is_regular_file(ec)) continue;
		const fs::path& p = it->path();
		const std::string leaf = lowered(krt::fromPath(p.filename()));
		if (leaf == "cgvariations.txt") { for (const auto& n : firstColumn(p)) listed.insert(n); continue; }
		if (leaf == "cgpieces.txt") {
			for (const auto& n : firstColumn(p)) listed.insert(n);
			if (ownTable.empty()) ownTable = p;
			continue;
		}
		const std::string e = extOf(p);
		if (!isImageExt(e)) continue;
		++stems[lowered(stemOf(p))];
		const fs::path rel = p.parent_path().lexically_relative(stage);
		if (!isLosslessExt(e) || rel.empty() || sameText(krt::fromPath(*rel.begin()), "lang") || !isCgFolder(rel, folders)) continue;
		byFolder[p.parent_path()].push_back(Pic{ p, krt::fromPath(p.filename()), stemOf(p), {} });
	}

	const fs::path cache = cacheDir() / "pieces";
	fs::create_directories(cache, ec);
	std::string lines;
	size_t done = 0, total = 0;
	for (const auto& [dir, pics] : byFolder) total += pics.size();
	for (auto& [dir, pics] : byFolder) {
		++result.folders;
		std::sort(pics.begin(), pics.end(), [](const Pic& a, const Pic& b) {
			const std::string la = lowered(a.leaf), lb = lowered(b.leaf);
			return la != lb ? la < lb : a.leaf < b.leaf;
		});
		// what can take part: a name of its own, not a mask nor masked, not a layer picture
		std::set<std::string> here;
		for (const auto& p : pics) here.insert(lowered(p.stem));
		auto eligible = [&](const Pic& p) {
			const std::string s = lowered(p.stem);
			if (stems[s] != 1 || listed.count(s)) return false;
			if (s.size() > 2 && s.compare(s.size() - 2, 2, "_m") == 0 && here.count(s.substr(0, s.size() - 2))) return false;
			if (!krt::image::findMaskFile(p.path).empty()) return false;
			const size_t us = p.stem.rfind('_');
			if (us != std::string::npos && us + 1 < p.stem.size() &&
			    std::all_of(p.stem.begin() + us + 1, p.stem.end(), [](char c) { return std::isdigit((unsigned char)c) != 0; })) {
				const fs::path txt = dir / krt::toPath(p.stem.substr(0, us) + ".txt");
				if (fs::exists(txt, ec) && isLayerStructure(txt)) return false;
			}
			return true;
		};

		const Pic* base = nullptr;
		krt::image::Image baseImg;
		bool baseLoaded = false, baseAlpha = false;
		for (auto& pic : pics) {
			if (pr.canceled()) { error = "Canceled"; return false; }
			pr.progress(total ? (double)done++ / total : 0, "Comparing CG variations: " + pic.leaf);
			if (!eligible(pic)) continue;
			++result.pictures;
			if (!sha256File(pic.path, pic.hash, error)) return false;
			if (!base) { base = &pic; baseLoaded = false; continue; }

			// the answer for this pair: "whole", or "<x> <y> <w> <h>" with the piece's file beside it
			Sha256 kh;
			const std::string k = base->hash + "|" + pic.hash + "|" + opaque + "|" + alpha + "|" + KAGEX_RELEASE_VERSION;   // JPEG keeps them whole
			kh.update(k.data(), k.size());
			const std::string key = kh.hex();
			const fs::path answerFile = cache / krt::toPath(key + ".txt");
			const fs::path pieceFile = cache / krt::toPath(key + krt::fromPath(pic.path.extension()));
			std::string answer;
			const bool cached = krt::readFile(answerFile, answer) &&
			                    (answer.rfind("whole", 0) == 0 || answer.rfind("same", 0) == 0 || fs::exists(pieceFile, ec));
			if (cached) ++result.fromCache;
			else {
				if (!baseLoaded) {
					krt::image::LoadInfo bi;
					if (!krt::image::load(base->path, baseImg, error, &bi)) { error = base->leaf + ": " + error; return false; }
					baseAlpha = bi.hasAlpha;
					baseLoaded = true;
				}
				krt::image::Image img;
				krt::image::LoadInfo info;
				if (!krt::image::load(pic.path, img, error, &info)) { error = pic.leaf + ": " + error; return false; }
				answer = "whole";
				krt::image::Format f;
				// one that becomes JPEG is kept whole, as is one of another size or one that differs a lot
				const bool transparent = krt::image::hasTransparency(img) || krt::image::hasTransparency(baseImg);
				const bool jpeg = transparent ? alpha == "jpeg-mask" : opaque == "jpeg";
				int x = 0, y = 0, w = 1, h = 1;
				if (!jpeg && img.width == baseImg.width && img.height == baseImg.height && pieceFormat(pic.path, f)) {
					if (!differingRect(baseImg, img, x, y, w, h)) x = y = 0, w = h = 1;   // the same picture: one pixel
					if ((double)w * h <= kMaxShare * img.width * img.height) {
						krt::image::Image part;
						part.width = w, part.height = h;
						part.bgra.resize((size_t)w * h * 4);
						for (int yy = 0; yy < h; ++yy) std::memcpy(part.row(yy), img.row(y + yy) + (size_t)x * 4, (size_t)w * 4);
						krt::image::SaveOptions so;
						so.withAlpha = info.hasAlpha || baseAlpha || krt::image::hasTransparency(part);
						if (!krt::image::save(pieceFile, part, f, so, error)) { error = pic.leaf + ": " + error; return false; }
						// only where it's smaller than the picture
						if (fs::file_size(pieceFile, ec) < fs::file_size(pic.path, ec)) answer = std::to_string(x) + " " + std::to_string(y) + " " + std::to_string(w) + " " + std::to_string(h);
						else answer = "same", fs::remove(pieceFile, ec);
					}
				}
				krt::writeFile(answerFile, answer);
				if (answer == "whole") { base = &pic; baseImg = std::move(img); baseAlpha = info.hasAlpha; baseLoaded = true; continue; }
			}
			if (answer.rfind("whole", 0) == 0) { base = &pic; baseLoaded = false; continue; }
			if (answer.rfind("same", 0) == 0) continue;   // like its base, but no smaller as a piece: kept whole
			int x = 0, y = 0, w = 0, h = 0;
			if (std::sscanf(answer.c_str(), "%d %d %d %d", &x, &y, &w, &h) != 4) continue;
			const uint64_t before = fs::file_size(pic.path, ec);
			fs::remove(pic.path, ec);   // a hard link to the game's own: replaced, never written to
			fs::copy_file(pieceFile, pic.path, ec);
			if (ec) { error = "Can't write " + krt::fromPath(pic.path) + ": " + ec.message(); return false; }
			result.bytesBefore += before;
			result.bytesAfter += fs::file_size(pic.path, ec);
			++result.pieces;
			lines += pic.stem + "\t" + base->stem + "\t" + std::to_string(x) + "\t" + std::to_string(y) + "\n";
		}
	}
	if (lines.empty()) return true;

	// the table, after the game's own lines when it has one
	fs::path table = ownTable.empty() ? stage / "cgpieces.txt" : ownTable;
	std::string text;
	if (!ownTable.empty()) {
		krt::readFile(ownTable, text);
		if (text.compare(0, 3, "\xEF\xBB\xBF") == 0) text.erase(0, 3);
		if (!text.empty() && text.back() != '\n') text += "\n";
	}
	text = "\xEF\xBB\xBF" + text + "# kagex-release " KAGEX_RELEASE_VERSION ": pictures kept as the rectangle that differs from another (name, base, x, y)\n" + lines;
	fs::remove(table, ec);
	if (!krt::writeFile(table, text)) { error = "Can't write " + krt::fromPath(table); return false; }
	return true;
}

} // namespace kr
