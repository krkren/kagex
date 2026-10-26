#include "Scenes.h"

#include <algorithm>
#include <cstring>
#include <fstream>
#include <functional>

#include "Subprocess.h"
#include "krt/app/Text.h"

#ifdef KR_HAVE_SCNFILE
#include "psb.hpp"
#include "seal.hpp"
#endif

namespace fs = std::filesystem;

namespace kr {

namespace {

std::string lower(std::string s)
{
	for (auto& c : s) c = (char)std::tolower((unsigned char)c);
	return s;
}

// A file that may be a binary with the plugin in it: a library, an executable or a WebAssembly
// module (by name, or an extensionless file that starts like an executable)
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

#ifdef KR_HAVE_SCNFILE

bool canEncryptScenes() { return true; }

bool readSceneKey(const Json& s, const Project& p, SceneKey& key, bool& have, std::string& error)
{
	have = false;
	std::string text = getEnv("KAGEX_SCENES_KEY");
	std::string from = "KAGEX_SCENES_KEY";
	if (text.empty()) {
		const std::string file = str(s, "scenes.keyFile");
		if (file.empty()) return true;
		from = file;
		if (!krt::readFile(p.root / krt::toPath(file), text)) { error = "Can't read the scenario key " + file; return false; }
	}
	try {
		key = scnseal::parseKey(text);
	} catch (const scnseal::Error& e) {
		std::fill(text.begin(), text.end(), '\0');
		std::string why = e.what();
		if (why.rfind("scnseal: ", 0) == 0) why = why.substr(9);
		error = "The scenario key (" + from + ") isn't a key: " + why;
		return false;
	}
	std::fill(text.begin(), text.end(), '\0');
	have = true;
	return true;
}

bool makeSceneKey(const fs::path& file, std::string& error)
{
	std::error_code ec;
	if (fs::exists(file, ec)) { error = krt::fromPath(file) + " is already there: a key isn't replaced by mistake"; return false; }
	try {
		scnseal::Key key = scnseal::randomKey();
		std::string text = scnseal::formatKey(key) + "\n";
		scnseal::wipe(key);
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

bool sealScene(const fs::path& file, const SceneKey& key, std::string& error)
{
	std::string text;
	if (!krt::readFile(file, text)) { error = "Can't read " + krt::fromPath(file); return false; }
	try {
		const std::vector<uint8_t> psb(text.begin(), text.end());
		if (scnseal::isSealed(psb.data(), psb.size())) return true;   // already done
		scnpsb::read(psb.data(), psb.size());                          // one the plugin reads
		const std::vector<uint8_t> sealed = scnseal::seal(psb, key);
		std::error_code ec;
		fs::remove(file, ec);
		if (!krt::writeFile(file, std::string(sealed.begin(), sealed.end()))) { error = "Can't write " + krt::fromPath(file); return false; }
	} catch (const std::exception& e) {
		error = krt::fromPath(file.filename()) + ": " + e.what();
		return false;
	}
	return true;
}

namespace {

// Where the key slots are in a binary: one, or one per architecture in a universal (fat) Mach-O
// binary. Empty when there's none
std::vector<size_t> slotOffsets(const std::string& bytes, const std::string& name, std::string& error)
{
	const auto m = scnseal::slotMarker();
	const std::string marker(m.begin(), m.end());
	std::vector<size_t> at;
	const std::boyer_moore_horspool_searcher<std::string::const_iterator> searcher(marker.cbegin(), marker.cend());
	for (auto it = std::search(bytes.cbegin(), bytes.cend(), searcher); it != bytes.cend();
	     it = std::search(it + 1, bytes.cend(), searcher)) {
		const size_t off = (size_t)(it - bytes.cbegin());
		if (off + scnseal::SLOT_SIZE > bytes.size()) { error = name + ": its key slot is cut short"; return {}; }
		at.push_back(off);
	}
	if (at.size() > 1) {
		const auto u = [&](size_t i) { return (uint32_t)(uint8_t)bytes[i]; };
		const bool fat = bytes.size() >= 8 && u(0) == 0xca && u(1) == 0xfe && u(2) == 0xba && (u(3) == 0xbe || u(3) == 0xbf);
		const uint32_t arches = fat ? (u(4) << 24 | u(5) << 16 | u(6) << 8 | u(7)) : 1;
		if (at.size() > arches) { error = name + " has " + std::to_string(at.size()) + " key slots, where it should have one"; return {}; }
	}
	return at;
}

} // namespace

std::vector<fs::path> sceneKeySlots(const fs::path& root, std::string& error)
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
		const auto at = slotOffsets(bytes, krt::fromPath(it->path().filename()), error);
		if (!error.empty()) return {};
		if (!at.empty()) found.push_back(it->path());
	}
	return found;
}

bool writeSceneKey(const fs::path& file, const SceneKey& key, std::string& error)
{
	std::string bytes;
	if (!krt::readFile(file, bytes)) { error = "Can't read " + krt::fromPath(file); return false; }
	const auto at = slotOffsets(bytes, krt::fromPath(file.filename()), error);
	if (!error.empty()) return false;
	if (at.empty()) { error = krt::fromPath(file.filename()) + " has no key slot"; return false; }
	for (size_t off : at) std::memcpy(&bytes[off + scnseal::SLOT_MARKER_SIZE], key.data(), key.size());
	// in place: the file keeps its permissions (this is the platform's own copy)
	if (!krt::writeFile(file, bytes)) { error = "Can't write " + krt::fromPath(file); return false; }
	std::fill(bytes.begin(), bytes.end(), '\0');
	return true;
}

void wipeSceneKey(SceneKey& key) { scnseal::wipe(key); }

#else

bool canEncryptScenes() { return false; }

bool readSceneKey(const Json& s, const Project&, SceneKey&, bool& have, std::string& error)
{
	have = false;
	if (getEnv("KAGEX_SCENES_KEY").empty() && str(s, "scenes.keyFile").empty()) return true;
	error = "This kagex-release was built without scnfile, so it can't encrypt scenarios";
	return false;
}

bool makeSceneKey(const fs::path&, std::string& error)
{
	error = "This kagex-release was built without scnfile, so it can't make scenario keys";
	return false;
}

bool sealScene(const fs::path&, const SceneKey&, std::string& error)
{
	error = "This kagex-release was built without scnfile, so it can't encrypt scenarios";
	return false;
}

// Without scnfile the slot can still be found (whether an engine has the plugin): the marker,
// kept inverted here too
std::vector<fs::path> sceneKeySlots(const fs::path& root, std::string& error)
{
	static const unsigned char inverted[16] = { 0xB4, 0xAC, 0xBC, 0xB1, 0xD2, 0xB4, 0xBA, 0xA6, 0xD2, 0xAC, 0xB3, 0xB0, 0xAB, 0xD2, 0x89, 0xCE };
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

bool writeSceneKey(const fs::path&, const SceneKey&, std::string& error)
{
	error = "This kagex-release was built without scnfile, so it can't write scenario keys";
	return false;
}

void wipeSceneKey(SceneKey& key) { std::fill(key.begin(), key.end(), 0); }

#endif

} // namespace kr
