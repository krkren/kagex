#include "Icons.h"

#include <algorithm>
#include <cmath>

#include "krt/image/Image.h"

namespace kr {

namespace {
void be32(std::string& s, uint32_t v) { for (int i = 3; i >= 0; --i) s += (char)((v >> (8 * i)) & 0xff); }
void le16(std::string& s, uint16_t v) { s += (char)(v & 0xff); s += (char)(v >> 8); }
void le32(std::string& s, uint32_t v) { for (int i = 0; i < 4; ++i) s += (char)((v >> (8 * i)) & 0xff); }
}

bool IconSource::load(const std::filesystem::path& png, std::string& error)
{
	krt::image::Image img;
	if (!krt::image::load(png, img, error)) return false;
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
