#include "Scripts.h"

#include <algorithm>
#include <cctype>
#include <cstring>
#include <map>
#include <regex>
#include <set>
#include <stdexcept>

#include "Host.h"
#include "Subprocess.h"
#include "krt/app/Progress.h"
#include "krt/app/Text.h"

namespace fs = std::filesystem;

namespace kr {

namespace {

std::string lower(std::string s)
{
	for (auto& c : s) c = (char)std::tolower((unsigned char)c);
	return s;
}

bool validUtf8(const std::string& s)
{
	size_t i = 0;
	while (i < s.size()) {
		const unsigned char c = (unsigned char)s[i];
		size_t n = c < 0x80 ? 1 : (c >> 5) == 6 ? 2 : (c >> 4) == 14 ? 3 : (c >> 3) == 30 ? 4 : 0;
		if (!n || i + n > s.size()) return false;
		for (size_t k = 1; k < n; ++k) if (((unsigned char)s[i + k] >> 6) != 2) return false;
		i += n;
	}
	return true;
}

// UTF-16LE (from a BOM's end) to UTF-8, and back with the BOM
std::string utf16ToUtf8(const std::string& in, size_t from)
{
	std::string out;
	for (size_t i = from; i + 1 < in.size(); i += 2) {
		uint32_t c = (unsigned char)in[i] | ((unsigned char)in[i + 1] << 8);
		if (c >= 0xD800 && c < 0xDC00 && i + 3 < in.size()) {
			const uint32_t lo = (unsigned char)in[i + 2] | ((unsigned char)in[i + 3] << 8);
			if (lo >= 0xDC00 && lo < 0xE000) { c = 0x10000 + ((c - 0xD800) << 10) + (lo - 0xDC00); i += 2; }
		}
		if (c < 0x80) out += (char)c;
		else if (c < 0x800) { out += (char)(0xC0 | c >> 6); out += (char)(0x80 | (c & 63)); }
		else if (c < 0x10000) { out += (char)(0xE0 | c >> 12); out += (char)(0x80 | ((c >> 6) & 63)); out += (char)(0x80 | (c & 63)); }
		else { out += (char)(0xF0 | c >> 18); out += (char)(0x80 | ((c >> 12) & 63)); out += (char)(0x80 | ((c >> 6) & 63)); out += (char)(0x80 | (c & 63)); }
	}
	return out;
}

std::string utf8ToUtf16(const std::string& s)
{
	std::string out = "\xFF\xFE";
	size_t i = 0;
	while (i < s.size()) {
		const unsigned char c = (unsigned char)s[i];
		const size_t n = c < 0x80 ? 1 : (c >> 5) == 6 ? 2 : (c >> 4) == 14 ? 3 : 4;
		uint32_t cp = n == 1 ? c : n == 2 ? (c & 31) : n == 3 ? (c & 15) : (c & 7);
		for (size_t k = 1; k < n && i + k < s.size(); ++k) cp = (cp << 6) | ((unsigned char)s[i + k] & 63);
		i += n;
		auto put = [&](uint32_t u) { out += (char)(u & 0xff); out += (char)(u >> 8); };
		if (cp >= 0x10000) { cp -= 0x10000; put(0xD800 + (cp >> 10)); put(0xDC00 + (cp & 0x3ff)); }
		else put(cp);
	}
	return out;
}

void put16(std::string& s, int v) { s += (char)(v & 0xff); s += (char)((v >> 8) & 0xff); }
void put32(std::string& s, uint32_t v) { for (int k = 0; k < 4; ++k) s += (char)((v >> (8 * k)) & 0xff); }
void put64(std::string& s, uint64_t v) { for (int k = 0; k < 8; ++k) s += (char)((v >> (8 * k)) & 0xff); }

bool fitsInt32(int64_t v) { return v >= INT32_MIN && v <= INT32_MAX; }

} // namespace

//---------------------------------------------------------------------------
// Scanning a script with TJS's lexical rules (tjsLex.cpp)
//---------------------------------------------------------------------------
namespace tjs {

namespace {

struct Token {
	enum Kind { Ident, Integer, Real, String, Regex, Octet, Punct } kind;
	size_t at, end;
	std::string text;   ///< Ident and Punct
	int64_t value = 0;  ///< Integer
};

bool identChar(unsigned char c) { return std::isalnum(c) || c == '_' || c >= 0x80; }
bool space(unsigned char c) { return c <= 0x20; }
int digitValue(unsigned char c, int base)
{
	int d = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : 99;
	return d < base ? d : -1;
}

// operators longest first (only some matter here: '/', ';', brackets, + - * <<)
const char* const kOperators[] = {
	">>>=", "<<=", ">>=", ">>>", "===", "!==", "<->", "&&=", "||=", "...",
	"<<", ">>", "==", "!=", "<=", ">=", "&&", "||", "++", "--", "+=", "-=", "*=", "/=", "\\=", "%=",
	"&=", "|=", "^=", "=>", "->", "::",
};

// the words after which a '/' starts a regular expression rather than dividing
const std::set<std::string> kBeforeExpression = {
	"return", "typeof", "delete", "in", "instanceof", "case", "throw", "void", "new", "else", "do",
	"incontextof", "invalidate", "isvalid", "int", "real", "string", "if", "while",
};

class Scanner {
public:
	Scanner(const std::string& s, bool sjis, Scan& out) : s_(s), n_(s.size()), sjis_(sjis), out_(out) {}

	// the tokens from i to the end, or (inner) past the '}' closing an embedded ${...}
	size_t tokens(size_t i, bool inner, std::vector<Token>& list)
	{
		int braces = 0;
		while (i < n_) {
			const unsigned char c = (unsigned char)s_[i];
			if (space(c)) { ++i; continue; }
			if (c == '/' && at(i + 1) == '/') {
				while (i < n_ && s_[i] != '\n') i = next(i);
				continue;
			}
			if (c == '/' && at(i + 1) == '*') {
				// block comments nest
				i += 2;
				int level = 0;
				for (;;) {
					if (i + 1 >= n_) { out_.ok = false; return n_; }
					if (s_[i] == '/' && s_[i + 1] == '*') { ++level; i += 2; continue; }
					if (s_[i] == '*' && s_[i + 1] == '/') {
						i += 2;
						if (level-- == 0) break;
						continue;
					}
					i = next(i);
				}
				continue;
			}
			if (inner && c == '}' && braces == 0) return i + 1;
			if (c == '"' || c == '\'') {
				const size_t end = string(i, false);
				list.push_back({ Token::String, i, end });
				i = end;
				continue;
			}
			if (c == '@') {
				size_t j = i + 1;
				while (j < n_ && space((unsigned char)s_[j])) ++j;
				if (j < n_ && (s_[j] == '"' || s_[j] == '\'')) {
					const size_t end = string(j, true);
					list.push_back({ Token::String, i, end });
					i = end;
					continue;
				}
				// @set (...), @if (...), @else, @endif: decided when compiling, not code
				j = i + 1;
				while (j < n_ && identChar((unsigned char)s_[j])) j = next(j);
				size_t k = j;
				while (k < n_ && (s_[k] == ' ' || s_[k] == '\t')) ++k;
				if (k < n_ && s_[k] == '(') {
					int depth = 0;
					for (; k < n_; k = next(k)) {
						if (s_[k] == '(') ++depth;
						else if (s_[k] == ')' && --depth == 0) { ++k; break; }
					}
					j = k;
				}
				i = j;
				continue;
			}
			if (std::isdigit(c) || (c == '.' && std::isdigit((unsigned char)at(i + 1)))) {
				i = number(i, list);
				continue;
			}
			if (identChar(c)) {
				size_t j = i;
				while (j < n_ && identChar((unsigned char)s_[j])) j = next(j);
				list.push_back({ Token::Ident, i, j, s_.substr(i, j - i) });
				i = j;
				continue;
			}
			if (c == '<' && at(i + 1) == '%') {
				const size_t end = s_.find("%>", i + 2);
				if (end == std::string::npos) { out_.ok = false; return n_; }
				list.push_back({ Token::Octet, i, end + 2 });
				i = end + 2;
				continue;
			}
			if (c == '/' && regexHere(list)) {
				// to the first '/' not escaped by '\', then its flags
				size_t j = i + 1;
				bool backslash = false;
				for (;;) {
					if (j >= n_) { out_.ok = false; return n_; }
					if (s_[j] == '\\') { backslash = !backslash; j = next(j); continue; }
					if (s_[j] == '/' && !backslash) break;
					backslash = false;
					j = next(j);
				}
				++j;
				while (j < n_ && s_[j] >= 'a' && s_[j] <= 'z') ++j;
				list.push_back({ Token::Regex, i, j });
				i = j;
				continue;
			}
			std::string op(1, (char)c);
			for (const char* o : kOperators) {
				const size_t len = std::strlen(o);
				if (s_.compare(i, len, o) == 0) { op = o; break; }
			}
			if (op == "{") ++braces;
			else if (op == "}") --braces;
			list.push_back({ Token::Punct, i, i + op.size(), op });
			i += op.size();
		}
		if (inner) out_.ok = false;
		return n_;
	}

private:
	char at(size_t i) const { return i < n_ ? s_[i] : '\0'; }

	// past one character: two bytes for a Shift_JIS double-byte one
	size_t next(size_t i) const
	{
		const unsigned char c = (unsigned char)s_[i];
		if (sjis_ && ((c >= 0x81 && c <= 0x9F) || (c >= 0xE0 && c <= 0xFC)) && i + 1 < n_) return i + 2;
		return i + 1;
	}

	// a string from its quote at i, past its closing quote; an embeddable one (@"...") has code
	// in ${...}
	size_t string(size_t i, bool embeddable)
	{
		const char quote = s_[i];
		size_t j = i + 1;
		while (j < n_) {
			if (s_[j] == '\\') {
				j = j + 1 < n_ ? next(j + 1) : n_;
				continue;
			}
			if (s_[j] == quote) return j + 1;
			if (embeddable && s_[j] == '$' && at(j + 1) == '{') {
				std::vector<Token> inner;
				++embedded_;
				j = tokens(j + 2, true, inner);
				--embedded_;
				continue;
			}
			j = next(j);
		}
		out_.ok = false;
		return n_;
	}

	size_t number(size_t i, std::vector<Token>& list)
	{
		auto real = [&](size_t j) {
			// the rest of a real: digits, the point, the exponent and its sign
			while (j < n_ && (std::isalnum((unsigned char)s_[j]) || s_[j] == '.' ||
			                  ((s_[j] == '+' || s_[j] == '-') && (s_[j - 1] == 'e' || s_[j - 1] == 'E' || s_[j - 1] == 'p' || s_[j - 1] == 'P'))))
				++j;
			list.push_back({ Token::Real, i, j });
			return j;
		};
		auto integer = [&](size_t j, int base) {
			uint64_t v = 0;
			int d;
			while (j < n_ && (d = digitValue((unsigned char)s_[j], base)) >= 0) {
				v = v * (uint64_t)base + (uint64_t)d;
				++j;
			}
			if (j < n_ && (s_[j] == '.' || (base == 10 ? (s_[j] == 'e' || s_[j] == 'E') : (s_[j] == 'p' || s_[j] == 'P'))))
				return real(j);
			Token t{ Token::Integer, i, j };
			t.value = (int64_t)v;
			list.push_back(t);
			out_.integers.push_back({ i, j - i, t.value });
			// the compiler folds a constant ${...} into the string around it
			if (embedded_ && !fitsInt32(t.value)) out_.wideFold = true;
			return j;
		};
		const char c = s_[i], m = at(i + 1);
		if (c == '.') return real(i + 1);
		if (c == '0' && (m == 'x' || m == 'X')) return integer(i + 2, 16);
		if (c == '0' && (m == 'b' || m == 'B')) return integer(i + 2, 2);
		if (c == '0' && std::isdigit((unsigned char)m)) return integer(i + 1, 8);
		return integer(i, 10);
	}

	// where a '/' starts a regular expression: where an operand is expected
	static bool regexHere(const std::vector<Token>& list)
	{
		if (list.empty()) return true;
		const Token& t = list.back();
		switch (t.kind) {
		case Token::Ident: return kBeforeExpression.count(t.text) > 0;
		case Token::Punct: return t.text != ")" && t.text != "]";
		default: return false;
		}
	}

	const std::string& s_;
	const size_t n_;
	const bool sjis_;
	Scan& out_;
	int embedded_ = 0;   ///< inside an embeddable string's ${...}
};

bool operand(const Token& t)
{
	if (t.kind == Token::Ident) return !kBeforeExpression.count(t.text);
	if (t.kind == Token::Punct) return t.text == ")" || t.text == "]";
	return true;
}

// a op b, or false when it leaves 64 bits (it doesn't fit 32 then either)
bool fold(int64_t a, const std::string& op, int64_t b, int64_t& r)
{
	const long double x = (long double)a, y = (long double)b;
	long double v;
	if (op == "+") v = x + y;
	else if (op == "-") v = x - y;
	else if (op == "*") v = x * y;
	else {
		if (b < 0 || b > 62) { r = a == 0 ? 0 : INT64_MAX; return a == 0; }
		v = x * (long double)((uint64_t)1 << b);
	}
	if (v > 9.2e18L || v < -9.2e18L) return false;
	r = (int64_t)v;
	return true;
}

} // namespace

Scan scan(const std::string& text, bool sjis)
{
	Scan out;
	if (text.size() >= 3 && text.compare(0, 3, "\xEF\xBB\xBF") == 0) out.start = 3;
	size_t from = out.start;
	if (text.compare(from, 2, "#!") == 0) {
		// a shell script's first line: a comment to TJS
		const size_t nl = text.find('\n', from);
		from = nl == std::string::npos ? text.size() : nl;
	}
	std::vector<Token> list;
	Scanner(text, sjis, out).tokens(from, false, list);
	out.tokens = !list.empty();

	// the trailing ';'s, and the statements before them
	size_t last = list.size();
	while (last > 0 && list[last - 1].kind == Token::Punct && list[last - 1].text == ";") --last;
	for (size_t i = last; i < list.size(); ++i) out.trailing.push_back(list[i].at);
	int depth = 0;
	for (size_t i = 0; i < last; ++i) {
		const Token& t = list[i];
		if (t.kind != Token::Punct) continue;
		if (t.text == "(" || t.text == "[" || t.text == "{") ++depth;
		else if (t.text == ")" || t.text == "]" || t.text == "}") --depth;
		else if (t.text == ";" && depth == 0) ++out.statements;
	}

	// literals the compiler folds into one constant (left to right, and pair by pair)
	static const std::set<std::string> folding = { "+", "-", "*", "<<" };
	for (size_t i = 0; i < list.size(); ++i) {
		if (list[i].kind != Token::Integer) continue;
		if (i >= 2 && list[i - 1].kind == Token::Punct && folding.count(list[i - 1].text) && list[i - 2].kind == Token::Integer) continue;
		int64_t acc = list[i].value, prev = acc;
		if (i >= 1 && list[i - 1].kind == Token::Punct && list[i - 1].text == "-" && (i < 2 || !operand(list[i - 2]))) acc = prev = -acc;
		for (size_t j = i; j + 2 < list.size(); j += 2) {
			const Token &op = list[j + 1], &b = list[j + 2];
			if (op.kind != Token::Punct || !folding.count(op.text) || b.kind != Token::Integer) break;
			int64_t r1 = 0, r2 = 0;
			if (!fold(acc, op.text, b.value, r1) || !fold(prev, op.text, b.value, r2) || !fitsInt32(r1) || !fitsInt32(r2)) {
				out.wideFold = true;
				break;
			}
			acc = r1;
			prev = b.value;
		}
	}
	return out;
}

//---------------------------------------------------------------------------
// Bytecode (tjsScriptBlock.cpp's ExportByteCode, tjsByteCodeLoader.cpp)
//---------------------------------------------------------------------------
namespace {

constexpr int16_t kString = 3, kOctet = 4, kReal = 5, kByte = 6, kShort = 7, kInteger = 8, kLong = 9;

struct Reader {
	const std::string& s;
	void need(size_t at, size_t n) const { if (at > s.size() || n > s.size() - at) throw "it ends early"; }
	uint32_t u32(size_t at) const
	{
		need(at, 4);
		return (unsigned char)s[at] | ((unsigned char)s[at + 1] << 8) | ((unsigned char)s[at + 2] << 16) | ((uint32_t)(unsigned char)s[at + 3] << 24);
	}
	int16_t i16(size_t at) const
	{
		need(at, 2);
		return (int16_t)((unsigned char)s[at] | ((unsigned char)s[at + 1] << 8));
	}
	int64_t i64(size_t at) const { return (int64_t)((uint64_t)u32(at) | ((uint64_t)u32(at + 4) << 32)); }
	// a count, checked against what's left
	size_t count(size_t at, size_t each) const
	{
		const size_t n = u32(at);
		need(at + 4, n * each);
		return n;
	}
};

} // namespace

bool Bytecode::parse(std::string data, std::string& error)
{
	*this = Bytecode();
	raw = std::move(data);
	try {
		const Reader r{ raw };
		if (raw.size() < 20 || raw.compare(0, 8, std::string("TJS2100\0", 8)) != 0) throw "it isn't TJS2 bytecode";
		if (r.u32(8) != raw.size()) throw "its size is wrong";
		if (raw.compare(12, 4, "DATA") != 0) throw "it has no constants";
		objsAt = 12 + (size_t)r.u32(16);
		size_t o = 20, n;
		n = r.count(o, 1); o += 4;
		for (size_t k = 0; k < n; ++k) bytes.push_back((int8_t)raw[o + k]);
		o += (n + 3) / 4 * 4;
		n = r.count(o, 2); o += 4;
		for (size_t k = 0; k < n; ++k) shorts.push_back(r.i16(o + 2 * k));
		o += n * 2 + (n & 1) * 2;
		n = r.count(o, 4); o += 4;
		for (size_t k = 0; k < n; ++k) ints.push_back((int32_t)r.u32(o + 4 * k));
		o += n * 4;
		longsAt = o;
		n = r.count(o, 8); o += 4;
		for (size_t k = 0; k < n; ++k) longs.push_back(r.i64(o + 8 * k));
		o += n * 8;
		longsEnd = o;
		n = r.count(o, 8); o += 4;
		for (size_t k = 0; k < n; ++k) doubles.push_back(raw.substr(o + 8 * k, 8));
		o += n * 8;
		n = r.count(o, 4); o += 4;
		for (size_t k = 0; k < n; ++k) {
			const size_t len = r.count(o, 2); o += 4;
			strings.push_back(raw.substr(o, len * 2));
			o += len * 2 + (len & 1) * 2;
		}
		n = r.count(o, 4); o += 4;
		for (size_t k = 0; k < n; ++k) {
			const size_t len = r.count(o, 1); o += 4;
			octets.push_back(raw.substr(o, len));
			o += (len + 3) / 4 * 4;
		}
		if (o != objsAt) throw "its constant tables don't add up";
		r.need(objsAt, 16);
		if (raw.compare(objsAt, 4, "OBJS") != 0) throw "it has no code";
		if (objsAt + r.u32(objsAt + 4) != raw.size()) throw "its code's size is wrong";
		const size_t count = r.u32(objsAt + 12);
		o = objsAt + 16;
		for (size_t k = 0; k < count; ++k) {
			r.need(o, 8);
			if (raw.compare(o, 4, "TJS2") != 0) throw "a function is broken";
			Object ob;
			ob.at = o + 8;
			ob.size = r.u32(o + 4);
			r.need(ob.at, ob.size);
			size_t p = ob.at + 48;
			p += 4 + r.count(p, 8) * 8;   // source positions (debug information)
			ob.codeCount = (int)r.count(p, 2); p += 4;
			ob.codeAt = p;
			p += (size_t)ob.codeCount * 2 + (ob.codeCount & 1) * 2;
			ob.slotCount = (int)r.count(p, 4); p += 4;
			ob.slotsAt = p;
			p += (size_t)ob.slotCount * 4;
			ob.restAt = p;
			p += 4 + r.count(p, 4) * 4;   // super class getters
			p += 4 + r.count(p, 8) * 8;   // properties
			if (p != ob.at + ob.size) throw "a function's size is wrong";
			objects.push_back(ob);
			o = p;
		}
		if (o != raw.size()) throw "there's more after its code";
	} catch (const char* e) {
		error = e;
		return false;
	}
	return true;
}

Bytecode::Value Bytecode::slot(const Object& o, int i) const
{
	const Reader r{ raw };
	Value v;
	v.type = r.i16(o.slotsAt + 4 * (size_t)i);
	const int16_t index = r.i16(o.slotsAt + 4 * (size_t)i + 2);
	auto pick = [&](const auto& table) { if (index < 0 || (size_t)index >= table.size()) throw "a constant's index is past its table"; return table[index]; };
	switch (v.type) {
	case kByte: v.integer = pick(bytes); break;
	case kShort: v.integer = pick(shorts); break;
	case kInteger: v.integer = pick(ints); break;
	case kLong: v.integer = pick(longs); break;
	case kString: v.bytes = pick(strings); break;
	case kOctet: v.bytes = pick(octets); break;
	case kReal: v.bytes = pick(doubles); break;
	default: v.integer = index; break;   // void, null, functions (by index)
	}
	return v;
}

std::string Bytecode::tooLarge() const
{
	constexpr size_t limit = 32767;
	if (objects.size() > limit) return "more than 32767 functions";
	if (strings.size() > limit) return "more than 32767 different names and strings";
	if (shorts.size() > limit || ints.size() > limit || longs.size() > limit || doubles.size() > limit || octets.size() > limit)
		return "more than 32767 different numbers";
	for (const auto& o : objects) {
		if ((size_t)o.codeCount > limit) return "a function of more than 32767 code words";
		if ((size_t)o.slotCount > limit) return "a function with more than 32767 constants";
	}
	return "";
}

std::string fixWideConstants(Bytecode& compiled, const Bytecode& marked, const std::vector<std::pair<int64_t, int64_t>>& markers, int& fixedSlots)
{
	fixedSlots = 0;
	const std::map<int64_t, int64_t> real(markers.begin(), markers.end());
	std::vector<std::pair<size_t, int64_t>> patches;   // slot in raw, its value
	try {
		if (compiled.objects.size() != marked.objects.size() || compiled.bytes != marked.bytes || compiled.shorts != marked.shorts ||
		    compiled.doubles != marked.doubles || compiled.strings != marked.strings || compiled.octets != marked.octets)
			throw "the two compiles differ";
		for (size_t k = 0; k < compiled.objects.size(); ++k) {
			const auto &a = compiled.objects[k], &b = marked.objects[k];
			if (a.codeCount != b.codeCount || a.slotCount != b.slotCount || a.size != b.size ||
			    compiled.raw.compare(a.at, a.slotsAt - a.at, marked.raw, b.at, b.slotsAt - b.at) != 0 ||
			    compiled.raw.compare(a.restAt, a.at + a.size - a.restAt, marked.raw, b.restAt, b.at + b.size - b.restAt) != 0)
				throw "the two compiles differ";
			for (int i = 0; i < a.slotCount; ++i) {
				const Bytecode::Value va = compiled.slot(a, i), vb = marked.slot(b, i);
				const auto m = vb.isInteger() ? real.find(vb.integer) : real.end();
				if (m == real.end()) {
					if (!(va == vb)) throw "the two compiles differ";
					continue;
				}
				if (va.isInteger() && va.integer == m->second) continue;   // an engine that keeps them
				if (va.type != kInteger || va.integer != (int64_t)(int32_t)m->second) throw "a constant isn't what it should be";
				patches.push_back({ a.slotsAt + 4 * (size_t)i, m->second });
			}
		}
	} catch (const char* e) {
		return e;
	}
	if (patches.empty()) return "";

	// the values go into the LONG table, and their slots point there
	std::vector<int64_t> longs = compiled.longs;
	std::string objs = compiled.raw.substr(compiled.objsAt);
	for (const auto& [at, value] : patches) {
		size_t index = std::find(longs.begin(), longs.end(), value) - longs.begin();
		if (index == longs.size()) longs.push_back(value);
		if (index > 32767) return "more than 32767 different numbers";
		std::string s;
		put16(s, kLong);
		put16(s, (int)index);
		objs.replace(at - compiled.objsAt, 4, s);
	}
	std::string table;
	put32(table, (uint32_t)longs.size());
	for (int64_t v : longs) put64(table, (uint64_t)v);
	const std::string& raw = compiled.raw;
	const std::string payload = raw.substr(20, compiled.longsAt - 20) + table + raw.substr(compiled.longsEnd, compiled.objsAt - compiled.longsEnd);
	std::string out = raw.substr(0, 8);
	put32(out, 0);
	out += "DATA";
	put32(out, (uint32_t)payload.size() + 8);
	out += payload;
	out += objs;
	const uint32_t size = (uint32_t)out.size();
	for (int k = 0; k < 4; ++k) out[8 + k] = (char)((size >> (8 * k)) & 0xff);
	std::string err;
	if (!compiled.parse(std::move(out), err)) return "the fixed bytecode doesn't read back: " + err;
	fixedSlots = (int)patches.size();
	return "";
}

} // namespace tjs

//---------------------------------------------------------------------------
// The compile run
//---------------------------------------------------------------------------
namespace {

// The engine's startup.tjs for it. list.txt has "@set (...)" lines, run as the framework runs
// them, and "<id>\t<script>\t<probe>\t<marked>\t." lines (paths from the data path, the .work
// folder): the probe is the script as one expression in parentheses, for scripts that may be one;
// marked has marker values for its constants beyond 32 bits. result.txt gets
// "<id>\t<s|e|x>\t<ok|failed|->\t<error>" for each: statements, an expression, or not compiled
const char* const kCompileScript = R"tjs(// kagex-release: compiles the game's scripts to bytecode
var base = System.dataPath;
var result = [];
try {
	var list = [].load(base + "compile/list.txt");
	for (var i = 0; i < list.count; i++) {
		var line = list[i];
		if (line == "") continue;
		if (line.charAt(0) == "@") {
			Scripts.exec(line);
			continue;
		}
		var f = [].split("\t", line);
		var id = f[0];
		var out = base + "compile/out/" + id;
		var modes = ["s", "e"];
		if (f[2] != "") {
			try {
				Scripts.compileStorage(base + f[2], out + ".p.bc", true, false, true);
				modes = ["e", "s"];
			} catch (e) {
			}
		}
		Debug.message("kagex-compile " + id);
		var mode = "x", error = "";
		for (var k = 0; k < modes.count && mode == "x"; k++) {
			var expr = modes[k] == "e";
			try {
				Scripts.compileStorage(base + f[1], out + ".bc", expr, false, expr);
				mode = modes[k];
			} catch (e) {
				if (error == "") error = e.message;
			}
		}
		var marked = "-";
		if (mode != "x" && f[3] != "") {
			try {
				Scripts.compileStorage(base + f[3], out + ".m.bc", mode == "e", false, mode == "e");
				marked = "ok";
			} catch (e) {
				marked = "failed";
			}
		}
		result.add(id + "\t" + mode + "\t" + marked + "\t" + error);
	}
} catch (e) {
	result.add("error\t" + e.message);
}
result.save(base + "compile/result.txt");
System.exit();
)tjs";

// The scripts the game reads first, whose @set lines the rest are compiled with
int loadOrder(const std::string& name)
{
	std::string leaf = lower(name);
	const size_t sl = leaf.rfind('/');
	if (sl != std::string::npos) leaf = leaf.substr(sl + 1);
	if (lower(name) == "startup.tjs") return 0;
	if (leaf == "initialize.tjs") return 1;
	if (leaf == "storages.tjs") return 2;
	if (leaf == "appconfig.tjs") return 3;
	if (leaf == "config.tjs") return 4;
	return 5;
}

// An option in the project's krkrz.cf (lower-case name), or empty
std::string cfOption(const Project& p, const std::string& name)
{
	std::string text, value;
	if (!krt::readFile(p.root / "krkrz.cf", text)) return value;
	size_t pos = 0;
	while (pos < text.size()) {
		size_t end = text.find('\n', pos);
		if (end == std::string::npos) end = text.size();
		const std::string t = krt::trim(text.substr(pos, end - pos));
		pos = end + 1;
		if (t.empty() || t[0] == ';') continue;
		const size_t eq = t.find('=');
		if (eq != std::string::npos && lower(krt::trim(t.substr(0, eq))) == name) value = krt::trim(t.substr(eq + 1));
	}
	return value;
}

} // namespace

bool compileScripts(const Json& s, const Project& p, const fs::path& stage, const fs::path& exe, const fs::path& work,
                    krt::Progress& pr, ScriptsResult& result, std::string& error)
{
	struct Item {
		std::string name;      ///< in data/
		bool utf16 = false;
		std::string text;      ///< UTF-8 when utf16, else the bytes as they are
		tjs::Scan scan;
		std::vector<std::pair<int64_t, int64_t>> markers;   ///< marker, the value it stands for
	};
	std::vector<Item> items;
	std::error_code ec;
	for (fs::recursive_directory_iterator it(stage, ec), end; it != end; it.increment(ec)) {
		if (ec) break;
		if (!it->is_regular_file(ec) || lower(krt::fromPath(it->path().extension())) != ".tjs") continue;
		std::string n = krt::fromPath(fs::relative(it->path(), stage, ec));
		std::replace(n.begin(), n.end(), '\\', '/');
		items.push_back({ n });
	}
	std::sort(items.begin(), items.end(), [](const Item& a, const Item& b) {
		const int oa = loadOrder(a.name), ob = loadOrder(b.name);
		return oa != ob ? oa < ob : a.name < b.name;
	});
	if (items.empty()) return true;

	const fs::path dir = work / "compile";
	fs::remove_all(dir, ec);
	fs::create_directories(dir / "in", ec);
	fs::create_directories(dir / "out", ec);
	auto write = [&](const fs::path& f, const std::string& text) {
		if (!krt::writeFile(f, text)) throw std::runtime_error("Can't write " + krt::fromPath(f));
	};
	// the script's own encoding: UTF-16LE scripts go back to it
	auto encoded = [](const Item& it, const std::string& text) { return it.utf16 ? utf8ToUtf16(text) : text; };

	std::string list = "\xEF\xBB\xBF";
	list += "@set (PACKED=1)\n";
	if (flag(s, "engine.debug")) list += "@set (DEBUG=1)\n";
	// whether this engine cuts constants to 32 bits
	list += "canary\tcompile/canary.tjs\tcompile/canary.tjs\t\t.\n";
	try {
		write(dir / "startup.tjs", std::string("\xEF\xBB\xBF") + kCompileScript);
		write(dir / "canary.tjs", "0x123456789\n");
		for (size_t i = 0; i < items.size(); ++i) {
			Item& it = items[i];
			std::string raw;
			if (!krt::readFile(stage / krt::toPath(it.name), raw)) throw std::runtime_error("Can't read " + it.name);
			it.utf16 = raw.size() >= 2 && (unsigned char)raw[0] == 0xFF && (unsigned char)raw[1] == 0xFE;
			it.text = it.utf16 ? utf16ToUtf8(raw, 2) : raw;
			it.scan = tjs::scan(it.text, !it.utf16 && !validUtf8(it.text));
			const std::string id = std::to_string(i);
			std::string probe, marked;
			if (it.scan.ok && it.scan.tokens && it.scan.statements == 0) {
				// blanked rather than cut off: whatever the scan missed is still in it
				std::string body = it.text.substr(it.scan.start);
				for (size_t at : it.scan.trailing) body[at - it.scan.start] = ' ';
				if (body.compare(0, 2, "#!") == 0) body.replace(0, 2, "//");
				probe = "compile/in/" + id + ".p.tjs";
				write(work / krt::toPath(probe), encoded(it, it.text.substr(0, it.scan.start) + "(" + body + "\n)"));
			}
			// marker values for its constants beyond 32 bits, unlike anything else in it
			std::set<int64_t> taken;
			for (const auto& l : it.scan.integers) {
				taken.insert(l.value);
				taken.insert(-l.value);
				taken.insert((int32_t)l.value);
				taken.insert(-(int64_t)(int32_t)l.value);
			}
			std::map<int64_t, int64_t> markerOf;
			int64_t nextMarker = 0x4B580000;   // "KX"
			for (const auto& l : it.scan.integers) {
				if (fitsInt32(l.value) || markerOf.count(l.value)) continue;
				while (taken.count(nextMarker) || taken.count(-nextMarker)) ++nextMarker;
				markerOf[l.value] = nextMarker;
				it.markers.push_back({ nextMarker, l.value });
				it.markers.push_back({ -nextMarker, -l.value });
				++nextMarker;
			}
			if (!markerOf.empty()) {
				std::string text = it.text;
				for (auto l = it.scan.integers.rbegin(); l != it.scan.integers.rend(); ++l)
					if (markerOf.count(l->value)) text.replace(l->at, l->len, std::to_string(markerOf[l->value]));
				marked = "compile/in/" + id + ".m.tjs";
				write(work / krt::toPath(marked), encoded(it, text));
			}
			list += id + "\tdata/" + it.name + "\t" + probe + "\t" + marked + "\t.\n";
		}
		write(dir / "list.txt", list);
	} catch (const std::exception& e) {
		error = e.what();
		return false;
	}

	// the engine, headless
	pr.progress(0, "Compiling the scripts");
	RunOptions opt;
	opt.timeoutSeconds = 300;
	opt.workDir = exe.parent_path();
	opt.env = { { "SDL_AUDIO_DRIVER", "dummy" } };
	if (std::string(hostId()) == "linux") opt.env.push_back({ "SDL_VIDEO_DRIVER", "offscreen" });
	opt.canceled = [&pr]() { return pr.canceled(); };
	size_t done = 0;
	opt.onLine = [&](const std::string& line) {
		if (line.find("kagex-compile ") != std::string::npos) pr.progress((double)++done / (items.size() + 1), "Compiling the scripts");
	};
	std::vector<std::string> args = { krt::fromPath(dir), "-datapath=" + krt::fromPath(work) + "/", "-forcelog=clear" };
	const std::string encoding = cfOption(p, "readencoding");
	if (!encoding.empty()) args.push_back("-readencoding=" + encoding);
	const RunResult rr = run(krt::fromPath(exe), args, opt);
	if (pr.canceled()) { error = "Canceled"; return false; }
	std::string log = rr.output;
	if (log.find("kagex-compile ") == std::string::npos) {
		// where the engine's output doesn't come back (Windows), its log file has the same lines
		// (elsewhere the engine names it \krkr.console.log: it ends the folder with a backslash)
#ifdef _WIN32
		const char* const names[] = { "krkr.console.log" };
#else
		const char* const names[] = { "krkr.console.log", "\\krkr.console.log" };
#endif
		for (const char* name : names) {
			std::string raw;
			if (krt::readFile(work / name, raw) && raw.size() >= 2) { log = utf16ToUtf8(raw, (unsigned char)raw[0] == 0xFF ? 2 : 0); break; }
		}
	}
	result.log = log;
	std::string resultText;
	if (!rr.started || !krt::readFile(dir / "result.txt", resultText)) {
		error = rr.started ? "The engine didn't finish compiling the scripts" + std::string(rr.timedOut ? " (it ran for 5 minutes)" : "") + " (see compile-scripts.log)"
		                   : "The engine couldn't be started to compile the scripts: " + krt::trim(rr.output);
		return false;
	}
	if (resultText.size() >= 2 && (unsigned char)resultText[0] == 0xFF && (unsigned char)resultText[1] == 0xFE) resultText = utf16ToUtf8(resultText, 2);
	struct Outcome { std::string mode, marked, error; };
	std::map<std::string, Outcome> outcomes;
	{
		size_t pos = 0;
		while (pos < resultText.size()) {
			size_t end = resultText.find('\n', pos);
			if (end == std::string::npos) end = resultText.size();
			std::string line = resultText.substr(pos, end - pos);
			pos = end + 1;
			if (!line.empty() && line.back() == '\r') line.pop_back();
			std::vector<std::string> f;
			size_t a = 0;
			for (size_t b; (b = line.find('\t', a)) != std::string::npos; a = b + 1) f.push_back(line.substr(a, b - a));
			f.push_back(line.substr(a));
			if (f.size() >= 2 && f[0] == "error") { error = "The compile script failed: " + f[1]; return false; }
			if (f.size() >= 3) outcomes[f[0]] = { f[1], f[2], f.size() >= 4 ? f[3] : std::string() };
		}
	}
	// where a compile error is: the engine logs "... at line N" after our "kagex-compile <id>"
	auto errorLine = [&log](const std::string& id) {
		const std::string mark = "kagex-compile " + id + "\n";
		size_t at = log.find(mark);
		if (at == std::string::npos) at = log.find("kagex-compile " + id + "\r");
		if (at == std::string::npos) return std::string();
		const size_t end = log.find("kagex-compile ", at + mark.size());
		static const std::regex re(R"(at line (\d+))");
		std::smatch m;
		const std::string part = log.substr(at, end == std::string::npos ? std::string::npos : end - at);
		return std::regex_search(part, m, re) ? std::string(m[1]) : std::string();
	};

	tjs::Bytecode canary;
	std::string err, bc;
	if (krt::readFile(dir / "out" / "canary.bc", bc) && canary.parse(bc, err))
		result.truncates = std::find(canary.longs.begin(), canary.longs.end(), (int64_t)0x123456789) == canary.longs.end();
	else
		result.truncates = true;   // can't tell: check every script

	for (size_t i = 0; i < items.size(); ++i) {
		const Item& it = items[i];
		const std::string id = std::to_string(i);
		const auto o = outcomes.find(id);
		auto keep = [&](const std::string& why) { result.kept.push_back({ it.name, why }); };
		if (o == outcomes.end() || o->second.mode == "x") {
			const std::string line = errorLine(id);
			keep("it doesn't compile (" + (o == outcomes.end() || o->second.error.empty() ? std::string("no result") : o->second.error) +
			     (line.empty() ? "" : " at line " + line) + ")");
			continue;
		}
		tjs::Bytecode code;
		if (!krt::readFile(dir / "out" / (id + ".bc"), bc) || bc.empty()) {
			if (it.scan.tokens) keep("the engine wrote no bytecode for it");
			continue;   // no code to hide (empty, or comments only)
		}
		if (!code.parse(bc, err)) { keep("its bytecode doesn't read back (" + err + ")"); continue; }
		if (result.truncates) {
			if (!it.scan.ok) { keep("kagex-release couldn't follow its text far enough to check its constants (an unclosed string or comment?)"); continue; }
			if (it.scan.wideFold) { keep("it has a constant expression beyond 32 bits (like 0xff << 24, or @\"${0x100000000}\"), which this computer's engine would cut to 32 bits"); continue; }
			if (!it.markers.empty()) {
				tjs::Bytecode marked;
				if (o->second.marked != "ok" || !krt::readFile(dir / "out" / (id + ".m.bc"), bc) || !marked.parse(bc, err)) {
					keep("its constants beyond 32 bits couldn't be checked (the second compile failed)");
					continue;
				}
				int fixedSlots = 0;
				const std::string why = tjs::fixWideConstants(code, marked, it.markers, fixedSlots);
				if (!why.empty()) { keep("its constants beyond 32 bits couldn't be put right: " + why); continue; }
				if (fixedSlots) ++result.fixed;
			}
		}
		const std::string big = code.tooLarge();
		if (!big.empty()) { keep("it's too large for the engine's bytecode (" + big + ")"); continue; }
		// staged files are hard links to the game's own: replaced, never written to
		const fs::path f = stage / krt::toPath(it.name);
		fs::remove(f, ec);
		if (!krt::writeFile(f, code.raw)) { error = "Can't write " + krt::fromPath(f); return false; }
		++result.compiled;
		if (o->second.mode == "e") ++result.expressions;
	}
	return true;
}

} // namespace kr
