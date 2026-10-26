#include "Project.h"

#include <cctype>
#include <regex>

#include "krt/app/Text.h"

namespace fs = std::filesystem;

namespace kr {

namespace {

bool validUtf8(const std::string& s)
{
	size_t i = 0;
	while (i < s.size()) {
		const unsigned char c = (unsigned char)s[i];
		size_t n = c < 0x80 ? 1 : (c >> 5) == 6 ? 2 : (c >> 4) == 14 ? 3 : (c >> 3) == 30 ? 4 : 0;
		if (!n || i + n > s.size()) return false;
		for (size_t k = 1; k < n; ++k)
			if (((unsigned char)s[i + k] >> 6) != 2) return false;
		i += n;
	}
	return true;
}

std::string lower(std::string s)
{
	for (auto& c : s) c = (char)std::tolower((unsigned char)c);
	return s;
}

// sf.software_title = "..."; and the like, from the game's first.ks
void readFirstKs(const fs::path& data, Project& p)
{
	std::error_code ec;
	fs::path found;
	for (fs::recursive_directory_iterator it(data, fs::directory_options::skip_permission_denied, ec), end;
	     it != end; it.increment(ec)) {
		if (ec) break;
		if (it->is_directory(ec) && lower(krt::fromPath(it->path().filename())) == "system") {
			it.disable_recursion_pending();
			continue;
		}
		if (lower(krt::fromPath(it->path().filename())) == "first.ks") { found = it->path(); break; }
	}
	std::string text;
	if (found.empty() || !krt::readFile(found, text)) return;
	static const std::regex re(R"re(sf\.software_(title|version|maker|year)\s*=\s*"([^"\r\n]*)")re");
	for (std::sregex_iterator it(text.begin(), text.end(), re), end; it != end; ++it) {
		const std::string key = (*it)[1], value = (*it)[2];
		if (!validUtf8(value)) continue;
		if (key == "title") p.title = value;
		else if (key == "version") p.version = value;
		else if (key == "maker") p.maker = value;
		else if (key == "year") p.year = value;
	}
}

// The list of scripts to compile, !scnlist.txt, wherever it is in data/ (the framework finds it
// by name on the auto path)
fs::path findSceneList(const fs::path& data)
{
	std::error_code ec;
	for (fs::recursive_directory_iterator it(data, fs::directory_options::skip_permission_denied, ec), end;
	     it != end; it.increment(ec)) {
		if (ec) break;
		if (lower(krt::fromPath(it->path().filename())) == "!scnlist.txt" && it->is_regular_file(ec)) return it->path();
	}
	return {};
}

// orgname= / appname= from krkrz.cf
void readCf(const fs::path& cf, Project& p)
{
	std::string text;
	if (!krt::readFile(cf, text)) return;
	size_t pos = 0;
	while (pos < text.size()) {
		size_t end = text.find('\n', pos);
		if (end == std::string::npos) end = text.size();
		std::string line = krt::trim(text.substr(pos, end - pos));
		pos = end + 1;
		if (line.empty() || line[0] == ';') continue;
		const size_t eq = line.find('=');
		if (eq == std::string::npos) continue;
		const std::string key = lower(krt::trim(line.substr(0, eq)));
		const std::string value = krt::trim(line.substr(eq + 1));
		if (key == "orgname") p.orgName = value;
		else if (key == "appname") p.appName = value;
	}
}

} // namespace

std::string slug(const std::string& s)
{
	std::string out;
	for (unsigned char c : s) {
		if (std::isalnum(c) && c < 0x80) out += (char)std::tolower(c);
		else if (!out.empty() && out.back() != '-') out += '-';
	}
	while (!out.empty() && out.back() == '-') out.pop_back();
	return out;
}

bool findProject(const fs::path& start, Project& out, std::string& error)
{
	std::error_code ec;
	fs::path dir = fs::absolute(start, ec);
	if (fs::is_regular_file(dir, ec)) dir = dir.parent_path();
	for (int level = 0; level < 4 && !dir.empty(); ++level) {
		if (fs::is_regular_file(dir / "data" / "startup.tjs", ec)) {
			Project p;
			p.root = fs::canonical(dir, ec);
			if (ec) p.root = dir;
			p.data = p.root / "data";
			if (fs::is_regular_file(p.data / "system" / "Initialize.tjs", ec)) {
				p.framework = p.data / "system";
				p.frameworkInData = true;
			} else if (fs::is_regular_file(p.root / "template" / "system" / "Initialize.tjs", ec)) {
				p.framework = p.root / "template" / "system";
			}
			p.frameworkCompiles = !p.framework.empty() && fs::is_regular_file(p.framework / "SceneParser.tjs", ec);
			p.sceneList = findSceneList(p.data);
			readFirstKs(p.data, p);
			readCf(p.root / "krkrz.cf", p);
			for (const char* icon : { "platform/icon-1024.png", "icon-1024.png", "icon.png" }) {
				if (fs::is_regular_file(p.root / icon, ec)) { p.icon = p.root / icon; break; }
			}
			for (const char* preview : { "platform/web/preview.jpg", "platform/web/preview.png" }) {
				if (fs::is_regular_file(p.root / preview, ec)) { p.preview = p.root / preview; break; }
			}
			for (const char* exe : { "krkrz.exe", "krkrz" }) {
				if (fs::is_regular_file(p.root / exe, ec)) { p.engine = p.root / exe; break; }
			}
			out = std::move(p);
			return true;
		}
		const fs::path parent = dir.parent_path();
		if (parent == dir) break;
		dir = parent;
	}
	error = "No KAGEX project here: none of " + krt::fromPath(fs::absolute(start, ec)) +
	        " and the folders above it has data/startup.tjs";
	return false;
}

} // namespace kr
