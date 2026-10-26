//---------------------------------------------------------------------------
// kagex-release: packages a KAGEX game for Windows, Linux, Steam, macOS, the web, Android and iOS
//
//   kagex-release [<release.json or project folder>]          opens the window
//   kagex-release --cli init  [<project folder>] [--force]    writes release.json with the defaults
//   kagex-release --cli check [<release.json>] [--json]       the settings, and what this computer can build
//   kagex-release --cli plan  [<release.json>] [--json]       what a build would make
//   kagex-release --cli build [<release.json>] [--json]       builds the packages
//   kagex-release --cli keygen <file>                         makes a key for encrypting compiled scenarios
//
// check, plan and build take --platform=a,b (only those platforms); build takes --engines=DIR
// (engine packages to use instead of downloading them) and --keep-work.
// Without a path it uses the current folder, or else the folder above the tool (a KAGEX
// package keeps the tool in tools/). CLI exit codes: 0 = fine, 1 = problems found, 2 = failed.
//---------------------------------------------------------------------------
#include <appserve/appserve.h>

#include <cstdio>
#include <memory>
#include <mutex>

#include "Build.h"
#include "Host.h"
#include "Plan.h"
#include "Project.h"
#include "Scenes.h"
#include "Settings.h"
#include "Subprocess.h"
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
	bool cli = false;
	bool force = false;
	bool json = false;
	bool keepWork = false;
	std::string engines;             // --engines=DIR
	std::vector<std::string> only;   // --platform=a,b
};

// The settings file and project for a path given on the command line (or none)
struct Target {
	fs::path file;       // release.json
	Project  project;
};

bool resolveTarget(const std::string& arg, Target& t, std::string& error)
{
	std::error_code ec;
	std::vector<fs::path> starts;
	if (!arg.empty()) starts.push_back(krt::toPath(arg));
	else {
		starts.push_back(fs::current_path(ec));
		starts.push_back(krt::selfPath().parent_path());
	}
	std::string firstError;
	for (const auto& start : starts) {
		Project p;
		std::string err;
		if (!findProject(start, p, err)) {
			if (firstError.empty()) firstError = err;
			continue;
		}
		t.project = std::move(p);
		t.file = (!arg.empty() && fs::is_regular_file(start, ec)) ? fs::absolute(start, ec) : t.project.root / "release.json";
		return true;
	}
	error = firstError;
	return false;
}

// release.json with the defaults filled in (just the defaults when there is no file yet)
bool loadEffective(const Target& t, Json& settings, std::string& error, bool* existed = nullptr)
{
	const Json defaults = defaultSettings(t.project);
	std::error_code ec;
	const bool exists = fs::exists(t.file, ec);
	if (existed) *existed = exists;
	if (!exists) { settings = defaults; return true; }
	Json loaded;
	if (!loadSettings(t.file, loaded, error)) return false;
	settings = withDefaults(loaded, defaults);
	return true;
}

Json issuesToJson(const std::vector<Issue>& issues)
{
	Json a = Json::array();
	for (const auto& i : issues) {
		Json o = Json::object();
		o.set("level", Json(i.level));
		o.set("field", Json(i.field));
		o.set("message", Json(i.message));
		a.push(std::move(o));
	}
	return a;
}

Json statusToJson(const PlatformStatus& st)
{
	Json o = Json::object();
	o.set("id", Json(st.id));
	o.set("possible", Json(st.possible));
	Json reqs = Json::array();
	for (const auto& r : st.requirements) {
		Json q = Json::object();
		q.set("name", Json(r.name));
		q.set("ok", Json(r.ok));
		q.set("detail", Json(r.detail));
		reqs.push(std::move(q));
	}
	o.set("requirements", std::move(reqs));
	o.set("notes", Json::array(st.notes));
	return o;
}

Json projectToJson(const Project& p)
{
	Json o = Json::object();
	o.set("root", Json(krt::fromPath(p.root)));
	o.set("data", Json(krt::fromPath(p.data)));
	o.set("framework", Json(krt::fromPath(p.framework)));
	o.set("frameworkInData", Json(p.frameworkInData));
	o.set("title", Json(p.title));
	o.set("version", Json(p.version));
	o.set("engine", Json(krt::fromPath(p.engine)));
	o.set("icon", Json(krt::fromPath(p.icon)));
	return o;
}

std::string humanSize(long long n)
{
	char buf[32];
	if (n < 1024 * 1024) std::snprintf(buf, sizeof(buf), "%.1f KB", n / 1024.0);
	else if (n < 1024LL * 1024 * 1024) std::snprintf(buf, sizeof(buf), "%.1f MB", n / 1048576.0);
	else std::snprintf(buf, sizeof(buf), "%.2f GB", n / 1073741824.0);
	return buf;
}

bool selected(const Options& o, const std::string& id)
{
	if (o.only.empty()) return true;
	for (const auto& x : o.only) if (x == id) return true;
	return false;
}

//---------------------------------------------------------------------------
// CLI
//---------------------------------------------------------------------------
int runCli(const Options& o, const std::vector<std::string>& args)
{
	if (args.empty()) {
		std::fprintf(stderr, "usage: kagex-release --cli init|check|plan [<path>] (see --help)\n");
		return 2;
	}
	const std::string cmd = args[0];
	const std::string path = args.size() > 1 ? args[1] : std::string();
	std::string err;
	if (cmd == "keygen") {
		if (path.empty()) { std::fprintf(stderr, "usage: kagex-release --cli keygen <file>\n"); return 2; }
		if (!makeSceneKey(krt::toPath(path), err)) { std::fprintf(stderr, "error: %s\n", err.c_str()); return 2; }
		std::printf("Wrote a new key to %s: name it in release.json's scenes.keyFile, and keep it out of the game's repository\n", path.c_str());
		return 0;
	}
	Target t;
	if (!resolveTarget(path, t, err)) { std::fprintf(stderr, "error: %s\n", err.c_str()); return 2; }

	if (cmd == "init") {
		std::error_code ec;
		if (fs::exists(t.file, ec) && !o.force) {
			std::fprintf(stderr, "error: %s is already there (--force replaces it)\n", krt::fromPath(t.file).c_str());
			return 2;
		}
		if (!saveSettings(t.file, defaultSettings(t.project), err)) { std::fprintf(stderr, "error: %s\n", err.c_str()); return 2; }
		std::printf("Wrote %s\n", krt::fromPath(t.file).c_str());
		return 0;
	}

	Json s;
	bool existed = false;
	if (!loadEffective(t, s, err, &existed)) { std::fprintf(stderr, "error: %s\n", err.c_str()); return 2; }
	if (!o.only.empty()) {
		// --platform picks the platforms for this run
		for (const auto& pl : platforms()) {
			Json& p = s["platforms"][pl.id];
			p.set("enabled", Json(selected(o, pl.id)));
		}
	}

	if (cmd == "check") {
		const auto issues = validate(s, t.project);
		std::vector<PlatformStatus> statuses;
		for (const auto& pl : platforms())
			if (flag(s, std::string("platforms.") + pl.id + ".enabled")) statuses.push_back(checkPlatform(pl.id, s, t.project));
		bool problems = hasErrors(issues);
		for (const auto& st : statuses) if (!st.possible) problems = true;
		if (o.json) {
			Json out = Json::object();
			out.set("file", Json(krt::fromPath(t.file)));
			out.set("exists", Json(existed));
			out.set("issues", issuesToJson(issues));
			Json sts = Json::array();
			for (const auto& st : statuses) sts.push(statusToJson(st));
			out.set("platforms", std::move(sts));
			std::printf("%s\n", out.dump(1).c_str());
			return problems ? 1 : 0;
		}
		std::printf("%s%s\n", krt::fromPath(t.file).c_str(), existed ? "" : " (not saved yet: the defaults)");
		for (const auto& i : issues)
			std::printf("  %s: %s: %s\n", i.level.c_str(), i.field.c_str(), i.message.c_str());
		if (issues.empty()) std::printf("  The settings are fine\n");
		for (const auto& st : statuses) {
			std::string title = st.id;
			for (const auto& pl : platforms()) if (st.id == pl.id) title = pl.title;
			std::printf("%s: %s\n", title.c_str(), st.possible ? "can be built here" : "can't be built here");
			for (const auto& r : st.requirements)
				std::printf("  [%s] %s: %s\n", r.ok ? "ok" : "missing", r.name.c_str(), r.detail.c_str());
			for (const auto& n : st.notes) std::printf("  note: %s\n", n.c_str());
		}
		return problems ? 1 : 0;
	}

	if (cmd == "plan") {
		const Json plan = makePlan(s, t.project);
		if (o.json) { std::printf("%s\n", plan.dump(1).c_str()); return 0; }
		const Json& d = plan["data"];
		std::printf("Game files: %lld (%s), %lld excluded; framework: %s\n", (long long)d["files"].asInt(),
		            humanSize(d["bytes"].asInt()).c_str(), (long long)d["excluded"].asInt(), d["framework"].asStr().c_str());
		std::printf("Converted: %lld images, %lld sounds\n", (long long)d["convertImages"].asInt(), (long long)d["convertAudio"].asInt());
		if (d["scenes"]["compile"].asBool())
			std::printf("Compiled: %lld scripts in !scnlist.txt%s\n", (long long)d["scenes"]["scripts"].asInt(),
			            d["scenes"]["encrypted"].asBool() ? ", encrypted" : "");
		for (const auto& out : plan["outputs"].elements()) {
			std::printf("%s:\n", out["title"].asStr().c_str());
			if (!out["folder"].asStr().empty()) std::printf("  folder  %s/\n", out["folder"].asStr().c_str());
			if (!out["package"].asStr().empty()) std::printf("  package %s\n", out["package"].asStr().c_str());
			for (const auto& c : out["contents"].elements()) std::printf("    %s\n", c.asStr().c_str());
		}
		return 0;
	}

	if (cmd == "build") {
		BuildOptions bo;
		bo.only = o.only;
		bo.engines = krt::toPath(o.engines);
		bo.keepWork = o.keepWork;
		krt::ConsoleProgress progress(o.json);
		const Json r = build(s, t.project, bo, progress);
		progress.finish();
		if (o.json) { std::printf("%s\n", r.dump(1).c_str()); return r["ok"].asBool() ? 0 : 1; }
		if (r.has("error")) std::fprintf(stderr, "error: %s\n", r["error"].asStr().c_str());
		for (const auto& out : r["outputs"].elements()) {
			if (out["ok"].asBool())
				std::printf("%s: %s\n", out["title"].asStr().c_str(),
				            (out["package"].asStr().empty() ? out["folder"] : out["package"]).asStr().c_str());
			else
				std::printf("%s: FAILED: %s\n", out["title"].asStr().c_str(), out["error"].asStr().c_str());
		}
		for (const auto& n : r["notes"].elements()) std::printf("note: %s\n", n.asStr().c_str());
		if (r.has("check")) {
			const Json& c = r["check"];
			std::printf("Test run: %s\n", c["message"].asStr().c_str());
			for (const auto& e : c["errors"].elements()) std::printf("  %s\n", e.asStr().c_str());
		}
		return r["ok"].asBool() ? 0 : 1;
	}

	std::fprintf(stderr, "error: unknown command %s (init, check, plan, build or keygen)\n", cmd.c_str());
	return 2;
}

//---------------------------------------------------------------------------
// The window's API
//---------------------------------------------------------------------------
class ReleaseModule : public appserve::IModule {
public:
	ReleaseModule(krt::JobRunner& jobs, Target target, bool haveTarget, std::string targetError)
		: jobs_(jobs), target_(std::move(target)), have_(haveTarget), targetError_(std::move(targetError)) {}
	const char* name() const override { return "kagex-release"; }

	void registerApi(appserve::ApiRegistry& reg) override
	{
		// The project, the settings (with the defaults filled in) and the platforms
		reg.route("/api/release/state", [this](const appserve::Request&) { return state(); });

		// Opens another project or release.json (body: { path })
		reg.route("/api/release/open", [this](const appserve::Request& req) {
			Target t;
			std::string err;
			if (!resolveTarget(req.json()["path"].asStr(), t, err)) return appserve::Response::error(400, err);
			{
				std::lock_guard<std::mutex> lk(mu_);
				target_ = std::move(t);
				have_ = true;
				targetError_.clear();
			}
			return state();
		});

		// Checks settings from the screen (body: { settings }): problems and the plan
		reg.route("/api/release/check", [this](const appserve::Request& req) {
			if (!have_) return appserve::Response::error(400, targetError_);
			const Json s = withDefaults(req.json()["settings"], defaultSettings(target_.project));
			Json out = Json::object();
			out.set("issues", issuesToJson(validate(s, target_.project)));
			out.set("plan", makePlan(s, target_.project));
			return appserve::Response::json(out);
		});

		// What this computer can build (body: { settings, platform }). Runs programs, so not on
		// the main thread
		reg.route("/api/release/host", appserve::Affinity::Any, [this](const appserve::Request& req) {
			Project p;
			{
				std::lock_guard<std::mutex> lk(mu_);
				if (!have_) return appserve::Response::error(400, targetError_);
				p = target_.project;
			}
			const Json s = withDefaults(req.json()["settings"], defaultSettings(p));
			const std::string only = req.json()["platform"].asStr();
			Json out = Json::array();
			for (const auto& pl : platforms())
				if (only.empty() || only == pl.id) out.push(statusToJson(checkPlatform(pl.id, s, p)));
			return appserve::Response::json(out);
		});

		// Builds (body: { settings, platforms }): a job; GET /api/job and the job/joblog events
		// report on it
		reg.route("/api/release/build", [this](const appserve::Request& req) {
			if (!have_) return appserve::Response::error(400, targetError_);
			const Json s = withDefaults(req.json()["settings"], defaultSettings(target_.project));
			BuildOptions bo;
			for (const auto& p : req.json()["platforms"].elements()) bo.only.push_back(p.asStr());
			// passwords typed for this build (keystores): passed on, never saved
			for (const auto& [k, v] : req.json()["secrets"].members()) bo.secrets[k] = v.asStr();
			const Project project = target_.project;
			const bool started = jobs_.start("build", [s, project, bo](krt::Progress& p) {
				return build(s, project, bo, p);
			});
			if (!started) return appserve::Response::error(409, "A build is running");
			return appserve::Response::json(jobs_.status());
		});

		// Shows a folder in the file manager (body: { path })
		reg.route("/api/release/reveal", appserve::Affinity::Any, [](const appserve::Request& req) {
			const std::string path = req.json()["path"].asStr();
			std::error_code ec;
			if (path.empty() || !fs::exists(krt::toPath(path), ec)) return appserve::Response::error(400, "Not found: " + path);
			RunOptions opt;
			opt.timeoutSeconds = 30;
#if defined(_WIN32)
			run("explorer", { fs::is_directory(krt::toPath(path), ec) ? path : "/select," + path }, opt);
#elif defined(__APPLE__)
			run("open", fs::is_directory(krt::toPath(path), ec) ? std::vector<std::string>{ path } : std::vector<std::string>{ "-R", path }, opt);
#else
			run("xdg-open", { fs::is_directory(krt::toPath(path), ec) ? path : krt::fromPath(krt::toPath(path).parent_path()) }, opt);
#endif
			return appserve::Response::json(Json::object());
		});

		// Makes a key for encrypting compiled scenarios (body: { path }, relative to the project)
		reg.route("/api/release/keygen", [this](const appserve::Request& req) {
			if (!have_) return appserve::Response::error(400, targetError_);
			const fs::path file = target_.project.root / krt::toPath(req.json()["path"].asStr());
			std::string err;
			if (!makeSceneKey(file, err)) return appserve::Response::error(400, err);
			Json out = Json::object();
			out.set("file", Json(krt::fromPath(file.lexically_normal())));
			return appserve::Response::json(out);
		});

		// Saves release.json (body: { settings })
		reg.route("/api/release/save", [this](const appserve::Request& req) {
			if (!have_) return appserve::Response::error(400, targetError_);
			std::string err;
			if (!saveSettings(target_.file, req.json()["settings"], err)) return appserve::Response::error(400, err);
			Json out = Json::object();
			out.set("file", Json(krt::fromPath(target_.file)));
			return appserve::Response::json(out);
		});
	}

private:
	appserve::Response state()
	{
		std::lock_guard<std::mutex> lk(mu_);
		Json out = Json::object();
		out.set("version", Json(KAGEX_RELEASE_VERSION));
		out.set("host", Json(hostId()));
		out.set("scnfile", Json(canEncryptScenes()));
		Json pls = Json::array();
		for (const auto& pl : platforms()) {
			Json o = Json::object();
			o.set("id", Json(pl.id));
			o.set("title", Json(pl.title));
			pls.push(std::move(o));
		}
		out.set("platforms", std::move(pls));
		if (!have_) {
			out.set("error", Json(targetError_));
			return appserve::Response::json(out);
		}
		Json s;
		std::string err;
		bool existed = false;
		if (!loadEffective(target_, s, err, &existed)) {
			out.set("error", Json(err));
			s = defaultSettings(target_.project);
		}
		out.set("file", Json(krt::fromPath(target_.file)));
		out.set("exists", Json(existed));
		out.set("project", projectToJson(target_.project));
		out.set("defaults", defaultSettings(target_.project));
		out.set("settings", std::move(s));
		return appserve::Response::json(out);
	}

	krt::JobRunner& jobs_;
	std::mutex      mu_;
	Target          target_;
	bool            have_;
	std::string     targetError_;
};

} // namespace

int main(int argc, char** argv)
{
	appserve::App app;
	app.options().appName = "kagex-release";
	app.options().appVersion = KAGEX_RELEASE_VERSION;
	Options o;
	app.addOption({ "cli", "", "Run a command (init, check, plan, build, keygen) instead of opening the window",
	                [&o](const std::string&) { o.cli = true; return true; } });
	app.addOption({ "force", "", "init: replace an existing release.json",
	                [&o](const std::string&) { o.force = true; return true; } });
	app.addOption({ "json", "", "check, plan, build: print JSON",
	                [&o](const std::string&) { o.json = true; return true; } });
	app.addOption({ "engines", "DIR", "build: engine packages (kagex_engine_*.zip, or unpacked) to use instead of downloading them",
	                [&o](const std::string& v) { o.engines = v; return true; } });
	app.addOption({ "keep-work", "", "build: keep the staged files (<output>/.work)",
	                [&o](const std::string&) { o.keepWork = true; return true; } });
	app.addOption({ "platform", "LIST", "check, plan, build: only these platforms (windows,linux,steam,macos,web,android,ios)",
	                [&o](const std::string& v) {
		                size_t start = 0;
		                while (start <= v.size()) {
			                size_t c = v.find(',', start);
			                if (c == std::string::npos) c = v.size();
			                const std::string id = krt::trim(v.substr(start, c - start));
			                start = c + 1;
			                if (id.empty()) continue;
			                bool known = false;
			                for (const auto& pl : platforms()) if (id == pl.id) known = true;
			                if (!known) { std::fprintf(stderr, "unknown platform: %s\n", id.c_str()); return false; }
			                o.only.push_back(id);
		                }
		                return true;
	                } });
#ifdef _WIN32
	SetConsoleOutputCP(CP_UTF8);
#endif
	if (!app.parseArgs(argc, argv)) return app.exitCode();
	const auto& args = app.options().args;
	if (o.cli) return runCli(o, args);

	Target t;
	std::string err;
	const bool have = resolveTarget(args.empty() ? std::string() : args[0], t, err);
	krt::hideConsoleIfOwned();
	app.addModule(appserve::makeFsModule());
	auto jobs = std::make_unique<krt::JobRunner>();
	krt::JobRunner& jobsRef = *jobs;
	app.addModule(std::move(jobs));
	app.addModule(std::make_unique<ReleaseModule>(jobsRef, std::move(t), have, err));
	return app.run();
}
