#include "Encrypt.h"

#include <algorithm>
#include <cstring>
#include <fstream>

#include "Subprocess.h"
#include "krt/app/Text.h"

#ifdef KR_HAVE_XP3CRYPT
#include "xp3crypt.hpp"
#endif

namespace fs = std::filesystem;

namespace kr {

namespace {

std::string lower(std::string s)
{
	for (auto& c : s) c = (char)std::tolower((unsigned char)c);
	return s;
}

// A file that may hold the plugin's key slot: an engine or plugin binary (by extension, or an
// extensionless file that starts like an executable)
bool maybeBinary(const fs::path& p)
{
	const std::string name = lower(krt::fromPath(p.filename()));
	const std::string ext = lower(krt::fromPath(p.extension()));
	if (ext == ".so" || ext == ".dll" || ext == ".dylib" || ext == ".wasm" || ext == ".exe") return true;
	if (name.rfind("lib", 0) == 0 && name.find(".so.") != std::string::npos) return true;
	if (!ext.empty()) return false;
	std::ifstream f(p, std::ios::binary);
	char buf[4];
	if (!f.read(buf, 4)) return false;
	const uint32_t m = (uint8_t)buf[0] | (uint8_t)buf[1] << 8 | (uint8_t)buf[2] << 16 | (uint32_t)(uint8_t)buf[3] << 24;
	return std::memcmp(buf, "\x7f" "ELF", 4) == 0 || m == 0xfeedfacfu || m == 0xfeedfaceu || m == 0xbebafecau || m == 0xcafebabeu;
}

// Folders that hold the game's data, not binaries
bool dataFolder(const std::string& name)
{
	const std::string n = lower(name);
	return n == "data" || n == "gamedata" || n == "licenses" || n == "res-override" || n == "_codesignature";
}

} // namespace

#ifdef KR_HAVE_XP3CRYPT

bool canEncryptArchive() { return true; }

bool readArchiveKey(const Json& s, const Project& p, ArchiveKey& key, bool& have, std::string& error)
{
	have = false;
	std::string text = getEnv("KAGEX_ARCHIVE_KEY");
	std::string from = "KAGEX_ARCHIVE_KEY";
	if (text.empty()) {
		const std::string file = str(s, "archive.keyFile");
		if (file.empty()) return true;
		from = file;
		if (!krt::readFile(p.root / krt::toPath(file), text)) { error = "Can't read the archive key " + file; return false; }
	}
	std::string why;
	if (!xp3crypt::parseKey(text, key, why)) {
		std::fill(text.begin(), text.end(), '\0');
		error = "The archive key (" + from + ") isn't a key: " + why;
		return false;
	}
	std::fill(text.begin(), text.end(), '\0');
	have = true;
	return true;
}

bool makeArchiveKey(const fs::path& file, std::string& error)
{
	std::error_code ec;
	if (fs::exists(file, ec)) { error = krt::fromPath(file) + " is already there: a key isn't replaced by mistake"; return false; }
	try {
		xp3crypt::Key key = xp3crypt::randomKey();
		std::string text = xp3crypt::formatKey(key) + "\n";
		xp3crypt::wipe(key);
		fs::create_directories(file.parent_path(), ec);
		const bool ok = krt::writeFile(file, text);
		std::fill(text.begin(), text.end(), '\0');
		if (!ok) { error = "Can't write " + krt::fromPath(file); return false; }
	} catch (const std::exception& e) {
		error = e.what();
		return false;
	}
	return true;
}

bool packEncrypted(const fs::path& stageDir, const fs::path& output, const ArchiveKey& key, int& files, uint64_t& bytes, std::string& error)
{
	xp3crypt::PackOptions opt;   // store everything (encrypted), compress the index
	xp3crypt::PackResult r;
	if (!xp3crypt::pack(stageDir, output, key, opt, r, error, {})) return false;
	files = r.files;
	bytes = r.arcBytes;
	return true;
}

std::vector<fs::path> archiveKeySlots(const fs::path& root, std::string& error)
{
	std::vector<fs::path> found;
	std::error_code ec;
	for (fs::recursive_directory_iterator it(root, ec), end; it != end; it.increment(ec)) {
		if (ec) break;
		const auto st = it->symlink_status(ec);
		if (fs::is_symlink(st)) continue;
		if (fs::is_directory(st)) {
			if (dataFolder(krt::fromPath(it->path().filename()))) it.disable_recursion_pending();
			continue;
		}
		if (!fs::is_regular_file(st) || !maybeBinary(it->path())) continue;
		std::string bytes;
		if (!krt::readFile(it->path(), bytes)) continue;
		const auto at = xp3crypt::findSlots(reinterpret_cast<const uint8_t*>(bytes.data()), bytes.size(), error);
		if (!error.empty()) return {};
		if (!at.empty()) found.push_back(it->path());
	}
	return found;
}

bool writeArchiveKey(const fs::path& file, const ArchiveKey& key, std::string& error)
{
	std::string bytes;
	if (!krt::readFile(file, bytes)) { error = "Can't read " + krt::fromPath(file); return false; }
	std::vector<uint8_t> bin(bytes.begin(), bytes.end());
	const int n = xp3crypt::writeSlots(bin, key, error);
	if (n == 0) return false;
	// in place: the file keeps its permissions (this is the platform's own copy)
	if (!krt::writeFile(file, std::string(bin.begin(), bin.end()))) { error = "Can't write " + krt::fromPath(file); return false; }
	std::fill(bin.begin(), bin.end(), 0);
	return true;
}

void wipeArchiveKey(ArchiveKey& key) { xp3crypt::wipe(key); }

#else

bool canEncryptArchive() { return false; }

bool readArchiveKey(const Json& s, const Project&, ArchiveKey&, bool& have, std::string& error)
{
	have = false;
	if (getEnv("KAGEX_ARCHIVE_KEY").empty() && str(s, "archive.keyFile").empty()) return true;
	error = "This kagex-release was built without xp3crypt, so it can't encrypt the archive";
	return false;
}

bool makeArchiveKey(const fs::path&, std::string& error)
{
	error = "This kagex-release was built without xp3crypt, so it can't make archive keys";
	return false;
}

bool packEncrypted(const fs::path&, const fs::path&, const ArchiveKey&, int&, uint64_t&, std::string& error)
{
	error = "This kagex-release was built without xp3crypt, so it can't encrypt the archive";
	return false;
}

// Without xp3crypt the slot can still be found (whether an engine has the plugin): the marker,
// kept inverted here too
std::vector<fs::path> archiveKeySlots(const fs::path& root, std::string& error)
{
	static const unsigned char inverted[16] = { 0xA7, 0xAF, 0xCC, 0xBC, 0xAD, 0xA6, 0xAF, 0xAB, 0xD2, 0xB4, 0xBA, 0xA6, 0xAC, 0xB3, 0xB0, 0xAB };
	std::string marker;
	for (unsigned char c : inverted) marker += (char)(unsigned char)~c;
	std::vector<fs::path> found;
	std::error_code ec;
	for (fs::recursive_directory_iterator it(root, ec), end; it != end; it.increment(ec)) {
		if (ec) break;
		const auto st = it->symlink_status(ec);
		if (fs::is_symlink(st)) continue;
		if (fs::is_directory(st)) {
			if (dataFolder(krt::fromPath(it->path().filename()))) it.disable_recursion_pending();
			continue;
		}
		if (!fs::is_regular_file(st) || !maybeBinary(it->path())) continue;
		std::string bytes;
		if (krt::readFile(it->path(), bytes) && bytes.find(marker) != std::string::npos) found.push_back(it->path());
	}
	(void)error;
	return found;
}

bool writeArchiveKey(const fs::path&, const ArchiveKey&, std::string& error)
{
	error = "This kagex-release was built without xp3crypt, so it can't write archive keys";
	return false;
}

void wipeArchiveKey(ArchiveKey& key) { std::fill(key.begin(), key.end(), 0); }

#endif

} // namespace kr
