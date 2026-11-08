#include "Loudness.h"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <mutex>
#include <sstream>
#include <thread>

#include "Archive.h"
#include "krt/app/Text.h"
#include "krt/audio/Audio.h"

#include <dr_flac.h>

namespace fs = std::filesystem;

namespace kr {

namespace {

// a biquad, run in direct form I over one channel
struct Biquad {
	double b0, b1, b2, a1, a2;
	double x1 = 0, x2 = 0, y1 = 0, y2 = 0;
	double step(double x)
	{
		const double y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
		x2 = x1; x1 = x;
		y2 = y1; y1 = y;
		return y;
	}
};

// BS.1770's K-weighting at any rate: the high shelf ("pre-filter") and the high pass ("RLB"),
// with the analogue prototypes' parameters that give the standard's 48 kHz coefficients
void kWeighting(int rate, Biquad& shelf, Biquad& highPass)
{
	const double pi = 3.14159265358979323846;
	{
		const double f0 = 1681.974450955533, G = 3.999843853973347, Q = 0.7071752369554196;
		const double K = std::tan(pi * f0 / rate);
		const double Vh = std::pow(10.0, G / 20.0);
		const double Vb = std::pow(Vh, 0.4996667741545416);
		const double a0 = 1.0 + K / Q + K * K;
		shelf.b0 = (Vh + Vb * K / Q + K * K) / a0;
		shelf.b1 = 2.0 * (K * K - Vh) / a0;
		shelf.b2 = (Vh - Vb * K / Q + K * K) / a0;
		shelf.a1 = 2.0 * (K * K - 1.0) / a0;
		shelf.a2 = (1.0 - K / Q + K * K) / a0;
	}
	{
		const double f0 = 38.13547087602444, Q = 0.5003270373238773;
		const double K = std::tan(pi * f0 / rate);
		const double a0 = 1.0 + K / Q + K * K;
		highPass.b0 = 1.0;
		highPass.b1 = -2.0;
		highPass.b2 = 1.0;
		highPass.a1 = 2.0 * (K * K - 1.0) / a0;
		highPass.a2 = (1.0 - K / Q + K * K) / a0;
	}
}

// a channel's weight: 1 for the front ones, 1.41 for the surrounds of 5.0/5.1, 0 for the LFE
double channelWeight(int channel, int channels)
{
	if (channels == 6) return channel == 3 ? 0.0 : channel >= 4 ? 1.41 : 1.0;
	if (channels == 5) return channel >= 3 ? 1.41 : 1.0;
	return 1.0;
}

std::string lower(std::string s)
{
	std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return (char)std::tolower(c); });
	return s;
}

} // namespace

double integratedLoudness(const float* x, size_t frames, int channels, int rate)
{
	if (!x || frames == 0 || channels <= 0 || rate <= 0) return -1000;
	// each channel's K-weighted squares, summed per 100 ms step
	const size_t step = (size_t)rate / 10;
	if (step == 0) return -1000;
	const size_t steps = (frames + step - 1) / step;
	std::vector<double> stepPower(steps, 0.0);   // the channels' weighted sum of squares per step
	for (int c = 0; c < channels; ++c) {
		const double w = channelWeight(c, channels);
		if (w == 0) continue;
		Biquad shelf{}, hp{};
		kWeighting(rate, shelf, hp);
		for (size_t i = 0; i < frames; ++i) {
			const double y = hp.step(shelf.step(x[i * channels + c]));
			stepPower[i / step] += w * y * y;
		}
	}
	auto loudnessOf = [](double meanPower) { return meanPower > 0 ? -0.691 + 10.0 * std::log10(meanPower) : -1000.0; };
	// 400 ms blocks, a step (75 % overlap) apart; a sound shorter than a block is one block
	std::vector<double> blocks;   // each block's mean power
	if (frames < step * 4) {
		double sum = 0;
		for (double p : stepPower) sum += p;
		blocks.push_back(sum / frames);
	} else {
		const size_t full = frames / step;   // whole steps; a partial last step isn't a block's
		for (size_t b = 0; b + 4 <= full; ++b)
			blocks.push_back((stepPower[b] + stepPower[b + 1] + stepPower[b + 2] + stepPower[b + 3]) / (step * 4.0));
	}
	// the absolute gate, then the relative one
	double sum = 0;
	size_t n = 0;
	for (double p : blocks)
		if (loudnessOf(p) > -70.0) { sum += p; ++n; }
	if (n == 0) return -1000;
	const double relative = loudnessOf(sum / n) - 10.0;
	sum = 0;
	n = 0;
	for (double p : blocks) {
		const double l = loudnessOf(p);
		if (l > -70.0 && l > relative) { sum += p; ++n; }
	}
	return n == 0 ? -1000 : loudnessOf(sum / n);
}

bool measureLoudness(const fs::path& file, double& lufs, std::string& error)
{
	krt::audio::Pcm pcm;
	if (lower(krt::fromPath(file.extension())) == ".flac") {
		std::string data;
		if (!krt::readFile(file, data)) { error = "Can't read " + krt::fromPath(file); return false; }
		drflac* f = drflac_open_memory(data.data(), data.size(), nullptr);
		if (!f) { error = "Not a FLAC file the decoder understands"; return false; }
		pcm.sampleRate = (int)f->sampleRate;
		pcm.channels = f->channels;
		pcm.data.resize((size_t)f->totalPCMFrameCount * f->channels);
		const drflac_uint64 got = drflac_read_pcm_frames_f32(f, f->totalPCMFrameCount, pcm.data.data());
		pcm.data.resize((size_t)got * f->channels);
		drflac_close(f);
	} else {
		krt::audio::Info info;
		if (!krt::audio::decode(file, pcm, info, error)) return false;
		if (info.format == krt::audio::Format::Opus && info.opusHeaderGainQ8 != 0)
			krt::audio::applyGain(pcm, info.opusHeaderGainQ8 / 256.0);   // the engine plays it with its gain
	}
	if (pcm.channels <= 0 || pcm.sampleRate <= 0 || pcm.frames() == 0) { error = "The sound has no samples"; return false; }
	lufs = integratedLoudness(pcm.data.data(), (size_t)pcm.frames(), pcm.channels, pcm.sampleRate);
	return true;
}

std::string loudnessKind(const std::string& relativePath)
{
	std::string p = lower(relativePath);
	std::replace(p.begin(), p.end(), '\\', '/');
	const size_t slash = p.rfind('/');
	if (slash == std::string::npos) return "";
	const size_t before = p.rfind('/', slash - 1);
	std::string folder = p.substr(before == std::string::npos ? 0 : before + 1, slash - (before == std::string::npos ? 0 : before + 1));
	if (folder.size() > 4 && folder.compare(folder.size() - 4, 4, ".xp3") == 0) folder.resize(folder.size() - 4);
	if (folder == "voice") return "voice";
	if (folder == "bgm") return "bgm";
	if (folder == "sound" || folder == "se") return "se";
	return "";
}

bool isMeasuredSound(const fs::path& file)
{
	const std::string e = lower(krt::fromPath(file.extension()));
	return e == ".ogg" || e == ".opus" || e == ".wav" || e == ".flac";
}

std::map<std::string, double> readLoudnessTable(const std::string& text)
{
	std::map<std::string, double> out;
	std::istringstream in(text);
	std::string line;
	while (std::getline(in, line)) {
		if (!line.empty() && line.back() == '\r') line.pop_back();
		if (line.size() >= 3 && (unsigned char)line[0] == 0xef && (unsigned char)line[1] == 0xbb && (unsigned char)line[2] == 0xbf) line = line.substr(3);
		size_t i = line.find_first_not_of(" \t");
		if (i == std::string::npos || line[i] == '#') continue;
		const size_t keyEnd = line.find_first_of(" \t", i);
		if (keyEnd == std::string::npos) continue;
		const std::string key = lower(line.substr(i, keyEnd - i));
		const size_t v = line.find_first_not_of(" \t", keyEnd);
		if (v == std::string::npos) continue;
		try { out[key] = std::stod(line.substr(v)); } catch (...) {}
	}
	return out;
}

std::vector<LoudnessEntry> loudnessReport(const fs::path& root, const std::map<std::string, double>& table,
                                          const std::map<std::string, double>& targets, double tolerance,
                                          const fs::path& cache, const std::function<bool()>& canceled)
{
	std::vector<LoudnessEntry> out;
	std::error_code ec;
	if (!fs::is_directory(root, ec)) return out;
	for (auto it = fs::recursive_directory_iterator(root, fs::directory_options::skip_permission_denied, ec);
	     it != fs::recursive_directory_iterator(); it.increment(ec)) {
		if (ec) break;
		if (!it->is_regular_file(ec) || !isMeasuredSound(it->path())) continue;
		LoudnessEntry e;
		e.path = krt::fromPath(it->path().lexically_relative(root));
		std::replace(e.path.begin(), e.path.end(), '\\', '/');
		e.name = krt::fromPath(it->path().filename());
		e.kind = loudnessKind(e.path);
		out.push_back(std::move(e));
	}
	std::sort(out.begin(), out.end(), [](const LoudnessEntry& a, const LoudnessEntry& b) { return a.path < b.path; });

	// measured in parallel; a file's value cached by its content
	std::atomic<size_t> next{ 0 };
	auto work = [&]() {
		for (;;) {
			const size_t i = next++;
			if (i >= out.size() || (canceled && canceled())) return;
			LoudnessEntry& e = out[i];
			const fs::path file = root / krt::toPath(e.path);
			std::string hex, err;
			fs::path cached;
			if (!cache.empty() && sha256File(file, hex, err)) {
				cached = cache / (hex + ".txt");
				std::string text;
				if (krt::readFile(cached, text)) {
					try { e.lufs = std::stod(text); e.measured = true; } catch (...) {}
				}
			}
			if (!e.measured) {
				e.measured = measureLoudness(file, e.lufs, e.error);
				if (e.measured && !cached.empty()) {
					char buf[32];
					std::snprintf(buf, sizeof(buf), "%.3f", e.lufs);
					std::error_code ec2;
					fs::create_directories(cache, ec2);
					krt::writeFile(cached, buf);
				}
			}
		}
	};
	const unsigned n = std::max(1u, std::min(8u, std::thread::hardware_concurrency()));
	std::vector<std::thread> threads;
	for (unsigned t = 0; t < n; ++t) threads.emplace_back(work);
	for (auto& t : threads) t.join();

	for (auto& e : out) {
		const std::string name = lower(e.name);
		const std::string stem = lower(krt::fromPath(krt::toPath(e.name).stem()));
		auto own = table.find(name);
		if (own == table.end()) own = table.find(stem);
		e.ownLine = own != table.end();
		auto kind = table.find(e.kind);
		e.gainNow = e.ownLine ? own->second : (!e.kind.empty() && kind != table.end()) ? kind->second : 0.0;
		e.gainApplies = lower(krt::fromPath(krt::toPath(e.name).extension())) != ".wav";
		auto t = targets.find(e.kind);
		e.hasTarget = !e.kind.empty() && t != targets.end();
		if (e.hasTarget && e.measured && e.lufs > -70) {
			e.target = t->second;
			const double played = e.lufs + (e.gainApplies ? e.gainNow : 0.0);
			e.far = std::fabs(played - e.target) > tolerance;
			e.newGain = std::round((e.target - e.lufs) * 10.0) / 10.0;
		}
	}
	return out;
}

fs::path findLoudnessTable(const fs::path& data)
{
	std::error_code ec;
	if (fs::is_regular_file(data / "loudness.csv", ec)) return data / "loudness.csv";
	for (auto it = fs::recursive_directory_iterator(data, fs::directory_options::skip_permission_denied, ec);
	     it != fs::recursive_directory_iterator(); it.increment(ec)) {
		if (ec) break;
		if (it->is_regular_file(ec) && lower(krt::fromPath(it->path().filename())) == "loudness.csv") return it->path();
	}
	return {};
}

std::string loudnessReportText(const std::vector<LoudnessEntry>& entries)
{
	std::string t = "# file\tkind\tLUFS\tas played\ttarget\tgain\tnote\n";
	char buf[64];
	for (const auto& e : entries) {
		t += e.path + "\t" + (e.kind.empty() ? "-" : e.kind) + "\t";
		if (!e.measured) { t += "-\t-\t-\t-\t" + e.error + "\n"; continue; }
		if (e.lufs <= -70) { t += "silent\t-\t-\t-\t\n"; continue; }
		std::snprintf(buf, sizeof(buf), "%.1f\t%.1f\t", e.lufs, e.lufs + (e.gainApplies ? e.gainNow : 0.0));
		t += buf;
		if (e.hasTarget) { std::snprintf(buf, sizeof(buf), "%.1f\t", e.target); t += buf; } else t += "-\t";
		std::snprintf(buf, sizeof(buf), "%+.1f\t", e.gainNow);
		t += buf;
		std::string note;
		if (!e.gainApplies) note = "WAV: the engine applies no gain";
		else if (e.ownLine) note = "its own line in loudness.csv";
		if (e.far) note += std::string(note.empty() ? "" : "; ") + (e.ownLine || !e.gainApplies ? "far from its target" : "brought to its target");
		t += note + "\n";
	}
	return t;
}

} // namespace kr
