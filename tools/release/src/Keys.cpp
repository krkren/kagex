#include "Keys.h"

#include <algorithm>
#include <cctype>
#include <cstring>

#include <tomcrypt.h>

#include "Sign.h"
#include "Subprocess.h"
#include "krt/app/Text.h"

namespace fs = std::filesystem;

namespace kr {

namespace {

const char kPrivBegin[] = "-----BEGIN RSA PRIVATE KEY-----";
const char kPrivEnd[]   = "-----END RSA PRIVATE KEY-----";

void wipeString(std::string& s)
{
	std::fill(s.begin(), s.end(), '\0');
	s.clear();
}

std::string lower(std::string s)
{
	for (auto& c : s) c = (char)std::tolower((unsigned char)c);
	return s;
}

bool parseHex32(const std::string& text, std::array<uint8_t, 32>& out)
{
	if (text.size() != 64) return false;
	for (size_t i = 0; i < 32; ++i) {
		int v = 0;
		for (int k = 0; k < 2; ++k) {
			const char c = text[i * 2 + k];
			int d;
			if (c >= '0' && c <= '9') d = c - '0';
			else if (c >= 'a' && c <= 'f') d = c - 'a' + 10;
			else if (c >= 'A' && c <= 'F') d = c - 'A' + 10;
			else return false;
			v = v * 16 + d;
		}
		out[i] = (uint8_t)v;
	}
	return true;
}

std::string hex32(const std::array<uint8_t, 32>& key)
{
	static const char digits[] = "0123456789abcdef";
	std::string s;
	for (uint8_t b : key) { s += digits[b >> 4]; s += digits[b & 15]; }
	return s;
}

bool randomKey(std::array<uint8_t, 32>& key, std::string& error)
{
	// the system's random source (/dev/urandom, or the Windows CryptoAPI) through libtomcrypt
	if (rng_get_bytes(key.data(), (unsigned long)key.size(), nullptr) != key.size()) {
		error = "the system's random source didn't answer";
		return false;
	}
	return true;
}

const char kHeader[] =
	"# kagex-release keys. Keep this file secret: outside the game's folder and out of its repository.\n"
	"# Back it up: patches and later builds of a game need the keys it was released with. Each kind of\n"
	"# protection has a key of its own: archive (data.xp3, xp3crypt), scenes (compiled scenarios, scnfile)\n"
	"# and the RSA private key below (signing; krkrsign reads this file as it is).\n";

} // namespace

void GameKeys::wipe()
{
	std::fill(archive.begin(), archive.end(), 0);
	std::fill(scenes.begin(), scenes.end(), 0);
	wipeString(signing);
	hasArchive = hasScenes = hasSigning = false;
}

KeysNeeded keysNeeded(const Json& s)
{
	KeysNeeded n;
	n.archive = flag(s, "archive.encrypt");
	n.scenes = flag(s, "scenes.compile") && flag(s, "scenes.encrypt");
	n.signing = flag(s, "signing.enabled");
	return n;
}

fs::path keysFile(const Json& s, const Project& p, std::string* from)
{
	const std::string env = getEnv("KAGEX_KEYS_FILE");
	if (!env.empty()) {
		if (from) *from = "KAGEX_KEYS_FILE";
		return krt::toPath(env);
	}
	const std::string file = str(s, "keys.file");
	if (file.empty()) return {};
	if (from) *from = "keys.file";
	const fs::path f = krt::toPath(file);
	return f.is_absolute() ? f : p.root / f;
}

bool parseKeys(const std::string& text, GameKeys& keys, std::string& error)
{
	keys.wipe();
	size_t pos = 0;
	int lineNo = 0;
	bool inPem = false;
	std::string pem;
	while (pos < text.size()) {
		size_t end = text.find('\n', pos);
		if (end == std::string::npos) end = text.size();
		std::string line = text.substr(pos, end - pos);
		pos = end + 1;
		++lineNo;
		if (!line.empty() && line.back() == '\r') line.pop_back();
		if (lineNo == 1 && line.size() >= 3 && (unsigned char)line[0] == 0xEF && (unsigned char)line[1] == 0xBB && (unsigned char)line[2] == 0xBF)
			line.erase(0, 3);
		const std::string t = krt::trim(line);
		if (inPem) {
			pem += t + "\r\n";
			if (t == kPrivEnd) {
				inPem = false;
				if (keys.hasSigning) { wipeString(pem); error = "line " + std::to_string(lineNo) + ": a second signing key"; return false; }
				keys.signing = pem;
				keys.hasSigning = true;
				wipeString(pem);
			}
			wipeString(line);
			continue;
		}
		if (t.empty() || t[0] == '#') continue;
		if (t == kPrivBegin) { inPem = true; pem = t + "\r\n"; continue; }
		const size_t colon = t.find(':');
		if (colon == std::string::npos) { error = "line " + std::to_string(lineNo) + " isn't \"name: key\""; return false; }
		const std::string name = lower(krt::trim(t.substr(0, colon)));
		std::string value = krt::trim(t.substr(colon + 1));
		if (name == "signing" && value.empty()) continue;   // a label before the PEM block
		std::array<uint8_t, 32>* slot = nullptr;
		bool* has = nullptr;
		if (name == "archive") { slot = &keys.archive; has = &keys.hasArchive; }
		else if (name == "scenes") { slot = &keys.scenes; has = &keys.hasScenes; }
		else { error = "line " + std::to_string(lineNo) + ": no key is called \"" + name + "\" (archive, scenes, or the signing key's PEM block)"; return false; }
		if (*has) { error = "line " + std::to_string(lineNo) + ": a second " + name + " key"; return false; }
		const bool ok = parseHex32(value, *slot);
		wipeString(value);
		wipeString(line);
		if (!ok) { error = "line " + std::to_string(lineNo) + ": the " + name + " key isn't 64 hexadecimal digits"; return false; }
		*has = true;
	}
	if (inPem) { wipeString(pem); error = std::string("the signing key has no \"") + kPrivEnd + "\" line"; return false; }
	return true;
}

bool readKeys(const fs::path& file, GameKeys& keys, std::string& error)
{
	std::string text;
	if (!krt::readFile(file, text)) { error = "Can't read " + krt::fromPath(file); return false; }
	std::string why;
	const bool ok = parseKeys(text, keys, why);
	wipeString(text);
	if (!ok) error = krt::fromPath(file) + ": " + why;
	return ok;
}

bool loadKeys(const Json& s, const Project& p, const KeysNeeded& need, GameKeys& keys, std::string& error)
{
	keys.wipe();
	if (!need.any()) return true;
	std::string from;
	const fs::path file = keysFile(s, p, &from);
	if (file.empty()) {
		error = "Encrypting and signing take the game's keys file: choose it in Keys (keys.file), or make one with Create keys… (kagex-release --cli keygen <file>)";
		return false;
	}
	std::error_code ec;
	if (!fs::is_regular_file(file, ec)) {
		error = "The keys file " + krt::fromPath(file) + (from == "KAGEX_KEYS_FILE" ? " (KAGEX_KEYS_FILE)" : "") + " doesn't exist (Create keys… makes one)";
		return false;
	}
	if (!readKeys(file, keys, error)) return false;
	std::string missing;
	const auto lack = [&](bool needed, bool have, const char* name) {
		if (needed && !have) missing += std::string(missing.empty() ? "" : ", ") + name;
	};
	lack(need.archive, keys.hasArchive, "archive");
	lack(need.scenes, keys.hasScenes, "scenes");
	lack(need.signing, keys.hasSigning, "signing");
	if (!missing.empty()) {
		error = "The keys file " + krt::fromPath(file) + " has no " + missing + " key: Create keys… (or --cli keygen) adds the keys a file lacks and keeps the rest";
		keys.wipe();
		return false;
	}
	if (keys.hasArchive && keys.hasScenes && keys.archive == keys.scenes) {
		error = "The archive and scenes keys in " + krt::fromPath(file) + " are the same: each kind of encryption needs a key of its own (delete one line, and Create keys… makes a new one)";
		keys.wipe();
		return false;
	}
	return true;
}

bool makeKeys(const fs::path& file, int bits, bool force, std::vector<std::string>& added, std::string& error)
{
	added.clear();
	GameKeys keys;
	std::error_code ec;
	const bool existed = fs::exists(file, ec);
	if (existed && !force) {
		if (!readKeys(file, keys, error)) {
			error += " (fix it, or move it away to make a new one)";
			return false;
		}
		if (keys.hasArchive && keys.hasScenes && keys.hasSigning) {
			error = krt::fromPath(file) + " already has every key (archive, scenes and signing); --force replaces them all, "
			        "which a released game's patches can't follow";
			return false;
		}
	}
	if (force) keys.wipe();
	if (!keys.hasArchive) {
		if (!randomKey(keys.archive, error)) return false;
		keys.hasArchive = true;
		added.push_back("archive");
	}
	if (!keys.hasScenes) {
		do {
			if (!randomKey(keys.scenes, error)) return false;
		} while (keys.scenes == keys.archive);
		keys.hasScenes = true;
		added.push_back("scenes");
	}
	if (!keys.hasSigning) {
		std::string pub;
		if (!generateSigningKeys(bits, pub, keys.signing, error)) return false;
		keys.hasSigning = true;
		added.push_back("signing");
	}
	std::string text = kHeader;
	text += "archive: " + hex32(keys.archive) + "\n";
	text += "scenes: " + hex32(keys.scenes) + "\n";
	text += "signing:\n";
	// one line ending for the whole file
	for (char c : keys.signing) if (c != '\r') text += c;
	if (!text.empty() && text.back() != '\n') text += '\n';
	keys.wipe();
	if (!file.parent_path().empty()) fs::create_directories(file.parent_path(), ec);
	// written next to the file, then moved over it, so a failure leaves the old file as it was
	const fs::path tmp = krt::toPath(krt::fromPath(file) + ".new");
	const bool ok = krt::writeFile(tmp, text);
	wipeString(text);
	if (!ok) { fs::remove(tmp, ec); error = "Can't write " + krt::fromPath(file); return false; }
#ifndef _WIN32
	fs::permissions(tmp, fs::perms::owner_read | fs::perms::owner_write, fs::perm_options::replace, ec);
#endif
	fs::rename(tmp, file, ec);
	if (ec) { fs::remove(tmp, ec); error = "Can't write " + krt::fromPath(file); return false; }
	return true;
}

} // namespace kr
