//---------------------------------------------------------------------------
// Running other programs (curl, java, gradle, xcodebuild, codesign, the engine for the check).
// Not named Process.h: on Windows that would shadow the C runtime's <process.h>
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <functional>
#include <string>
#include <vector>

namespace kr {

struct RunResult {
	bool        started = false;   ///< false: the program couldn't be started (output has why)
	int         exitCode = -1;
	bool        timedOut = false;
	std::string output;            ///< stdout and stderr together

	bool ok() const { return started && !timedOut && exitCode == 0; }
};

struct RunOptions {
	std::filesystem::path workDir;                           ///< empty: the current folder
	std::vector<std::pair<std::string, std::string>> env;    ///< added to (or replacing in) the environment
	int timeoutSeconds = 0;                                  ///< 0: none
	/// each line of output as it arrives (the output is collected either way)
	std::function<void(const std::string&)> onLine;
	/// polled while it runs; true stops the program
	std::function<bool()> canceled;
};

/// Runs program (a path, or a name looked up in PATH) with args, and waits for it
RunResult run(const std::string& program, const std::vector<std::string>& args, const RunOptions& opt = {});

/// The full path of a program in PATH (with .exe/.cmd/.bat on Windows), or empty
std::filesystem::path findProgram(const std::string& name);

/// An environment variable (UTF-8), or empty
std::string getEnv(const std::string& name);

} // namespace kr
