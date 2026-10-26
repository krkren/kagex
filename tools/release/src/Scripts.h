//---------------------------------------------------------------------------
// Compiling the game's TJS scripts to bytecode (contents.compileScripts)
//
// After the media conversion (which rewrites names in scripts as text), every .tjs in the staged
// data is compiled by this computer's engine, run headless with a startup.tjs of ours
// (Scripts.compileStorage), and replaced by its bytecode under the same name. The engine tells
// bytecode from source by its header wherever it runs a script (Scripts.execStorage and
// evalStorage, startup.tjs), so the framework loads them as before.
//
//   mode:      a script that is one expression (envinit.tjs' %[ ... ];) is compiled as an
//              expression, so Scripts.evalStorage still returns its value (bytecode keeps the mode
//              it was compiled in); the others as statements. Which it is, the engine decides:
//              "(" + the script with its trailing ';'s blanked + ")" compiles only for one
//              expression
//   @if:       decided when compiling: PACKED=1, DEBUG=1 with the debug engine (as Initialize.tjs
//              sets them), and the @set lines of the scripts the game reads first, which are
//              compiled first (startup.tjs, Initialize.tjs, Storages.tjs, AppConfig.tjs,
//              Config.tjs)
//   constants: engines built where long is 64 bits (Linux, macOS) store integer constants
//              outside 32 bits cut to 32 (0xff000000 became -16777216; UPSTREAM.md). Where the
//              compiling engine does (a canary script shows it), a script with such literals is
//              compiled again with marker values in their place; the slots the markers mark are
//              set to the real values, and the two compiles must match everywhere else
//   kept:      a script that doesn't compile, that the engine would misread (indexes past 16
//              bits) or whose constants can't be put right stays source, with the reason
//
// Bytecode has no line numbers: the engine's debug information crashes it when it reports an
// exception (UPSTREAM.md), so errors in compiled scripts name the function, at line 1.
//---------------------------------------------------------------------------
#pragma once
#include <cstdint>
#include <filesystem>
#include <string>
#include <utility>
#include <vector>

#include "Settings.h"

namespace krt {
class Progress;
}

namespace kr {

struct ScriptsResult {
	int compiled = 0;      ///< replaced by bytecode
	int expressions = 0;   ///< of those, compiled as an expression
	int fixed = 0;         ///< of those, with constants beyond 32 bits put right
	bool truncates = false;   ///< the compiling engine cuts constants to 32 bits
	std::vector<std::pair<std::string, std::string>> kept;   ///< staged name, why it stays source
	std::string log;       ///< the engine's output
};

/// Compiles the .tjs files in stage (the staged data/) with the engine at engineExe, using
/// work/compile. false only on errors that stop the build (the engine didn't run)
bool compileScripts(const Json& settings, const Project& project, const std::filesystem::path& stage,
                    const std::filesystem::path& engineExe, const std::filesystem::path& work,
                    krt::Progress& progress, ScriptsResult& result, std::string& error);

namespace tjs {

/// What compiling a script needs to know of its text, from a scan with TJS's lexical rules
/// (comments, which nest; strings, embeddable ones with ${...}; regular expressions; octets;
/// @-directives)
struct Scan {
	struct Literal {
		size_t  at = 0, len = 0;   ///< in the text
		int64_t value = 0;
	};
	bool ok = true;                 ///< false: an unclosed comment or string (nothing below is sure)
	size_t start = 0;               ///< after a BOM
	std::vector<Literal> integers;  ///< every integer literal in code
	std::vector<size_t> trailing;   ///< the ';'s after the last other token
	int statements = 0;             ///< ';' outside brackets, before the trailing ones
	bool tokens = false;            ///< any code at all
	/// literal op literal (+ - * <<) beyond 32 bits, or a literal beyond 32 bits in an embeddable
	/// string: the compiler folds it into one constant, which no marker can follow
	bool wideFold = false;
};

/// text as UTF-8 or Shift_JIS bytes (sjis: skip double-byte characters' second bytes)
Scan scan(const std::string& text, bool sjis);

/// TJS2 bytecode ("TJS2100\0"): its constant tables and each function's code and constants
struct Bytecode {
	struct Value {
		int16_t     type = 0;
		int64_t     integer = 0;   ///< BYTE, SHORT, INTEGER, LONG (and the index otherwise)
		std::string bytes;         ///< STRING (UTF-16LE), OCTET, REAL (its 8 bytes)
		bool operator==(const Value& o) const { return type == o.type && integer == o.integer && bytes == o.bytes; }
		bool isInteger() const { return type >= 6 && type <= 9; }
	};
	struct Object {
		size_t at = 0, size = 0;   ///< its chunk's body in raw
		size_t codeAt = 0;         ///< the code words
		int    codeCount = 0;
		size_t slotsAt = 0;        ///< its constants: (int16 type, int16 index) each
		int    slotCount = 0;
		size_t restAt = 0;         ///< super class getters and properties, to the end
	};
	std::string raw;
	std::vector<int8_t> bytes;
	std::vector<int16_t> shorts;
	std::vector<int32_t> ints;
	std::vector<int64_t> longs;
	std::vector<std::string> doubles, strings, octets;   ///< raw bytes (strings in UTF-16LE)
	size_t longsAt = 0, longsEnd = 0;   ///< the LONG table, with its count, in raw
	size_t objsAt = 0;                  ///< "OBJS"
	std::vector<Object> objects;

	bool parse(std::string data, std::string& error);
	Value slot(const Object& o, int i) const;
	/// Indexes the engine reads as 16-bit signed: an empty string when all fit
	std::string tooLarge() const;
};

/// Puts right the constants cut to 32 bits in compiled (the script as it is), from marked (the
/// same script with each value v in markers.second written as markers.first): every slot holding
/// a marker becomes v, and everything else must be the same in both. Returns why not, or empty
std::string fixWideConstants(Bytecode& compiled, const Bytecode& marked,
                             const std::vector<std::pair<int64_t, int64_t>>& markers, int& fixedSlots);

} // namespace tjs

} // namespace kr
