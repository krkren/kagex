//---------------------------------------------------------------------------
// kagex-lipsync: the mouths' vowels for the voices a game picks (README.md)
//
//   kagex-lipsync [<project folder>]                 opens the window
//   kagex-lipsync --cli list  [<project folder>]     the voices, their lines and their tracks
//   kagex-lipsync --cli make  [<voice>...]           makes the voices' tracks from their lines
//   kagex-lipsync --cli check [<project folder>]     the tracks whose voice changed since
//   kagex-lipsync --cli align <voice file> <text> [<out.lip>]   one file and a line, no game
//
// make takes voice file names (ai000001.ogg) and/or --all (every voice the scripts give a line),
// --character=NAME (that character's), --stale (the tracks whose voice changed); --text=TEXT
// (the line, for one voice), --force (also remake current tracks and replace hand-written ones).
// --project=DIR names the game for make; list and check take it as their argument. Without one,
// the current folder, or else the folder above the tool. --engines=DIR as kagex-release.
// --json prints JSON. Exit codes: 0 = fine, 1 = problems found, 2 = failed.
//---------------------------------------------------------------------------
#include <appserve/appserve.h>

#include <algorithm>
#include <cstdio>
#include <map>
#include <memory>
#include <mutex>

#include "Align.h"
#include "Project.h"
#include "Subprocess.h"
#include "Voices.h"
#include "krt/app/JobRunner.h"
#include "krt/app/Progress.h"
#include "krt/app/Text.h"

#ifdef _WIN32
#include <windows.h>
#endif

namespace fs = std::filesystem;
using appserve::Json;
using namespace kr;

namespace {

struct Options {
	bool cli = false, json = false, all = false, stale = false, force = false;
	std::string project, engines, character, text;
};

std::string lower(std::string s)
{
	std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return (char)std::tolower(c); });
	return s;
}

bool resolveProject(const std::string& arg, Project& p, std::string& error)
{
	std::error_code ec;
	std::vector<fs::path> starts;
	if (!arg.empty()) starts.push_back(krt::toPath(arg));
	else {
		starts.push_back(fs::current_path(ec));
		starts.push_back(krt::selfPath().parent_path());
	}
	std::string first;
	for (const auto& s : starts) {
		std::string err;
		if (findProject(s, p, err)) return true;
		if (first.empty()) first = err;
	}
	error = first;
	return false;
}

Json voiceToJson(const Voice& v)
{
	Json o = Json::object();
	o.set("name", Json(v.name));
	o.set("file", Json(krt::fromPath(v.file)));
	o.set("status", Json(v.status));
	o.set("lip", Json(krt::fromPath(v.lip)));
	Json lines = Json::array();
	for (const auto& l : v.lines) {
		Json x = Json::object();
		x.set("character", Json(l.character));
		x.set("script", Json(l.script));
		x.set("text", Json(l.text));
		x.set("reading", Json(l.reading));
		x.set("language", Json(l.language));
		lines.push(std::move(x));
	}
	o.set("lines", std::move(lines));
	if (v.header.exists) {
		Json h = Json::object();
		h.set("text", Json(v.header.text));
		h.set("language", Json(v.header.language));
		h.set("marks", Json((int64_t)v.header.marks));
		o.set("track", std::move(h));
	}
	return o;
}

/// A voice to make a track for, and its line (empty: the one the scripts give it)
struct MakeItem {
	std::string name;
	std::string text;
};

/// Makes the tracks of these voices (found by name in voices, whose states are updated)
Json makeTracks(std::vector<Voice>& voices, const std::vector<MakeItem>& items, krt::Progress& pr)
{
	Json out = Json::object();
	Json results = Json::array();
	Aligner aligner(lipsyncDataDir());
	std::string err;
	if (!aligner.open(err)) {
		out.set("ok", Json(false));
		out.set("error", Json(err));
		out.set("results", std::move(results));
		return out;
	}
	std::map<std::string, size_t> byName;
	for (size_t i = 0; i < voices.size(); ++i) byName[lower(voices[i].name)] = i;
	int made = 0, failed = 0;
	for (size_t i = 0; i < items.size(); ++i) {
		if (pr.canceled()) break;
		const MakeItem& it = items[i];
		pr.progress((double)i / items.size(), "Aligning " + it.name);
		Json r = Json::object();
		r.set("name", Json(it.name));
		auto found = byName.find(lower(it.name));
		std::string error;
		if (found == byName.end()) error = "The game has no voice of that name";
		else {
			Voice& v = voices[found->second];
			// the line typed in, else the scripts' in each of the game's languages, until one fits
			const std::vector<std::string> texts = it.text.empty() ? lineTextsFor(v) : std::vector<std::string>{ krt::trim(it.text) };
			std::string text;
			AlignResult a;
			bool aligned = false;
			if (v.file.empty()) error = "The voice isn't in the game's data";
			else if (texts.empty() || texts.front().empty()) error = "No line: the scripts don't give it one, so type what it says";
			else {
				for (const auto& t : texts) {
					std::string e;
					a = AlignResult();
					if (aligner.align(v.file, t, a, e)) { text = t; aligned = true; break; }
					if (error.empty()) error = e;
					if (pr.canceled()) break;
				}
				if (!aligned && texts.size() > 1 && error.find("doesn't fit") != std::string::npos)
					error = "The voice doesn't fit its line in any of the game's " + std::to_string(texts.size()) +
					        " languages: type what it says, in the language it says it";
			}
			if (aligned) error.clear();
			if (!aligned) {}
			else if (!writeLip(v, text, a, error)) {}
			else {
				refreshVoice(v);
				r.set("marks", Json((int64_t)a.marks.size()));
				r.set("language", Json(a.language));
				r.set("lip", Json(krt::fromPath(v.lip)));
				r.set("warnings", Json::array(a.warnings));
				r.set("voice", voiceToJson(v));
				for (const auto& w : a.warnings) pr.log(it.name + ": " + w);
			}
		}
		r.set("ok", Json(error.empty()));
		if (!error.empty()) {
			r.set("error", Json(error));
			pr.log(it.name + ": " + error);
			++failed;
		} else {
			++made;
		}
		results.push(std::move(r));
	}
	pr.progress(1, "Made " + std::to_string(made) + " tracks" + (failed ? ", " + std::to_string(failed) + " failed" : ""));
	out.set("ok", Json(failed == 0 && !pr.canceled()));
	out.set("made", Json((int64_t)made));
	out.set("failed", Json((int64_t)failed));
	out.set("results", std::move(results));
	return out;
}

/// The game's voices with the lines its scripts give them (runs the game's engine)
bool readGame(const Project& p, const std::string& engines, krt::Progress& pr, std::vector<Voice>& voices,
              std::vector<std::string>& problems, std::string& error, const std::vector<std::string>& extra = {})
{
	fs::path exe;
	if (!findGameEngine(p, krt::toPath(engines), pr, exe, error)) return false;
	std::vector<VoiceLine> lines;
	std::string log;
	if (!readVoiceLines(p, exe, pr, lines, problems, log, error)) return false;
	voices = listVoices(p, lines, extra);
	return true;
}

//---------------------------------------------------------------------------
// CLI
//---------------------------------------------------------------------------
int runCli(const Options& o, const std::vector<std::string>& args)
{
	if (args.empty()) {
		std::fprintf(stderr, "usage: kagex-lipsync --cli list|make|check|align ... (see --help)\n");
		return 2;
	}
	const std::string cmd = args[0];
	std::string err;
	krt::ConsoleProgress progress(o.json);

	if (cmd == "align") {
		// one voice file and its line, outside any game
		if (args.size() < 3) { std::fprintf(stderr, "usage: kagex-lipsync --cli align <voice file> <text> [<out.lip>]\n"); return 2; }
		Voice v;
		v.file = krt::toPath(args[1]);
		v.name = krt::fromPath(v.file.filename());
		v.lip = args.size() > 3 ? krt::toPath(args[3]) : fs::path();
		Aligner aligner(lipsyncDataDir());
		AlignResult r;
		if (!aligner.align(v.file, args[2], r, err)) { std::fprintf(stderr, "error: %s\n", err.c_str()); return 2; }
		for (const auto& w : r.warnings) std::fprintf(stderr, "warning: %s\n", w.c_str());
		if (!v.lip.empty()) {
			if (!writeLip(v, args[2], r, err)) { std::fprintf(stderr, "error: %s\n", err.c_str()); return 2; }
			std::printf("Wrote %s: %d marks (%s)\n", krt::fromPath(v.lip).c_str(), (int)r.marks.size(), r.language.c_str());
		} else {
			for (const auto& m : r.marks) std::printf("%d\t%s\t%d\n", m.ms, m.mouth.c_str(), m.open);
		}
		return 0;
	}

	Project p;
	const std::string where = !o.project.empty() ? o.project : (cmd != "make" && args.size() > 1 ? args[1] : std::string());
	if (!resolveProject(where, p, err)) { std::fprintf(stderr, "error: %s\n", err.c_str()); return 2; }

	if (cmd == "check") {
		// no engine needed: the tracks already there, against their voices
		const auto voices = voicesWithTracks(p);
		int stale = 0, orphans = 0;
		Json list = Json::array();
		for (const auto& v : voices) {
			if (v.status == "stale") ++stale;
			if (v.status == "missing") ++orphans;
			list.push(voiceToJson(v));
		}
		if (o.json) {
			Json out = Json::object();
			out.set("tracks", std::move(list));
			out.set("stale", Json((int64_t)stale));
			std::printf("%s\n", out.dump(1).c_str());
		} else {
			for (const auto& v : voices) {
				if (v.status == "stale") std::printf("out of date: %s (the voice changed since its track was made)\n", krt::fromPath(v.lip).c_str());
				else if (v.status == "missing") std::printf("no voice: %s\n", krt::fromPath(v.lip).c_str());
			}
			std::printf("%d tracks: %d out of date, %d without a voice\n", (int)voices.size(), stale, orphans);
		}
		return stale > 0 ? 1 : 0;
	}

	if (cmd == "list") {
		std::vector<Voice> voices;
		std::vector<std::string> problems;
		if (!readGame(p, o.engines, progress, voices, problems, err)) { std::fprintf(stderr, "error: %s\n", err.c_str()); return 2; }
		progress.finish();
		if (o.json) {
			Json out = Json::object();
			Json list = Json::array();
			for (const auto& v : voices) list.push(voiceToJson(v));
			out.set("voices", std::move(list));
			out.set("problems", Json::array(problems));
			std::printf("%s\n", out.dump(1).c_str());
			return problems.empty() ? 0 : 1;
		}
		for (const auto& v : voices) {
			const std::string who = v.lines.empty() ? "" : v.lines.front().character;
			const std::string line = v.lines.empty() ? "(no line)" : v.lines.front().text;
			std::printf("%-8s %-24s %-10s %s\n", v.status.c_str(), v.name.c_str(), who.c_str(), line.c_str());
		}
		for (const auto& pr : problems) std::fprintf(stderr, "problem: %s\n", pr.c_str());
		return problems.empty() ? 0 : 1;
	}

	if (cmd == "make") {
		std::vector<std::string> names(args.begin() + 1, args.end());
		if (names.empty() && !o.all && o.character.empty() && !o.stale) {
			std::fprintf(stderr, "usage: kagex-lipsync --cli make [<voice>...] [--all] [--character=NAME] [--stale] [--text=TEXT] [--force]\n");
			return 2;
		}
		if (!o.text.empty() && names.size() != 1) { std::fprintf(stderr, "error: --text is for one voice\n"); return 2; }
		std::vector<Voice> voices;
		if (!o.text.empty()) {
			// the line is given: no need to read the scripts
			voices = listVoices(p, {}, names);
		} else {
			std::vector<std::string> problems;
			if (!readGame(p, o.engines, progress, voices, problems, err, names)) { std::fprintf(stderr, "error: %s\n", err.c_str()); return 2; }
			for (const auto& pr : problems) std::fprintf(stderr, "problem: %s\n", pr.c_str());
		}
		std::vector<MakeItem> items;
		std::map<std::string, bool> named;
		for (const auto& n : names) named[lower(n)] = true;
		for (const auto& v : voices) {
			const bool picked = named.count(lower(v.name)) > 0;
			bool wanted = picked;
			if (!wanted && o.all && !v.lines.empty()) wanted = true;
			if (!wanted && !o.character.empty())
				for (const auto& l : v.lines) if (lower(l.character) == lower(o.character)) wanted = true;
			if (!wanted && o.stale && v.status == "stale") wanted = true;
			if (!wanted) continue;
			// a current track is made again only when asked for by name, a hand-written one only with --force
			if (v.status == "manual" && !o.force) { std::fprintf(stderr, "skipped %s: its track is hand-written (--force replaces it)\n", v.name.c_str()); continue; }
			if (v.status == "current" && !picked && !o.force) continue;
			items.push_back({ v.name, o.text });
		}
		for (const auto& n : names) {
			bool there = false;
			for (const auto& v : voices) if (lower(v.name) == lower(n)) there = true;
			if (!there) std::fprintf(stderr, "error: the game has no voice named %s\n", n.c_str());
		}
		const Json r = makeTracks(voices, items, progress);
		progress.finish();
		if (o.json) { std::printf("%s\n", r.dump(1).c_str()); return r["ok"].asBool() ? 0 : 1; }
		if (r.has("error")) { std::fprintf(stderr, "error: %s\n", r["error"].asStr().c_str()); return 2; }
		for (const auto& x : r["results"].elements()) {
			if (x["ok"].asBool()) std::printf("%s: %lld marks (%s) -> %s\n", x["name"].asStr().c_str(), (long long)x["marks"].asInt(),
			                                  x["language"].asStr().c_str(), x["lip"].asStr().c_str());
			else std::printf("%s: FAILED: %s\n", x["name"].asStr().c_str(), x["error"].asStr().c_str());
		}
		std::printf("%lld made, %lld failed\n", (long long)r["made"].asInt(), (long long)r["failed"].asInt());
		return r["ok"].asBool() ? 0 : 1;
	}

	std::fprintf(stderr, "error: unknown command %s (list, make, check or align)\n", cmd.c_str());
	return 2;
}

//---------------------------------------------------------------------------
// The window's API
//---------------------------------------------------------------------------
class LipsyncModule : public appserve::IModule {
public:
	LipsyncModule(krt::JobRunner& jobs, std::string engines) : jobs_(jobs), engines_(std::move(engines)) {}
	const char* name() const override { return "kagex-lipsync"; }

	void setProject(const Project& p)
	{
		std::lock_guard<std::mutex> lk(mu_);
		project_ = p;
		have_ = true;
		error_.clear();
		// what's there without the engine: the voice folders' sounds and their tracks
		voices_ = listVoices(p, {});
		linesRead_ = false;
		problems_.clear();
	}
	void setError(const std::string& e)
	{
		std::lock_guard<std::mutex> lk(mu_);
		have_ = false;
		error_ = e;
	}

	void registerApi(appserve::ApiRegistry& reg) override
	{
		reg.route("/api/lipsync/state", [this](const appserve::Request&) { return appserve::Response::json(state()); });

		// Opens another game (body: { path })
		reg.route("/api/lipsync/open", appserve::Affinity::Any, [this](const appserve::Request& req) {
			Project p;
			std::string err;
			if (!resolveProject(req.json()["path"].asStr(), p, err)) return appserve::Response::error(400, err);
			setProject(p);
			return appserve::Response::json(state());
		});

		// Reads the scripts' lines (a job: runs the game's engine)
		reg.route("/api/lipsync/read", [this](const appserve::Request&) {
			Project p;
			{
				std::lock_guard<std::mutex> lk(mu_);
				if (!have_) return appserve::Response::error(400, error_);
				p = project_;
			}
			const std::string engines = engines_;
			const bool started = jobs_.start("read", [this, p, engines](krt::Progress& pr) {
				std::vector<Voice> voices;
				std::vector<std::string> problems;
				std::string err;
				Json out = Json::object();
				if (!readGame(p, engines, pr, voices, problems, err)) {
					out.set("ok", Json(false));
					out.set("error", Json(err));
					std::lock_guard<std::mutex> lk(mu_);
					readError_ = err;
					return out;
				}
				std::lock_guard<std::mutex> lk(mu_);
				if (project_.root == p.root) {
					voices_ = std::move(voices);
					linesRead_ = true;
					problems_ = problems;
					readError_.clear();
				}
				out.set("ok", Json(true));
				out.set("problems", Json::array(problems));
				return out;
			});
			if (!started) return appserve::Response::error(409, "Busy: something is running");
			return appserve::Response::json(jobs_.status());
		});

		// Makes tracks (body: { voices: [{ name, text }] }; text empty: the voice's line)
		reg.route("/api/lipsync/make", [this](const appserve::Request& req) {
			std::vector<MakeItem> items;
			for (const auto& v : req.json()["voices"].elements()) items.push_back({ v["name"].asStr(), v["text"].asStr() });
			if (items.empty()) return appserve::Response::error(400, "Pick the voices first");
			std::vector<Voice> voices;
			fs::path root;
			{
				std::lock_guard<std::mutex> lk(mu_);
				if (!have_) return appserve::Response::error(400, error_);
				voices = voices_;
				root = project_.root;
			}
			const bool started = jobs_.start("make", [this, voices, items, root](krt::Progress& pr) mutable {
				Json r = makeTracks(voices, items, pr);
				std::lock_guard<std::mutex> lk(mu_);
				if (project_.root == root) mergeStates(voices);
				return r;
			});
			if (!started) return appserve::Response::error(409, "Busy: something is running");
			return appserve::Response::json(jobs_.status());
		});

		// Removes tracks (body: { names })
		reg.route("/api/lipsync/remove", appserve::Affinity::Any, [this](const appserve::Request& req) {
			std::lock_guard<std::mutex> lk(mu_);
			int removed = 0;
			for (const auto& n : req.json()["names"].elements()) {
				for (auto& v : voices_) {
					if (lower(v.name) != lower(n.asStr()) || v.lip.empty()) continue;
					std::error_code ec;
					if (fs::remove(v.lip, ec)) ++removed;
					refreshVoice(v);
				}
			}
			Json out = Json::object();
			out.set("removed", Json((int64_t)removed));
			return appserve::Response::json(out);
		});

		// A voice's sound, to play (?name=)
		reg.route("/api/lipsync/audio", appserve::Affinity::Any, [this](const appserve::Request& req) {
			const fs::path file = voiceFile(req.param("name"));
			std::string data;
			if (file.empty() || !krt::readFile(file, data)) return appserve::Response::error(404, "No such voice");
			const std::string ext = lower(krt::fromPath(file.extension()));
			const char* mime = ext == ".wav" ? "audio/wav" : ext == ".flac" ? "audio/flac" : "audio/ogg";
			return appserve::Response::bytes(std::move(data), mime);
		});

		// A voice's track, to show (?name=): [[ms, mouth, open]...]
		reg.route("/api/lipsync/track", appserve::Affinity::Any, [this](const appserve::Request& req) {
			fs::path lip;
			{
				std::lock_guard<std::mutex> lk(mu_);
				for (const auto& v : voices_) if (lower(v.name) == lower(req.param("name"))) lip = v.lip;
			}
			std::string data;
			if (lip.empty() || !krt::readFile(lip, data)) return appserve::Response::error(404, "No track");
			Json marks = Json::array();
			size_t pos = 0;
			while (pos < data.size()) {
				size_t end = data.find('\n', pos);
				if (end == std::string::npos) end = data.size();
				std::string line = data.substr(pos, end - pos);
				pos = end + 1;
				if (!line.empty() && line.back() == '\r') line.pop_back();
				if (line.empty() || line[0] == '#') continue;
				const size_t t1 = line.find('\t');
				if (t1 == std::string::npos) continue;
				const size_t t2 = line.find('\t', t1 + 1);
				Json m = Json::array();
				m.push(Json((int64_t)std::atoll(line.substr(0, t1).c_str())));
				m.push(Json(line.substr(t1 + 1, t2 == std::string::npos ? std::string::npos : t2 - t1 - 1)));
				m.push(Json((int64_t)(t2 == std::string::npos ? -1 : std::atoi(line.substr(t2 + 1).c_str()))));
				marks.push(std::move(m));
			}
			return appserve::Response::json(marks);
		});

		// Shows a file or folder in the file manager (body: { path })
		reg.route("/api/lipsync/reveal", appserve::Affinity::Any, [](const appserve::Request& req) {
			const std::string path = req.json()["path"].asStr();
			std::error_code ec;
			if (path.empty() || !fs::exists(krt::toPath(path), ec)) return appserve::Response::error(400, "Not found: " + path);
			RunOptions opt;
			opt.timeoutSeconds = 30;
			const bool dir = fs::is_directory(krt::toPath(path), ec);
#if defined(_WIN32)
			run("explorer", { dir ? path : "/select," + path }, opt);
#elif defined(__APPLE__)
			run("open", dir ? std::vector<std::string>{ path } : std::vector<std::string>{ "-R", path }, opt);
#else
			run("xdg-open", { dir ? path : krt::fromPath(krt::toPath(path).parent_path()) }, opt);
#endif
			return appserve::Response::json(Json::object());
		});
	}

private:
	Json state()
	{
		std::lock_guard<std::mutex> lk(mu_);
		Json out = Json::object();
		out.set("version", Json(KAGEX_RELEASE_VERSION));
		const fs::path data = lipsyncDataDir();
		std::error_code ec;
		out.set("models", Json(fs::is_directory(data / "pocketsphinx", ec) && fs::is_directory(data / "open_jtalk", ec)));
		out.set("modelsDir", Json(krt::fromPath(data)));
		if (!have_) { out.set("error", Json(error_)); return out; }
		Json p = Json::object();
		p.set("root", Json(krt::fromPath(project_.root)));
		p.set("data", Json(krt::fromPath(project_.data)));
		p.set("title", Json(project_.title));
		out.set("project", std::move(p));
		out.set("linesRead", Json(linesRead_));
		out.set("readError", Json(readError_));
		out.set("problems", Json::array(problems_));
		Json list = Json::array();
		for (const auto& v : voices_) list.push(voiceToJson(v));
		out.set("voices", std::move(list));
		return out;
	}

	// a job's voices' states into the list (the list may have been read again meanwhile)
	void mergeStates(const std::vector<Voice>& done)
	{
		std::map<std::string, const Voice*> byName;
		for (const auto& v : done) byName[lower(v.name)] = &v;
		for (auto& v : voices_) {
			auto it = byName.find(lower(v.name));
			if (it == byName.end()) continue;
			v.lip = it->second->lip;
			v.header = it->second->header;
			v.status = it->second->status;
		}
	}

	fs::path voiceFile(const std::string& name)
	{
		std::lock_guard<std::mutex> lk(mu_);
		for (const auto& v : voices_) if (lower(v.name) == lower(name)) return v.file;
		return {};
	}

	krt::JobRunner& jobs_;
	std::string engines_;
	std::mutex mu_;
	Project project_;
	bool have_ = false;
	std::string error_;
	std::vector<Voice> voices_;
	bool linesRead_ = false;
	std::string readError_;
	std::vector<std::string> problems_;
};

} // namespace

int main(int argc, char** argv)
{
	appserve::App app;
	app.options().appName = "kagex-lipsync";
	app.options().appVersion = KAGEX_RELEASE_VERSION;
	Options o;
	app.addOption({ "cli", "", "Run a command (list, make, check, align) instead of opening the window",
	                [&o](const std::string&) { o.cli = true; return true; } });
	app.addOption({ "json", "", "list, make, check: print JSON", [&o](const std::string&) { o.json = true; return true; } });
	app.addOption({ "project", "DIR", "The game (the folder with data/)", [&o](const std::string& v) { o.project = v; return true; } });
	app.addOption({ "all", "", "make: every voice the scripts give a line", [&o](const std::string&) { o.all = true; return true; } });
	app.addOption({ "character", "NAME", "make: the voices of this character", [&o](const std::string& v) { o.character = v; return true; } });
	app.addOption({ "stale", "", "make: the tracks whose voice changed since", [&o](const std::string&) { o.stale = true; return true; } });
	app.addOption({ "text", "TEXT", "make: the line (for one voice), instead of the scripts'", [&o](const std::string& v) { o.text = v; return true; } });
	app.addOption({ "force", "", "make: also remake current tracks, and replace hand-written ones", [&o](const std::string&) { o.force = true; return true; } });
	app.addOption({ "engines", "DIR", "Engine packages (kagex_engine_*.zip, or unpacked) to read the scripts with, instead of downloading",
	                [&o](const std::string& v) { o.engines = v; return true; } });
#ifdef _WIN32
	SetConsoleOutputCP(CP_UTF8);
#endif
	if (!app.parseArgs(argc, argv)) return app.exitCode();
	const auto& args = app.options().args;
	if (o.cli) return runCli(o, args);

	krt::hideConsoleIfOwned();
	app.addModule(appserve::makeFsModule());
	auto jobs = std::make_unique<krt::JobRunner>();
	krt::JobRunner& jobsRef = *jobs;
	app.addModule(std::move(jobs));
	auto module = std::make_unique<LipsyncModule>(jobsRef, o.engines);
	Project p;
	std::string err;
	if (resolveProject(!o.project.empty() ? o.project : args.empty() ? std::string() : args[0], p, err)) module->setProject(p);
	else module->setError(err);
	app.addModule(std::move(module));
	return app.run();
}
