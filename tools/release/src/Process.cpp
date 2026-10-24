#include "Process.h"

#include <chrono>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <thread>

#include "krt/app/Text.h"

#ifdef _WIN32
#include <windows.h>
#else
#include <cerrno>
#include <csignal>
#include <fcntl.h>
#include <poll.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
extern char** environ;
#endif

namespace fs = std::filesystem;

namespace kr {

namespace {

// Splits the output into lines for onLine, and collects all of it
class LineSink {
public:
	explicit LineSink(const RunOptions& opt) : opt_(opt) {}
	void add(const char* p, size_t n)
	{
		out_.append(p, n);
		if (!opt_.onLine) return;
		pending_.append(p, n);
		size_t start = 0, nl;
		while ((nl = pending_.find('\n', start)) != std::string::npos) {
			std::string line = pending_.substr(start, nl - start);
			if (!line.empty() && line.back() == '\r') line.pop_back();
			opt_.onLine(line);
			start = nl + 1;
		}
		pending_.erase(0, start);
	}
	void finish()
	{
		if (opt_.onLine && !pending_.empty()) opt_.onLine(pending_);
		pending_.clear();
	}
	std::string take() { return std::move(out_); }

private:
	const RunOptions& opt_;
	std::string out_, pending_;
};

#ifdef _WIN32
std::wstring widen(const std::string& s)
{
	if (s.empty()) return {};
	int n = MultiByteToWideChar(CP_UTF8, 0, s.data(), (int)s.size(), nullptr, 0);
	std::wstring w(n, L'\0');
	MultiByteToWideChar(CP_UTF8, 0, s.data(), (int)s.size(), w.data(), n);
	return w;
}

std::string narrow(const std::wstring& w)
{
	if (w.empty()) return {};
	int n = WideCharToMultiByte(CP_UTF8, 0, w.data(), (int)w.size(), nullptr, 0, nullptr, nullptr);
	std::string s(n, '\0');
	WideCharToMultiByte(CP_UTF8, 0, w.data(), (int)w.size(), s.data(), n, nullptr, nullptr);
	return s;
}

// The quoting CommandLineToArgvW (and the C runtime) undo
std::wstring quoteArg(const std::wstring& a)
{
	if (!a.empty() && a.find_first_of(L" \t\n\v\"") == std::wstring::npos) return a;
	std::wstring q = L"\"";
	for (size_t i = 0;; ++i) {
		size_t backslashes = 0;
		while (i < a.size() && a[i] == L'\\') { ++i; ++backslashes; }
		if (i == a.size()) { q.append(backslashes * 2, L'\\'); break; }
		if (a[i] == L'"') { q.append(backslashes * 2 + 1, L'\\'); q += L'"'; }
		else { q.append(backslashes, L'\\'); q += a[i]; }
	}
	q += L'"';
	return q;
}
#endif

} // namespace

std::string getEnv(const std::string& name)
{
#ifdef _WIN32
	std::wstring w = widen(name);
	DWORD n = GetEnvironmentVariableW(w.c_str(), nullptr, 0);
	if (!n) return {};
	std::wstring v(n, L'\0');
	n = GetEnvironmentVariableW(w.c_str(), v.data(), n);
	v.resize(n);
	return narrow(v);
#else
	const char* v = std::getenv(name.c_str());
	return v ? v : "";
#endif
}

fs::path findProgram(const std::string& name)
{
	std::error_code ec;
	fs::path p = krt::toPath(name);
	if (p.has_parent_path()) return fs::exists(p, ec) ? p : fs::path();
#ifdef _WIN32
	const char sep = ';';
	std::vector<std::string> exts = { "" , ".exe", ".cmd", ".bat", ".com" };
	if (p.has_extension()) exts = { "" };
#else
	const char sep = ':';
	std::vector<std::string> exts = { "" };
#endif
	const std::string path = getEnv("PATH");
	size_t start = 0;
	while (start <= path.size()) {
		size_t end = path.find(sep, start);
		if (end == std::string::npos) end = path.size();
		std::string dir = path.substr(start, end - start);
		start = end + 1;
		if (dir.empty()) continue;
		for (const auto& ext : exts) {
			fs::path cand = krt::toPath(dir) / krt::toPath(name + ext);
			if (fs::is_regular_file(cand, ec)) {
#ifndef _WIN32
				if (access(cand.c_str(), X_OK) != 0) continue;
#endif
				return cand;
			}
		}
	}
	return {};
}

RunResult run(const std::string& program, const std::vector<std::string>& args, const RunOptions& opt)
{
	RunResult r;
	const fs::path exe = findProgram(program);
	if (exe.empty()) {
		r.output = program + ": not found";
		return r;
	}
	LineSink sink(opt);
	const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(opt.timeoutSeconds);

#ifdef _WIN32
	std::wstring cmd;
	const std::wstring ext = exe.extension().wstring();
	const bool batch = _wcsicmp(ext.c_str(), L".bat") == 0 || _wcsicmp(ext.c_str(), L".cmd") == 0;
	{
		std::wstring line = quoteArg(exe.wstring());
		for (const auto& a : args) line += L" " + quoteArg(widen(a));
		cmd = batch ? L"cmd.exe /d /s /c \"" + line + L"\"" : line;
	}

	// the environment block: ours with the overrides
	std::wstring envBlock;
	if (!opt.env.empty()) {
		std::vector<std::wstring> vars;
		if (LPWCH base = GetEnvironmentStringsW()) {
			for (LPWCH p = base; *p; p += wcslen(p) + 1) vars.emplace_back(p);
			FreeEnvironmentStringsW(base);
		}
		for (const auto& [k, v] : opt.env) {
			const std::wstring key = widen(k) + L"=";
			bool replaced = false;
			for (auto& var : vars) {
				if (var.size() >= key.size() && _wcsnicmp(var.c_str(), key.c_str(), key.size()) == 0) {
					var = key + widen(v);
					replaced = true;
				}
			}
			if (!replaced) vars.push_back(key + widen(v));
		}
		for (const auto& var : vars) { envBlock += var; envBlock += L'\0'; }
		envBlock += L'\0';
	}

	SECURITY_ATTRIBUTES sa = { sizeof(sa), nullptr, TRUE };
	HANDLE readPipe = nullptr, writePipe = nullptr;
	if (!CreatePipe(&readPipe, &writePipe, &sa, 0)) {
		r.output = "could not create a pipe";
		return r;
	}
	SetHandleInformation(readPipe, HANDLE_FLAG_INHERIT, 0);
	HANDLE nul = CreateFileW(L"NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa, OPEN_EXISTING, 0, nullptr);

	STARTUPINFOW si = {};
	si.cb = sizeof(si);
	si.dwFlags = STARTF_USESTDHANDLES;
	si.hStdInput = nul;
	si.hStdOutput = writePipe;
	si.hStdError = writePipe;
	PROCESS_INFORMATION pi = {};
	const std::wstring dir = opt.workDir.empty() ? std::wstring() : opt.workDir.wstring();
	std::vector<wchar_t> cmdBuf(cmd.begin(), cmd.end());
	cmdBuf.push_back(L'\0');

	// a job, so that stopping it stops what it started too (gradle's java, cmd's children)
	HANDLE job = CreateJobObjectW(nullptr, nullptr);
	if (job) {
		JOBOBJECT_EXTENDED_LIMIT_INFORMATION li = {};
		li.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
		SetInformationJobObject(job, JobObjectExtendedLimitInformation, &li, sizeof(li));
	}
	const BOOL ok = CreateProcessW(nullptr, cmdBuf.data(), nullptr, nullptr, TRUE,
	                               CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT | CREATE_SUSPENDED,
	                               envBlock.empty() ? nullptr : (LPVOID)envBlock.c_str(),
	                               dir.empty() ? nullptr : dir.c_str(), &si, &pi);
	CloseHandle(writePipe);
	if (nul != INVALID_HANDLE_VALUE) CloseHandle(nul);
	if (!ok) {
		CloseHandle(readPipe);
		if (job) CloseHandle(job);
		r.output = krt::fromPath(exe) + ": could not be started (error " + std::to_string(GetLastError()) + ")";
		return r;
	}
	if (job) AssignProcessToJobObject(job, pi.hProcess);
	ResumeThread(pi.hThread);
	CloseHandle(pi.hThread);
	r.started = true;

	std::mutex mu;
	std::thread reader([&]() {
		char buf[4096];
		DWORD n = 0;
		while (ReadFile(readPipe, buf, sizeof(buf), &n, nullptr) && n > 0) {
			std::lock_guard<std::mutex> lk(mu);
			sink.add(buf, n);
		}
	});
	bool stopped = false;
	while (WaitForSingleObject(pi.hProcess, 100) == WAIT_TIMEOUT) {
		const bool late = opt.timeoutSeconds > 0 && std::chrono::steady_clock::now() > deadline;
		if (late || (opt.canceled && opt.canceled())) {
			r.timedOut = late;
			stopped = true;
			if (job) TerminateJobObject(job, 1); else TerminateProcess(pi.hProcess, 1);
			WaitForSingleObject(pi.hProcess, 5000);
			break;
		}
	}
	DWORD code = 1;
	GetExitCodeProcess(pi.hProcess, &code);
	r.exitCode = stopped ? -1 : (int)code;
	CloseHandle(pi.hProcess);
	if (job) CloseHandle(job);   // also ends anything it left running
	reader.join();
	CloseHandle(readPipe);
#else
	int fds[2];
	if (pipe(fds) != 0) {
		r.output = "could not create a pipe";
		return r;
	}
	// everything the child needs is prepared before fork (only exec-safe calls after it)
	std::vector<std::string> argStore;
	argStore.push_back(exe.string());
	for (const auto& a : args) argStore.push_back(a);
	std::vector<char*> argv;
	for (auto& a : argStore) argv.push_back(a.data());
	argv.push_back(nullptr);

	std::vector<std::string> envStore;
	for (char** e = environ; *e; ++e) {
		std::string var = *e;
		bool overridden = false;
		for (const auto& kv : opt.env)
			if (var.compare(0, kv.first.size() + 1, kv.first + "=") == 0) overridden = true;
		if (!overridden) envStore.push_back(std::move(var));
	}
	for (const auto& [k, v] : opt.env) envStore.push_back(k + "=" + v);
	std::vector<char*> envp;
	for (auto& e : envStore) envp.push_back(e.data());
	envp.push_back(nullptr);
	const std::string dir = opt.workDir.empty() ? std::string() : opt.workDir.string();

	const pid_t pid = fork();
	if (pid < 0) {
		close(fds[0]);
		close(fds[1]);
		r.output = "could not start a process";
		return r;
	}
	if (pid == 0) {
		setpgid(0, 0);
		const int nul = open("/dev/null", O_RDONLY);
		if (nul >= 0) dup2(nul, 0);
		dup2(fds[1], 1);
		dup2(fds[1], 2);
		close(fds[0]);
		close(fds[1]);
		if (!dir.empty() && chdir(dir.c_str()) != 0) _exit(126);
		execve(argv[0], argv.data(), envp.data());
		const char msg[] = "exec failed\n";
		(void)!write(2, msg, sizeof(msg) - 1);
		_exit(127);
	}
	setpgid(pid, pid);
	close(fds[1]);
	r.started = true;
	fcntl(fds[0], F_SETFL, fcntl(fds[0], F_GETFL) | O_NONBLOCK);

	bool stopped = false, eof = false;
	int status = 0;
	bool exited = false;
	std::chrono::steady_clock::time_point exitTime;
	while (!eof || !exited) {
		pollfd pfd = { fds[0], POLLIN, 0 };
		if (!eof) poll(&pfd, 1, 100);
		else std::this_thread::sleep_for(std::chrono::milliseconds(20));
		if (!eof) {
			char buf[4096];
			for (;;) {
				const ssize_t n = read(fds[0], buf, sizeof(buf));
				if (n > 0) { sink.add(buf, (size_t)n); continue; }
				if (n == 0) eof = true;
				else if (errno != EAGAIN && errno != EINTR) eof = true;
				break;
			}
		}
		if (!exited && waitpid(pid, &status, WNOHANG) == pid) {
			exited = true;
			exitTime = std::chrono::steady_clock::now();
		}
		if (exited && !eof) {
			// drain what is left in the pipe, but not for what the program left running
			// (a daemon it started can hold the pipe open)
			if (std::chrono::steady_clock::now() - exitTime > std::chrono::seconds(2)) break;
			continue;
		}
		const bool late = opt.timeoutSeconds > 0 && std::chrono::steady_clock::now() > deadline;
		if (!exited && !stopped && (late || (opt.canceled && opt.canceled()))) {
			r.timedOut = late;
			stopped = true;
			kill(-pid, SIGTERM);
			for (int i = 0; i < 50 && waitpid(pid, &status, WNOHANG) != pid; ++i)
				std::this_thread::sleep_for(std::chrono::milliseconds(100));
			kill(-pid, SIGKILL);
			waitpid(pid, &status, 0);
			exited = true;
			eof = true;
		}
		if (exited && eof) break;
	}
	close(fds[0]);
	if (stopped) r.exitCode = -1;
	else if (WIFEXITED(status)) r.exitCode = WEXITSTATUS(status);
	else r.exitCode = 128 + (WIFSIGNALED(status) ? WTERMSIG(status) : 0);
#endif
	sink.finish();
	r.output = sink.take();
	return r;
}

} // namespace kr
