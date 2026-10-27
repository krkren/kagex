#include "LipTracks.h"

#include <algorithm>
#include <map>
#include <mutex>

#include "Archive.h"
#include "krt/app/Text.h"

namespace fs = std::filesystem;

namespace kr {

namespace {

std::string lower(std::string s)
{
	std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return (char)std::tolower(c); });
	return s;
}

// a voice's SHA-256, kept while its size and time stay the same (the check runs often)
bool cachedHash(const fs::path& file, std::string& hex)
{
	static std::mutex mu;
	static std::map<std::string, std::pair<std::string, std::string>> cache;   // path -> (size:time, hash)
	std::error_code ec;
	const auto size = fs::file_size(file, ec);
	if (ec) return false;
	const auto time = fs::last_write_time(file, ec).time_since_epoch().count();
	const std::string key = std::to_string(size) + ":" + std::to_string((long long)time);
	const std::string path = krt::fromPath(file);
	{
		std::lock_guard<std::mutex> lk(mu);
		auto it = cache.find(path);
		if (it != cache.end() && it->second.first == key) { hex = it->second.second; return true; }
	}
	std::string err;
	if (!sha256File(file, hex, err)) return false;
	std::lock_guard<std::mutex> lk(mu);
	cache[path] = { key, hex };
	return true;
}

} // namespace

LipHeader readLipHeader(const fs::path& lip)
{
	LipHeader h;
	std::string data;
	std::error_code ec;
	if (!fs::is_regular_file(lip, ec) || !krt::readFile(lip, data)) return h;
	h.exists = true;
	if (data.size() >= 3 && (unsigned char)data[0] == 0xEF && (unsigned char)data[1] == 0xBB && (unsigned char)data[2] == 0xBF) data.erase(0, 3);
	size_t pos = 0;
	while (pos < data.size()) {
		size_t end = data.find('\n', pos);
		if (end == std::string::npos) end = data.size();
		std::string line = data.substr(pos, end - pos);
		pos = end + 1;
		if (!line.empty() && line.back() == '\r') line.pop_back();
		if (line.rfind("# kagex-lipsync", 0) == 0) h.ours = true;
		else if (line.rfind("# voice: ", 0) == 0) h.voiceHash = krt::trim(line.substr(9));
		else if (line.rfind("# text: ", 0) == 0) h.text = line.substr(8);
		else if (line.rfind("# language: ", 0) == 0) h.language = krt::trim(line.substr(12));
		else if (!line.empty() && line[0] != '#') ++h.marks;
	}
	return h;
}

fs::path voiceOfLip(const fs::path& lip)
{
	std::error_code ec;
	for (const char* ext : { ".wav", ".ogg", ".opus", ".flac" }) {
		const fs::path f = lip.parent_path() / (krt::fromPath(lip.stem()) + ext);
		if (fs::is_regular_file(f, ec)) return f;
	}
	return {};
}

std::vector<fs::path> staleLipTracks(const Project& project)
{
	std::vector<fs::path> out;
	std::error_code ec;
	for (fs::recursive_directory_iterator it(project.data, ec), end; it != end; it.increment(ec)) {
		if (ec) break;
		if (!it->is_regular_file(ec) || lower(krt::fromPath(it->path().extension())) != ".lip") continue;
		const fs::path rel = it->path().lexically_relative(project.data);
		if (rel.begin() != rel.end() && lower(krt::fromPath(*rel.begin())) == "system") continue;
		const LipHeader h = readLipHeader(it->path());
		if (!h.ours || h.voiceHash.empty()) continue;
		const fs::path voice = voiceOfLip(it->path());
		std::string hex;
		if (voice.empty() || !cachedHash(voice, hex) || hex != h.voiceHash) out.push_back(it->path());
	}
	std::sort(out.begin(), out.end());
	return out;
}

} // namespace kr
