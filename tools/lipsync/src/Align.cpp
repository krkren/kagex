#include "Align.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <map>

#include "Subprocess.h"
#include "dr_flac.h"            // implemented in kagex-release's Media.cpp
#include "krt/app/Text.h"
#include "krt/audio/Audio.h"

#include <pocketsphinx.h>
#include "mecab.h"
extern "C" {
// in this order: each needs the ones before it
#include "njd.h"
#include "jpcommon.h"
#include "mecab2njd.h"
#include "njd2jpcommon.h"
#include "njd_set_accent_phrase.h"
#include "njd_set_accent_type.h"
#include "njd_set_digit.h"
#include "njd_set_long_vowel.h"
#include "njd_set_pronunciation.h"
#include "njd_set_unvoiced_vowel.h"
#include "text2mecab.h"
}

#ifdef _WIN32
#include <windows.h>
#endif

namespace fs = std::filesystem;

namespace kr {

namespace {

const int kRate = 16000;     // the acoustic model's
const int kFrameMs = 10;     // PocketSphinx's frames (frate 100)

// KAGEnvCharacterEx.tjs's lipSyncHalfLevel and lipSyncOpenLevel: how open a mark is
const double kHalfLevel = 0.03, kOpenLevel = 0.12;

// The mouth each sound makes: a vowel, two for a diphthong (half its time each), "n" where the
// lips close; anything else is "-". English as CMUdict writes it (ARPAbet, stress left out)
const std::map<std::string, std::string> kEnglishMouths = {
	{ "AA", "a" }, { "AE", "a" }, { "AH", "a" }, { "AO", "o" }, { "AW", "au" }, { "AY", "ai" }, { "EH", "e" },
	{ "ER", "e" }, { "EY", "ei" }, { "IH", "i" }, { "IY", "i" }, { "OW", "ou" }, { "OY", "oi" }, { "UH", "u" },
	{ "UW", "u" }, { "W", "u" }, { "M", "n" }, { "B", "n" }, { "P", "n" },
};
// Japanese is aligned with the same English model, each of OpenJTalk's phonemes as the English
// sounds nearest it; its vowels come back as these
const std::map<std::string, std::string> kJapaneseMouths = {
	{ "AA", "a" }, { "IY", "i" }, { "UW", "u" }, { "EH", "e" }, { "OW", "o" }, { "M", "n" }, { "B", "n" }, { "P", "n" },
};
const std::map<std::string, std::string> kJapaneseSounds = {
	{ "a", "AA" }, { "i", "IY" }, { "u", "UW" }, { "e", "EH" }, { "o", "OW" },
	{ "A", "AA" }, { "I", "IY" }, { "U", "UW" }, { "E", "EH" }, { "O", "OW" },   // devoiced
	{ "k", "K" }, { "ky", "K Y" }, { "kw", "K W" }, { "g", "G" }, { "gy", "G Y" }, { "gw", "G W" },
	{ "s", "S" }, { "sh", "SH" }, { "z", "Z" }, { "j", "JH" }, { "t", "T" }, { "ts", "T S" }, { "ty", "T Y" },
	{ "ch", "CH" }, { "d", "D" }, { "dy", "D Y" }, { "n", "N" }, { "ny", "N Y" }, { "N", "N" }, { "h", "HH" },
	{ "hy", "HH Y" }, { "f", "F" }, { "b", "B" }, { "by", "B Y" }, { "p", "P" }, { "py", "P Y" }, { "m", "M" },
	{ "my", "M Y" }, { "y", "Y" }, { "r", "D" }, { "ry", "D Y" }, { "w", "W" }, { "v", "V" },
	{ "cl", "" },   // the pause before a doubled consonant: part of what follows
};

// A path the C libraries can fopen: on Windows, the short (8.3) name, which is plain ASCII
std::string narrowPath(const fs::path& p)
{
#ifdef _WIN32
	const std::wstring w = p.wstring();
	const DWORD n = GetShortPathNameW(w.c_str(), nullptr, 0);
	if (n > 0) {
		std::wstring s(n, L'\0');
		if (GetShortPathNameW(w.c_str(), s.data(), n) > 0) {
			s.resize(wcslen(s.c_str()));
			const int m = WideCharToMultiByte(CP_ACP, 0, s.c_str(), -1, nullptr, 0, nullptr, nullptr);
			std::string out(m > 0 ? m : 0, '\0');
			if (m > 0) WideCharToMultiByte(CP_ACP, 0, s.c_str(), -1, out.data(), m, nullptr, nullptr);
			out.resize(strlen(out.c_str()));
			return out;
		}
	}
	return p.string();
#else
	return p.string();
#endif
}

// The voice as one channel (the channels' average, as the engine's getSoundLevel hears it)
bool decodeVoice(const fs::path& file, std::vector<float>& mono, int& rate, std::string& error)
{
	krt::audio::Pcm pcm;
	std::string ext = krt::fromPath(file.extension());
	std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char c) { return (char)std::tolower(c); });
	if (ext == ".flac") {
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
	if (pcm.channels <= 0 || pcm.sampleRate <= 0 || pcm.frames() == 0) { error = "The voice has no samples"; return false; }
	rate = pcm.sampleRate;
	const size_t n = (size_t)pcm.frames();
	mono.assign(n, 0.0f);
	for (size_t i = 0; i < n; ++i) {
		float s = 0;
		for (int c = 0; c < pcm.channels; ++c) s += pcm.data[i * pcm.channels + c];
		mono[i] = s / pcm.channels;
	}
	return true;
}

// The voice at 16 kHz, 16-bit: a windowed sinc low-pass below the new Nyquist frequency
std::vector<int16_t> resample16k(const std::vector<float>& x, int rate)
{
	const double ratio = (double)kRate / rate;
	const size_t n = (size_t)std::floor(x.size() * ratio);
	std::vector<int16_t> out(n);
	const double pi = 3.14159265358979323846;
	const double fc = std::min(1.0, ratio) * 0.92;   // the cutoff, of the input's Nyquist
	const int half = rate == kRate ? 0 : (int)std::ceil(16 / fc);
	for (size_t i = 0; i < n; ++i) {
		const double pos = i / ratio;
		double acc;
		if (half == 0) acc = x[i];
		else {
			acc = 0;
			const long c = (long)std::floor(pos);
			for (long k = c - half + 1; k <= c + half; ++k) {
				if (k < 0 || k >= (long)x.size()) continue;
				const double d = pos - k;
				const double w = 0.5 + 0.5 * std::cos(pi * d / half);
				const double t = fc * d;
				const double sinc = std::fabs(t) < 1e-9 ? 1.0 : std::sin(pi * t) / (pi * t);
				acc += x[k] * fc * sinc * w;
			}
		}
		out[i] = (int16_t)std::lround(std::clamp(acc, -1.0, 1.0) * 32767);
	}
	return out;
}

std::vector<std::string> splitWords(const std::string& s)
{
	std::vector<std::string> out;
	std::string cur;
	for (char c : s) {
		if (c == ' ') { if (!cur.empty()) out.push_back(cur); cur.clear(); }
		else cur += c;
	}
	if (!cur.empty()) out.push_back(cur);
	return out;
}

// OpenJTalk's front end: a Japanese line's phonemes, as it would say it
class Jtalk {
public:
	~Jtalk()
	{
		if (!loaded_) return;
		Mecab_clear(&mecab_);
		NJD_clear(&njd_);
		JPCommon_clear(&jpcommon_);
	}
	bool load(const fs::path& dic, std::string& error)
	{
		if (loaded_) return true;
		Mecab_initialize(&mecab_);
		NJD_initialize(&njd_);
		JPCommon_initialize(&jpcommon_);
		loaded_ = true;
		if (!Mecab_load(&mecab_, narrowPath(dic).c_str())) {
			error = "Can't load the OpenJTalk dictionary from " + krt::fromPath(dic);
			return false;
		}
		return true;
	}
	/// The phonemes, "pau" where it would pause and "sil" at the ends
	std::vector<std::string> phonemes(const std::string& text)
	{
		std::vector<char> buff(text.size() * 8 + 1024);
		text2mecab(buff.data(), text.c_str());
		Mecab_analysis(&mecab_, buff.data());
		mecab2njd(&njd_, Mecab_get_feature(&mecab_), Mecab_get_size(&mecab_));
		njd_set_pronunciation(&njd_);
		njd_set_digit(&njd_);
		njd_set_accent_phrase(&njd_);
		njd_set_accent_type(&njd_);
		njd_set_unvoiced_vowel(&njd_);
		njd_set_long_vowel(&njd_);
		njd2jpcommon(&jpcommon_, &njd_);
		JPCommon_make_label(&jpcommon_);
		std::vector<std::string> out;
		const int n = JPCommon_get_label_size(&jpcommon_);
		char** labels = JPCommon_get_label_feature(&jpcommon_);
		for (int i = 0; i < n; ++i) {
			// a full-context label: "xx^xx-<phoneme>+xx=..."
			const char* a = std::strchr(labels[i], '-');
			const char* b = a ? std::strchr(a, '+') : nullptr;
			if (a && b) out.emplace_back(a + 1, b - a - 1);
		}
		JPCommon_refresh(&jpcommon_);
		NJD_refresh(&njd_);
		Mecab_refresh(&mecab_);
		return out;
	}

private:
	Mecab mecab_;
	NJD njd_;
	JPCommon jpcommon_;
	bool loaded_ = false;
};

int utf8Next(const std::string& s, size_t& i)
{
	const unsigned char c = (unsigned char)s[i++];
	if (c < 0x80) return c;
	int n = c >= 0xF0 ? 3 : c >= 0xE0 ? 2 : c >= 0xC0 ? 1 : 0;
	int cp = c & (0x3F >> n);
	while (n-- > 0 && i < s.size()) cp = (cp << 6) | ((unsigned char)s[i++] & 0x3F);
	return cp;
}

} // namespace

fs::path lipsyncDataDir()
{
	const std::string env = getEnv("KAGEX_LIPSYNC_DATA");
	if (!env.empty()) return krt::toPath(env);
	return krt::selfPath().parent_path() / "lipsync";
}

bool isJapaneseText(const std::string& text)
{
	for (size_t i = 0; i < text.size();) {
		const int cp = utf8Next(text, i);
		if ((cp >= 0x3040 && cp <= 0x30FF) || (cp >= 0x3400 && cp <= 0x4DBF) || (cp >= 0x4E00 && cp <= 0x9FFF) ||
		    (cp >= 0xFF66 && cp <= 0xFF9F))
			return true;
	}
	return false;
}

struct Aligner::Impl {
	fs::path data;
	ps_decoder_t* ps = nullptr;
	Jtalk jtalk;
	bool jtalkLoaded = false;
	int words = 0;   // Japanese words added to the dictionary so far (each line's are new)

	~Impl()
	{
		if (ps) ps_free(ps);
	}
};

Aligner::Aligner(fs::path dataDir) : impl_(std::make_unique<Impl>())
{
	impl_->data = std::move(dataDir);
}

Aligner::~Aligner() = default;

bool Aligner::open(std::string& error)
{
	if (impl_->ps) return true;
	const fs::path hmm = impl_->data / "pocketsphinx" / "en-us";
	const fs::path dict = impl_->data / "pocketsphinx" / "cmudict-en-us.dict";
	std::error_code ec;
	if (!fs::is_directory(hmm, ec) || !fs::is_regular_file(dict, ec)) {
		error = "The speech models aren't at " + krt::fromPath(impl_->data) + " (lipsync/ beside kagex-lipsync, or KAGEX_LIPSYNC_DATA)";
		return false;
	}
	err_set_logfp(nullptr);
	ps_config_t* config = ps_config_init(nullptr);
	ps_config_set_str(config, "hmm", narrowPath(hmm).c_str());
	ps_config_set_str(config, "dict", narrowPath(dict).c_str());
	ps_config_set_str(config, "lm", nullptr);
	ps_config_set_bool(config, "bestpath", 0);
	ps_config_set_int(config, "samprate", kRate);
	impl_->ps = ps_init(config);
	ps_config_free(config);
	if (!impl_->ps) { error = "PocketSphinx couldn't load its model from " + krt::fromPath(hmm); return false; }
	return true;
}

bool Aligner::align(const fs::path& voice, const std::string& text, AlignResult& out, std::string& error)
{
	out = AlignResult();
	if (!open(error)) return false;
	std::vector<float> mono;
	int rate = 0;
	if (!decodeVoice(voice, mono, rate, error)) return false;
	out.seconds = (double)mono.size() / rate;
	const std::vector<int16_t> pcm = resample16k(mono, rate);

	// the words to align, each in the dictionary
	ps_decoder_t* ps = impl_->ps;
	std::vector<std::string> words;
	const bool japanese = isJapaneseText(text);
	out.language = japanese ? "ja" : "en";
	if (japanese) {
		if (!impl_->jtalkLoaded) {
			if (!impl_->jtalk.load(impl_->data / "open_jtalk", error)) return false;
			impl_->jtalkLoaded = true;
		}
		// a word for each stretch between pauses, its sounds the English ones nearest
		std::string phones;
		auto addWord = [&]() {
			if (phones.empty()) return;
			const std::string name = "kagexja" + std::to_string(++impl_->words);
			ps_add_word(ps, name.c_str(), phones.c_str(), 0);
			words.push_back(name);
			out.sounds += (out.sounds.empty() ? "" : " | ") + phones;
			phones.clear();
		};
		for (const auto& p : impl_->jtalk.phonemes(text)) {
			if (p == "sil" || p == "pau") { addWord(); continue; }
			const auto it = kJapaneseSounds.find(p);
			if (it == kJapaneseSounds.end()) { out.warnings.push_back("a sound OpenJTalk gave isn't known: " + p); continue; }
			if (it->second.empty()) continue;
			phones += (phones.empty() ? "" : " ") + it->second;
		}
		addWord();
	} else {
		// English words, as CMUdict has them (lower case, with apostrophes)
		std::string cur;
		auto flush = [&]() {
			while (!cur.empty() && cur.back() == '\'') cur.pop_back();
			while (!cur.empty() && cur.front() == '\'') cur.erase(cur.begin());
			if (cur.empty()) return;
			char* p = ps_lookup_word(ps, cur.c_str());
			if (p) {
				words.push_back(cur);
				out.sounds += (out.sounds.empty() ? "" : " | ") + std::string(p);
				std::free(p);
			} else {
				out.warnings.push_back("not in the dictionary, left out: " + cur);
			}
			cur.clear();
		};
		for (size_t i = 0; i < text.size();) {
			const int cp = utf8Next(text, i);
			if ((cp >= 'a' && cp <= 'z') || (cp >= 'A' && cp <= 'Z') || (cp >= '0' && cp <= '9') || cp == '\'')
				cur += (char)std::tolower(cp);
			else if (cp == 0x2019 && !cur.empty())   // a typographic apostrophe
				cur += '\'';
			else
				flush();
		}
		flush();
	}
	if (words.empty()) { error = "The line has no words to align"; return false; }
	std::string joined;
	for (const auto& w : words) joined += (joined.empty() ? "" : " ") + w;

	// the words first, then their sounds (PocketSphinx's own two passes)
	if (ps_set_align_text(ps, joined.c_str()) < 0) { error = "PocketSphinx couldn't take the line"; return false; }
	if (ps_start_utt(ps) < 0 || ps_process_raw(ps, pcm.data(), pcm.size(), 0, 1) < 0 || ps_end_utt(ps) < 0) {
		error = "The voice doesn't fit its line: type what it says, in the language it says it";
		return false;
	}
	if (ps_set_alignment(ps, nullptr) < 0 || ps_start_utt(ps) < 0 || ps_process_raw(ps, pcm.data(), pcm.size(), 0, 1) < 0 ||
	    ps_end_utt(ps) < 0) {
		error = "The voice doesn't fit its line: type what it says, in the language it says it";
		return false;
	}
	ps_alignment_t* al = ps_get_alignment(ps);
	if (!al) { error = "The voice doesn't fit its line: type what it says, in the language it says it"; return false; }

	// the marks: each sound's mouth from its start (a diphthong's second half from its middle)
	const auto& mouths = japanese ? kJapaneseMouths : kEnglishMouths;
	std::vector<std::pair<long, std::string>> marks;   // (sample at the voice's rate, mouth)
	marks.push_back({ 0, "-" });
	const double perFrame = (double)rate * kFrameMs / 1000;
	for (ps_alignment_iter_t* w = ps_alignment_words(al); w; w = ps_alignment_iter_next(w)) {
		for (ps_alignment_iter_t* p = ps_alignment_iter_children(w); p; p = ps_alignment_iter_next(p)) {
			int start = 0, duration = 0;
			ps_alignment_iter_seg(p, &start, &duration);
			const char* nm = ps_alignment_iter_name(p);
			std::string name = nm ? nm : "";
			while (!name.empty() && std::isdigit((unsigned char)name.back())) name.pop_back();
			const auto it = mouths.find(name);
			const std::string m = it == mouths.end() ? "-" : it->second;
			const long s = (long)std::lround(start * perFrame), e = (long)std::lround((start + duration) * perFrame);
			if (m.size() == 2) {
				marks.push_back({ s, m.substr(0, 1) });
				marks.push_back({ (s + e) / 2, m.substr(1, 1) });
			} else {
				marks.push_back({ s, m });
			}
		}
	}
	const long total = (long)mono.size();
	marks.push_back({ total, "-" });
	for (size_t k = 0; k + 1 < marks.size(); ++k) {
		long s = std::clamp(marks[k].first, 0L, total), e = std::clamp(marks[k + 1].first, 0L, total);
		double sum = 0;
		for (long i = s; i < e; ++i) sum += (double)mono[i] * mono[i];
		const double rms = e > s ? std::sqrt(sum / (e - s)) : 0.0;
		const std::string& m = marks[k].second;
		const int open = m == "n" ? 0 : rms > kOpenLevel ? 2 : rms > kHalfLevel ? 1 : 0;
		const int ms = (int)std::lround(s * 1000.0 / rate);
		while (!out.marks.empty() && out.marks.back().ms >= ms) out.marks.pop_back();   // the later of two at one time
		if (out.marks.empty() || out.marks.back().mouth != m || out.marks.back().open != open) out.marks.push_back({ ms, m, open });
	}
	return true;
}

} // namespace kr
