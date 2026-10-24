//---------------------------------------------------------------------------
// Icons from the game's 1024x1024 PNG: PNGs of any size, Windows .ico and macOS .icns
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <string>
#include <vector>

namespace kr {

class IconSource {
public:
	bool load(const std::filesystem::path& png, std::string& error);
	bool loaded() const { return width_ > 0; }
	/// A square PNG of size x size (area-averaged; the source is fitted into the square)
	bool png(int size, std::string& out, std::string& error) const;
	/// .ico with 16, 24, 32, 48, 64, 128 and 256 (PNG-compressed entries)
	bool ico(std::string& out, std::string& error) const;
	/// .icns with 16 to 1024 (PNG entries)
	bool icns(std::string& out, std::string& error) const;

private:
	int width_ = 0, height_ = 0;
	std::vector<float> premul_;   // RGBA, alpha-premultiplied, 0..1
};

} // namespace kr
