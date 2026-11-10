#include "Icons.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>

#include "krt/image/Image.h"

namespace kr {

namespace {
void be32(std::string& s, uint32_t v) { for (int i = 3; i >= 0; --i) s += (char)((v >> (8 * i)) & 0xff); }
void le16(std::string& s, uint16_t v) { s += (char)(v & 0xff); s += (char)(v >> 8); }
void le32(std::string& s, uint32_t v) { for (int i = 0; i < 4; ++i) s += (char)((v >> (8 * i)) & 0xff); }
}

namespace {

uint16_t rd16(const std::string& d, size_t at) { return at + 2 <= d.size() ? (uint16_t)((uint8_t)d[at] | ((uint8_t)d[at + 1] << 8)) : 0; }
uint32_t rd32(const std::string& d, size_t at) { return at + 4 <= d.size() ? (uint32_t)rd16(d, at) | ((uint32_t)rd16(d, at + 2) << 16) : 0; }

// One icon image of an .ico or an executable's resources: a PNG, or a DIB (BITMAPINFOHEADER, the
// colour bitmap, then the 1-bit AND mask; the height counts both)
bool decodeIconImage(const std::string& d, krt::image::Image& out, std::string& error)
{
	if (d.size() >= 8 && d.compare(0, 8, "\x89PNG\r\n\x1a\n", 8) == 0)
		return krt::image::loadMemory((const uint8_t*)d.data(), d.size(), out, error);
	const uint32_t hs = rd32(d, 0);
	const int w = (int)rd32(d, 4), h = (int)rd32(d, 8) / 2, bpp = rd16(d, 14);
	if (hs < 40 || w <= 0 || h <= 0 || w > 1024 || h > 1024 || rd32(d, 16) != 0) { error = "an icon image this tool can't read"; return false; }
	size_t at = hs;
	std::vector<uint32_t> palette;
	if (bpp <= 8) {
		uint32_t n = rd32(d, 32);
		if (n == 0) n = 1u << bpp;
		for (uint32_t i = 0; i < n; ++i, at += 4) palette.push_back(rd32(d, at));
	}
	const size_t stride = ((size_t)w * bpp + 31) / 32 * 4, mstride = ((size_t)w + 31) / 32 * 4;
	const size_t xorAt = at, andAt = at + stride * h;
	if (andAt > d.size()) { error = "an icon image cut short"; return false; }
	out.width = w;
	out.height = h;
	out.bgra.assign((size_t)w * h * 4, 0);
	bool anyAlpha = false;
	for (int y = 0; y < h; ++y) {
		const size_t row = xorAt + stride * (h - 1 - y);   // bottom-up
		for (int x = 0; x < w; ++x) {
			uint8_t* p = &out.bgra[((size_t)y * w + x) * 4];
			uint32_t c = 0;
			if (bpp == 32) { c = rd32(d, row + x * 4); p[3] = (uint8_t)(c >> 24); anyAlpha |= p[3] != 0; }
			else if (bpp == 24) c = (uint8_t)d[row + x * 3] | ((uint8_t)d[row + x * 3 + 1] << 8) | ((uint8_t)d[row + x * 3 + 2] << 16);
			else {
				const size_t bit = (size_t)x * bpp;
				const int v = ((uint8_t)d[row + bit / 8] >> (8 - bpp - (int)(bit % 8))) & ((1 << bpp) - 1);
				c = v < (int)palette.size() ? palette[v] : 0;
			}
			p[0] = (uint8_t)c; p[1] = (uint8_t)(c >> 8); p[2] = (uint8_t)(c >> 16);
		}
	}
	// without alpha of its own, the AND mask says what's transparent
	if (!anyAlpha)
		for (int y = 0; y < h; ++y) {
			const size_t row = andAt + mstride * (h - 1 - y);
			for (int x = 0; x < w; ++x) {
				const bool clear = row + x / 8 < d.size() && (((uint8_t)d[row + x / 8] >> (7 - x % 8)) & 1);
				out.bgra[((size_t)y * w + x) * 4 + 3] = clear ? 0 : 255;
			}
		}
	return true;
}

// The largest image of an icon group: entries of (width, height, bit count, size, where); width
// and height 0 mean 256
struct IconEntry { int w, h, bpp; uint32_t size, where; };
size_t largest(const std::vector<IconEntry>& e)
{
	size_t best = 0;
	for (size_t i = 1; i < e.size(); ++i) {
		const long a = (long)e[i].w * e[i].h, b = (long)e[best].w * e[best].h;
		if (a > b || (a == b && e[i].bpp > e[best].bpp)) best = i;
	}
	return best;
}

bool icoFile(const std::string& d, krt::image::Image& out, std::string& error)
{
	const int n = rd16(d, 4);
	if (rd16(d, 0) != 0 || rd16(d, 2) != 1 || n == 0) { error = "not an .ico file"; return false; }
	std::vector<IconEntry> e;
	for (int i = 0; i < n; ++i) {
		const size_t at = 6 + 16 * i;
		e.push_back({ (uint8_t)d[at] ? (uint8_t)d[at] : 256, (uint8_t)d[at + 1] ? (uint8_t)d[at + 1] : 256, rd16(d, at + 6), rd32(d, at + 8), rd32(d, at + 12) });
	}
	const IconEntry& b = e[largest(e)];
	if ((size_t)b.where + b.size > d.size()) { error = "an .ico cut short"; return false; }
	return decodeIconImage(d.substr(b.where, b.size), out, error);
}

// A Windows executable's icon (since 0.28.1, for a game brought from Windows Kirikiri): the first
// icon group of its resources, its largest image
bool exeIcon(const std::string& d, krt::image::Image& out, std::string& error)
{
	error = "no icon in the executable";
	if (d.size() < 64 || d.compare(0, 2, "MZ") != 0) { error = "not a Windows executable"; return false; }
	const size_t pe = rd32(d, 0x3c);
	if (pe + 24 > d.size() || d.compare(pe, 4, std::string("PE\0\0", 4)) != 0) { error = "not a Windows executable"; return false; }
	const int sections = rd16(d, pe + 6);
	const size_t opt = pe + 24, optSize = rd16(d, pe + 20);
	const bool plus = rd16(d, opt) == 0x20b;
	const uint32_t resRva = rd32(d, opt + (plus ? 112 : 96) + 2 * 8);
	if (resRva == 0) return false;
	struct Sec { uint32_t va, vsize, raw, rsize; };
	std::vector<Sec> secs;
	for (int i = 0; i < sections; ++i) {
		const size_t at = opt + optSize + 40 * i;
		secs.push_back({ rd32(d, at + 12), rd32(d, at + 8), rd32(d, at + 20), rd32(d, at + 16) });
	}
	auto off = [&](uint32_t rva) -> size_t {
		for (const Sec& s : secs)
			if (rva >= s.va && rva < s.va + std::max(s.vsize, s.rsize)) return (size_t)s.raw + (rva - s.va);
		return std::string::npos;
	};
	const size_t root = off(resRva);
	if (root == std::string::npos) return false;
	// a directory's entries: (id or name, offset with the subdirectory bit)
	auto entries = [&](size_t dir) {
		std::vector<std::pair<uint32_t, uint32_t>> v;
		const int n = rd16(d, dir + 12) + rd16(d, dir + 14);
		for (int i = 0; i < n && i < 4096; ++i) v.push_back({ rd32(d, dir + 16 + 8 * i), rd32(d, dir + 16 + 8 * i + 4) });
		return v;
	};
	// a resource's data: down the name and language levels to the first data entry
	auto data = [&](uint32_t entry) -> std::string {
		size_t at = root + (entry & 0x7fffffff);
		for (int level = 0; level < 2 && (entry & 0x80000000); ++level) {
			const auto sub = entries(at);
			if (sub.empty()) return std::string();
			entry = sub[0].second;
			at = root + (entry & 0x7fffffff);
		}
		const size_t where = off(rd32(d, at));
		const uint32_t size = rd32(d, at + 4);
		if (where == std::string::npos || where + size > d.size()) return std::string();
		return d.substr(where, size);
	};
	uint32_t groups = 0, icons = 0;
	for (const auto& e : entries(root)) {
		if (e.first == 14) groups = e.second;
		if (e.first == 3) icons = e.second;
	}
	if (!groups || !icons) return false;
	const auto groupList = entries(root + (groups & 0x7fffffff));
	if (groupList.empty()) return false;
	const std::string g = data(groupList[0].second);
	const int n = rd16(g, 4);
	std::vector<IconEntry> e;
	for (int i = 0; i < n; ++i) {
		const size_t at = 6 + 14 * i;
		if (at + 14 > g.size()) break;
		e.push_back({ (uint8_t)g[at] ? (uint8_t)g[at] : 256, (uint8_t)g[at + 1] ? (uint8_t)g[at + 1] : 256, rd16(g, at + 6), rd32(g, at + 8), rd16(g, at + 12) });
	}
	if (e.empty()) return false;
	const uint32_t id = e[largest(e)].where;
	for (const auto& icon : entries(root + (icons & 0x7fffffff)))
		if (icon.first == id) {
			const std::string img = data(icon.second);
			if (img.empty()) return false;
			return decodeIconImage(img, out, error);
		}
	return false;
}

} // namespace

bool IconSource::load(const std::filesystem::path& png, std::string& error)
{
	krt::image::Image img;
	std::string ext = png.extension().string();
	std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char c) { return (char)std::tolower(c); });
	if (ext == ".exe" || ext == ".ico" || ext == ".dll") {
		std::string bytes;
		std::error_code ec;
		const auto size = std::filesystem::file_size(png, ec);
		std::FILE* f = ec ? nullptr : std::fopen(png.string().c_str(), "rb");
		if (!f) { error = "can't read " + png.string(); return false; }
		bytes.resize((size_t)size);
		const size_t got = std::fread(bytes.data(), 1, bytes.size(), f);
		std::fclose(f);
		bytes.resize(got);
		if (!(ext == ".ico" ? icoFile(bytes, img, error) : exeIcon(bytes, img, error))) return false;
	} else if (!krt::image::load(png, img, error)) return false;
	width_ = img.width;
	height_ = img.height;
	premul_.resize((size_t)width_ * height_ * 4);
	for (size_t i = 0; i < (size_t)width_ * height_; ++i) {
		const uint8_t* p = img.bgra.data() + i * 4;
		const float a = p[3] / 255.0f;
		premul_[i * 4 + 0] = p[2] / 255.0f * a;
		premul_[i * 4 + 1] = p[1] / 255.0f * a;
		premul_[i * 4 + 2] = p[0] / 255.0f * a;
		premul_[i * 4 + 3] = a;
	}
	return true;
}

bool IconSource::png(int size, std::string& out, std::string& error) const
{
	if (!loaded()) { error = "No icon loaded"; return false; }
	// fit the source into the square, centered
	const double scale = (double)size / std::max(width_, height_);
	const double dw = width_ * scale, dh = height_ * scale;
	const double ox = (size - dw) / 2, oy = (size - dh) / 2;
	krt::image::Image img;
	img.width = img.height = size;
	img.bgra.assign((size_t)size * size * 4, 0);
	for (int y = 0; y < size; ++y) {
		// the source rows this pixel covers
		const double sy0 = (y - oy) / scale, sy1 = (y + 1 - oy) / scale;
		for (int x = 0; x < size; ++x) {
			const double sx0 = (x - ox) / scale, sx1 = (x + 1 - ox) / scale;
			double acc[4] = { 0, 0, 0, 0 }, area = 0;
			const int ys = std::max(0, (int)std::floor(sy0)), ye = std::min(height_, (int)std::ceil(sy1));
			const int xs = std::max(0, (int)std::floor(sx0)), xe = std::min(width_, (int)std::ceil(sx1));
			for (int sy = ys; sy < ye; ++sy) {
				const double wy = std::min<double>(sy + 1, sy1) - std::max<double>(sy, sy0);
				if (wy <= 0) continue;
				for (int sx = xs; sx < xe; ++sx) {
					const double wx = std::min<double>(sx + 1, sx1) - std::max<double>(sx, sx0);
					if (wx <= 0) continue;
					const float* p = &premul_[((size_t)sy * width_ + sx) * 4];
					const double w = wx * wy;
					for (int c = 0; c < 4; ++c) acc[c] += p[c] * w;
					area += w;
				}
			}
			// pixels outside the source stay transparent
			const double full = (sx1 - sx0) * (sy1 - sy0);
			if (area <= 0) continue;
			const double a = acc[3] / full;
			uint8_t* d = img.bgra.data() + ((size_t)y * size + x) * 4;
			if (a <= 0) continue;
			auto to8 = [](double v) { return (uint8_t)std::clamp((int)std::lround(v * 255.0), 0, 255); };
			d[0] = to8(acc[2] / full / a);
			d[1] = to8(acc[1] / full / a);
			d[2] = to8(acc[0] / full / a);
			d[3] = to8(a);
		}
	}
	std::vector<uint8_t> bytes;
	krt::image::SaveOptions opt;
	opt.withAlpha = true;
	if (!krt::image::saveMemory(bytes, img, krt::image::Format::Png, opt, error)) return false;
	out.assign((const char*)bytes.data(), bytes.size());
	return true;
}

bool IconSource::ico(std::string& out, std::string& error) const
{
	const int sizes[] = { 16, 24, 32, 48, 64, 128, 256 };
	std::vector<std::string> images;
	for (int s : sizes) {
		std::string p;
		if (!png(s, p, error)) return false;
		images.push_back(std::move(p));
	}
	out.clear();
	le16(out, 0);
	le16(out, 1);
	le16(out, (uint16_t)images.size());
	uint32_t offset = 6 + 16 * (uint32_t)images.size();
	for (size_t i = 0; i < images.size(); ++i) {
		out += (char)(sizes[i] >= 256 ? 0 : sizes[i]);
		out += (char)(sizes[i] >= 256 ? 0 : sizes[i]);
		out += (char)0;
		out += (char)0;
		le16(out, 1);
		le16(out, 32);
		le32(out, (uint32_t)images[i].size());
		le32(out, offset);
		offset += (uint32_t)images[i].size();
	}
	for (const auto& i : images) out += i;
	return true;
}

bool IconSource::icns(std::string& out, std::string& error) const
{
	const std::pair<const char*, int> types[] = {
		{ "icp4", 16 }, { "icp5", 32 }, { "icp6", 64 }, { "ic07", 128 }, { "ic08", 256 }, { "ic09", 512 },
		{ "ic10", 1024 }, { "ic11", 32 }, { "ic12", 64 }, { "ic13", 256 }, { "ic14", 512 },
	};
	std::string body;
	for (const auto& [type, size] : types) {
		std::string p;
		if (!png(size, p, error)) return false;
		body.append(type, 4);
		be32(body, (uint32_t)p.size() + 8);
		body += p;
	}
	out = "icns";
	be32(out, (uint32_t)body.size() + 8);
	out += body;
	return true;
}

} // namespace kr
