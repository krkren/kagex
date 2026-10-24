#include "Archive.h"

#include <algorithm>
#include <cstring>
#include <ctime>
#include <zlib.h>

#include "krt/app/Text.h"

#ifndef _WIN32
#include <sys/stat.h>
#include <unistd.h>
#endif

namespace fs = std::filesystem;

namespace kr {

namespace {

std::FILE* openFile(const fs::path& p, const char* mode)
{
#ifdef _WIN32
	std::wstring m(mode, mode + std::strlen(mode));
	return _wfopen(p.wstring().c_str(), m.c_str());
#else
	return std::fopen(p.c_str(), mode);
#endif
}

bool seek(std::FILE* f, uint64_t pos)
{
#ifdef _WIN32
	return _fseeki64(f, (long long)pos, SEEK_SET) == 0;
#else
	return fseeko(f, (off_t)pos, SEEK_SET) == 0;
#endif
}

uint64_t tell(std::FILE* f)
{
#ifdef _WIN32
	return (uint64_t)_ftelli64(f);
#else
	return (uint64_t)ftello(f);
#endif
}

uint64_t fileSize(std::FILE* f)
{
#ifdef _WIN32
	_fseeki64(f, 0, SEEK_END);
#else
	fseeko(f, 0, SEEK_END);
#endif
	return tell(f);
}

uint16_t rd16(const uint8_t* p) { return (uint16_t)(p[0] | p[1] << 8); }
uint32_t rd32(const uint8_t* p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
uint64_t rd64(const uint8_t* p) { return (uint64_t)rd32(p) | (uint64_t)rd32(p + 4) << 32; }

void put16(std::string& s, uint16_t v) { s += (char)(v & 0xff); s += (char)(v >> 8); }
void put32(std::string& s, uint32_t v) { for (int i = 0; i < 4; ++i) s += (char)((v >> (8 * i)) & 0xff); }
void put64(std::string& s, uint64_t v) { for (int i = 0; i < 8; ++i) s += (char)((v >> (8 * i)) & 0xff); }

uint32_t dosTimeOf(std::time_t t)
{
	std::tm tm{};
#ifdef _WIN32
	localtime_s(&tm, &t);
#else
	localtime_r(&t, &tm);
#endif
	if (tm.tm_year < 80) return (0 << 25) | (1 << 21) | (1 << 16);   // 1980-01-01
	return (uint32_t)((tm.tm_year - 80) << 25 | (tm.tm_mon + 1) << 21 | tm.tm_mday << 16 |
	                  tm.tm_hour << 11 | tm.tm_min << 5 | tm.tm_sec / 2);
}

std::time_t mtimeOf(const fs::path& p)
{
#ifdef _WIN32
	std::error_code ec;
	auto ft = fs::last_write_time(p, ec);
	if (ec) return std::time(nullptr);
	// file_time_type's epoch is 1601 on MSVC
	auto secs = std::chrono::duration_cast<std::chrono::seconds>(ft.time_since_epoch()).count();
	return (std::time_t)(secs - 11644473600LL);
#else
	struct stat st;
	if (::stat(p.c_str(), &st) != 0) return std::time(nullptr);
	return st.st_mtime;
#endif
}

uint32_t diskMode(const fs::path& p, bool dir)
{
#ifdef _WIN32
	(void)p;
	return dir ? 0040755 : 0100644;
#else
	struct stat st;
	if (::lstat(p.c_str(), &st) != 0) return dir ? 0040755 : 0100644;
	return (uint32_t)st.st_mode;
#endif
}

bool safeName(const std::string& name)
{
	if (name.empty() || name[0] == '/' || name.find('\\') != std::string::npos || name.find(':') != std::string::npos) return false;
	size_t start = 0;
	while (start <= name.size()) {
		size_t sl = name.find('/', start);
		if (sl == std::string::npos) sl = name.size();
		if (name.compare(start, sl - start, "..") == 0 && sl - start == 2) return false;
		start = sl + 1;
	}
	return true;
}

} // namespace

bool isCompressedAlready(const std::string& name)
{
	static const char* exts[] = { ".ogg", ".opus", ".mp3", ".m4a", ".png", ".jpg", ".jpeg", ".webp", ".tlg",
		".webm", ".mp4", ".mpg", ".ogv", ".zip", ".gz", ".xz", ".bz2", ".7z", ".xp3", ".apk", ".aab", ".ipa", ".dmg", ".icns" };
	std::string lower = name;
	for (auto& c : lower) c = (char)std::tolower((unsigned char)c);
	for (const char* e : exts) {
		const size_t n = std::strlen(e);
		if (lower.size() >= n && lower.compare(lower.size() - n, n, e) == 0) return true;
	}
	return false;
}

//---------------------------------------------------------------------------
// ZipReader
//---------------------------------------------------------------------------
ZipReader::~ZipReader()
{
	if (f_) std::fclose(f_);
}

bool ZipReader::open(const fs::path& file, std::string& error)
{
	f_ = openFile(file, "rb");
	if (!f_) { error = "Can't open " + krt::fromPath(file); return false; }
	const uint64_t size = fileSize(f_);
	const uint64_t tail = std::min<uint64_t>(size, 65557);
	std::vector<uint8_t> buf((size_t)tail);
	if (!seek(f_, size - tail) || std::fread(buf.data(), 1, buf.size(), f_) != buf.size()) { error = "Can't read " + krt::fromPath(file); return false; }
	long eocd = -1;
	for (long i = (long)buf.size() - 22; i >= 0; --i)
		if (rd32(&buf[i]) == 0x06054b50) { eocd = i; break; }
	if (eocd < 0) { error = krt::fromPath(file) + " isn't a zip file"; return false; }
	uint64_t count = rd16(&buf[eocd + 10]);
	uint64_t cdSize = rd32(&buf[eocd + 12]);
	uint64_t cdOffset = rd32(&buf[eocd + 16]);
	if ((count == 0xffff || cdSize == 0xffffffff || cdOffset == 0xffffffff) && eocd >= 20 && rd32(&buf[eocd - 20]) == 0x07064b50) {
		const uint64_t z64 = rd64(&buf[eocd - 20 + 8]);
		uint8_t rec[56];
		if (!seek(f_, z64) || std::fread(rec, 1, 56, f_) != 56 || rd32(rec) != 0x06064b50) { error = "Broken ZIP64 directory"; return false; }
		count = rd64(rec + 32);
		cdSize = rd64(rec + 40);
		cdOffset = rd64(rec + 48);
	}
	std::vector<uint8_t> cd((size_t)cdSize);
	if (!seek(f_, cdOffset) || std::fread(cd.data(), 1, cd.size(), f_) != cd.size()) { error = "Can't read the zip directory"; return false; }
	size_t p = 0;
	for (uint64_t i = 0; i < count; ++i) {
		if (p + 46 > cd.size() || rd32(&cd[p]) != 0x02014b50) { error = "Broken zip directory"; return false; }
		ZipEntry e;
		const uint16_t madeBy = rd16(&cd[p + 4]);
		e.method = rd16(&cd[p + 10]);
		e.crc = rd32(&cd[p + 16]);
		e.compressedSize = rd32(&cd[p + 20]);
		e.size = rd32(&cd[p + 24]);
		const uint16_t nameLen = rd16(&cd[p + 28]), extraLen = rd16(&cd[p + 30]), commentLen = rd16(&cd[p + 32]);
		const uint32_t ext = rd32(&cd[p + 38]);
		e.localHeaderOffset = rd32(&cd[p + 42]);
		if (p + 46 + nameLen + extraLen + commentLen > cd.size()) { error = "Broken zip directory"; return false; }
		e.name.assign((const char*)&cd[p + 46], nameLen);
		if ((madeBy >> 8) == 3) e.unixMode = ext >> 16;
		// ZIP64 sizes and offset
		size_t x = p + 46 + nameLen, xend = x + extraLen;
		while (x + 4 <= xend) {
			const uint16_t id = rd16(&cd[x]), len = rd16(&cd[x + 2]);
			if (id == 1) {
				size_t q = x + 4;
				if (e.size == 0xffffffff && q + 8 <= x + 4 + len) { e.size = rd64(&cd[q]); q += 8; }
				if (e.compressedSize == 0xffffffff && q + 8 <= x + 4 + len) { e.compressedSize = rd64(&cd[q]); q += 8; }
				if (e.localHeaderOffset == 0xffffffff && q + 8 <= x + 4 + len) { e.localHeaderOffset = rd64(&cd[q]); q += 8; }
			}
			x += 4 + len;
		}
		entries_.push_back(std::move(e));
		p += 46 + nameLen + extraLen + commentLen;
	}
	return true;
}

bool ZipReader::dataOffset(const ZipEntry& e, uint64_t& offset, std::string& error)
{
	uint8_t h[30];
	if (!seek(f_, e.localHeaderOffset) || std::fread(h, 1, 30, f_) != 30 || rd32(h) != 0x04034b50) { error = "Broken zip entry " + e.name; return false; }
	offset = e.localHeaderOffset + 30 + rd16(h + 26) + rd16(h + 28);
	return true;
}

bool ZipReader::read(const ZipEntry& e, std::string& out, std::string& error)
{
	uint64_t off;
	if (!dataOffset(e, off, error)) return false;
	if (!seek(f_, off)) { error = "Can't read " + e.name; return false; }
	out.clear();
	if (e.method == 0) {
		out.resize((size_t)e.size);
		if (e.size && std::fread(&out[0], 1, out.size(), f_) != out.size()) { error = "Can't read " + e.name; return false; }
	} else if (e.method == 8) {
		z_stream zs{};
		if (inflateInit2(&zs, -15) != Z_OK) { error = "zlib"; return false; }
		out.resize((size_t)e.size);
		std::vector<char> in(1 << 16);
		uint64_t left = e.compressedSize;
		zs.next_out = (Bytef*)(out.empty() ? nullptr : &out[0]);
		zs.avail_out = (uInt)out.size();
		int r = Z_OK;
		while (r != Z_STREAM_END) {
			if (zs.avail_in == 0) {
				const size_t n = (size_t)std::min<uint64_t>(left, in.size());
				if (n == 0) break;
				if (std::fread(in.data(), 1, n, f_) != n) break;
				left -= n;
				zs.next_in = (Bytef*)in.data();
				zs.avail_in = (uInt)n;
			}
			r = inflate(&zs, Z_NO_FLUSH);
			if (r != Z_OK && r != Z_STREAM_END) break;
		}
		inflateEnd(&zs);
		if (r != Z_STREAM_END || zs.total_out != e.size) { error = "Can't decompress " + e.name; return false; }
	} else {
		error = e.name + ": unsupported compression";
		return false;
	}
	if ((uint32_t)crc32(0, (const Bytef*)out.data(), (uInt)out.size()) != e.crc) { error = e.name + ": damaged (CRC)"; return false; }
	return true;
}

bool ZipReader::extractAll(const fs::path& dir, std::string& error, const std::function<bool(const ZipEntry&)>& filter)
{
	std::error_code ec;
	std::vector<std::pair<fs::path, std::string>> links;
	for (const auto& e : entries_) {
		if (filter && !filter(e)) continue;
		if (!safeName(e.name)) { error = "Unsafe name in the zip: " + e.name; return false; }
		const fs::path target = dir / krt::toPath(e.isDir() ? e.name.substr(0, e.name.size() - 1) : e.name);
		if (e.isDir()) { fs::create_directories(target, ec); continue; }
		fs::create_directories(target.parent_path(), ec);
		std::string data;
		if (!read(e, data, error)) return false;
		if (e.isSymlink()) { links.emplace_back(target, data); continue; }
		if (!krt::writeFile(target, data)) { error = "Can't write " + krt::fromPath(target); return false; }
#ifndef _WIN32
		if (e.unixMode & 0777) ::chmod(target.c_str(), e.unixMode & 0777);
#endif
	}
	for (const auto& [link, to] : links) {
		fs::remove(link, ec);
#ifdef _WIN32
		// no symbolic links without developer mode: a copy of what it points to
		fs::copy_file(link.parent_path() / krt::toPath(to), link, fs::copy_options::overwrite_existing, ec);
#else
		fs::create_symlink(krt::toPath(to), link, ec);
#endif
		if (ec) { error = "Can't create " + krt::fromPath(link) + ": " + ec.message(); return false; }
	}
	return true;
}

//---------------------------------------------------------------------------
// ZipWriter
//---------------------------------------------------------------------------
ZipWriter::~ZipWriter()
{
	if (f_) std::fclose(f_);
}

bool ZipWriter::open(const fs::path& file, std::string& error)
{
	f_ = openFile(file, "wb");
	if (!f_) { error = "Can't create " + krt::fromPath(file); return false; }
	return true;
}

bool ZipWriter::writeEntry(const std::string& name, uint32_t unixMode, uint32_t dosTime, bool compress,
                           const std::function<size_t(char*, size_t)>& source, uint64_t sizeHint, std::string& error)
{
	const bool zip64 = sizeHint >= 0xF0000000ull;
	Central c{ name, 0, 0, tell(f_), 0, unixMode, dosTime, (uint16_t)(compress ? 8 : 0) };
	std::string h;
	put32(h, 0x04034b50);
	put16(h, zip64 ? 45 : 20);
	put16(h, 0x0800);   // UTF-8 names
	put16(h, c.method);
	put16(h, (uint16_t)(dosTime & 0xffff));
	put16(h, (uint16_t)(dosTime >> 16));
	put32(h, 0);        // crc, sizes: filled in afterwards
	put32(h, zip64 ? 0xffffffff : 0);
	put32(h, zip64 ? 0xffffffff : 0);
	put16(h, (uint16_t)name.size());
	put16(h, zip64 ? 20 : 0);
	h += name;
	if (zip64) { put16(h, 1); put16(h, 16); put64(h, 0); put64(h, 0); }
	if (std::fwrite(h.data(), 1, h.size(), f_) != h.size()) { error = "Can't write the zip"; return false; }

	std::vector<char> in(1 << 17), out(1 << 17);
	uLong crc = crc32(0, nullptr, 0);
	uint64_t size = 0, csize = 0;
	z_stream zs{};
	if (compress && deflateInit2(&zs, 6, Z_DEFLATED, -15, 8, Z_DEFAULT_STRATEGY) != Z_OK) { error = "zlib"; return false; }
	for (;;) {
		const size_t n = source(in.data(), in.size());
		crc = crc32(crc, (const Bytef*)in.data(), (uInt)n);
		size += n;
		if (!compress) {
			if (n && std::fwrite(in.data(), 1, n, f_) != n) { error = "Can't write the zip"; return false; }
			csize += n;
			if (n == 0) break;
			continue;
		}
		zs.next_in = (Bytef*)in.data();
		zs.avail_in = (uInt)n;
		const int flush = n == 0 ? Z_FINISH : Z_NO_FLUSH;
		int r;
		do {
			zs.next_out = (Bytef*)out.data();
			zs.avail_out = (uInt)out.size();
			r = deflate(&zs, flush);
			const size_t got = out.size() - zs.avail_out;
			if (got && std::fwrite(out.data(), 1, got, f_) != got) { deflateEnd(&zs); error = "Can't write the zip"; return false; }
			csize += got;
		} while (zs.avail_out == 0 || (flush == Z_FINISH && r != Z_STREAM_END));
		if (n == 0) break;
	}
	if (compress) deflateEnd(&zs);
	if (!zip64 && (size >= 0xffffffffull || csize >= 0xffffffffull)) { error = name + " grew past 4 GB unexpectedly"; return false; }
	c.crc = (uint32_t)crc;
	c.size = size;
	c.compressedSize = csize;
	const uint64_t end = tell(f_);
	std::string fix;
	put32(fix, c.crc);
	if (zip64) {
		if (!seek(f_, c.offset + 14) || std::fwrite(fix.data(), 1, 4, f_) != 4) { error = "Can't write the zip"; return false; }
		std::string x;
		put64(x, size);
		put64(x, csize);
		if (!seek(f_, c.offset + 30 + name.size() + 4) || std::fwrite(x.data(), 1, 16, f_) != 16) { error = "Can't write the zip"; return false; }
	} else {
		put32(fix, (uint32_t)csize);
		put32(fix, (uint32_t)size);
		if (!seek(f_, c.offset + 14) || std::fwrite(fix.data(), 1, 12, f_) != 12) { error = "Can't write the zip"; return false; }
	}
	seek(f_, end);
	central_.push_back(std::move(c));
	return true;
}

bool ZipWriter::addFile(const std::string& name, const fs::path& source, bool compress, std::string& error, uint32_t unixMode)
{
	std::FILE* in = openFile(source, "rb");
	if (!in) { error = "Can't read " + krt::fromPath(source); return false; }
	const uint64_t size = fileSize(in);
	seek(in, 0);
	bool readError = false;
	const bool ok = writeEntry(name, unixMode ? unixMode : diskMode(source, false), dosTimeOf(mtimeOf(source)), compress && size > 0,
		[&](char* buf, size_t n) {
			const size_t got = std::fread(buf, 1, n, in);
			if (got < n && std::ferror(in)) readError = true;
			return got;
		}, size, error);
	std::fclose(in);
	if (ok && readError) { error = "Can't read " + krt::fromPath(source); return false; }
	return ok;
}

bool ZipWriter::addData(const std::string& name, const std::string& data, uint32_t unixMode, std::string& error)
{
	size_t pos = 0;
	return writeEntry(name, unixMode ? unixMode : 0100644, dosTimeOf(std::time(nullptr)), data.size() > 64,
		[&](char* buf, size_t n) {
			const size_t k = std::min(n, data.size() - pos);
			std::memcpy(buf, data.data() + pos, k);
			pos += k;
			return k;
		}, data.size(), error);
}

bool ZipWriter::addDir(const std::string& name, std::string& error)
{
	const std::string n = name.empty() || name.back() == '/' ? name : name + "/";
	return writeEntry(n, 0040755, dosTimeOf(std::time(nullptr)), false, [](char*, size_t) { return (size_t)0; }, 0, error);
}

bool ZipWriter::addSymlink(const std::string& name, const std::string& target, std::string& error)
{
	size_t pos = 0;
	return writeEntry(name, 0120777, dosTimeOf(std::time(nullptr)), false,
		[&](char* buf, size_t n) {
			const size_t k = std::min(n, target.size() - pos);
			std::memcpy(buf, target.data() + pos, k);
			pos += k;
			return k;
		}, target.size(), error);
}

bool ZipWriter::close(std::string& error)
{
	if (!f_) return true;
	const uint64_t cdStart = tell(f_);
	std::string cd;
	for (const auto& c : central_) {
		const bool z64 = c.size >= 0xffffffffull || c.compressedSize >= 0xffffffffull || c.offset >= 0xffffffffull;
		put32(cd, 0x02014b50);
		put16(cd, (3 << 8) | 45);
		put16(cd, z64 ? 45 : 20);
		put16(cd, 0x0800);
		put16(cd, c.method);
		put16(cd, (uint16_t)(c.dosTime & 0xffff));
		put16(cd, (uint16_t)(c.dosTime >> 16));
		put32(cd, c.crc);
		put32(cd, z64 ? 0xffffffff : (uint32_t)c.compressedSize);
		put32(cd, z64 ? 0xffffffff : (uint32_t)c.size);
		put16(cd, (uint16_t)c.name.size());
		put16(cd, z64 ? 28 : 0);
		put16(cd, 0);
		put16(cd, 0);
		put16(cd, 0);
		const bool dir = (c.unixMode & 0170000) == 0040000;
		put32(cd, (c.unixMode << 16) | (dir ? 0x10 : 0));
		put32(cd, z64 ? 0xffffffff : (uint32_t)c.offset);
		cd += c.name;
		if (z64) { put16(cd, 1); put16(cd, 24); put64(cd, c.size); put64(cd, c.compressedSize); put64(cd, c.offset); }
	}
	const uint64_t cdSize = cd.size();
	const uint64_t count = central_.size();
	const bool z64 = count >= 0xffff || cdStart >= 0xffffffffull || cdSize >= 0xffffffffull;
	if (z64) {
		const uint64_t recAt = cdStart + cdSize;
		put32(cd, 0x06064b50);
		put64(cd, 44);
		put16(cd, (3 << 8) | 45);
		put16(cd, 45);
		put32(cd, 0);
		put32(cd, 0);
		put64(cd, count);
		put64(cd, count);
		put64(cd, cdSize);
		put64(cd, cdStart);
		put32(cd, 0x07064b50);
		put32(cd, 0);
		put64(cd, recAt);
		put32(cd, 1);
	}
	put32(cd, 0x06054b50);
	put16(cd, 0);
	put16(cd, 0);
	put16(cd, z64 ? 0xffff : (uint16_t)count);
	put16(cd, z64 ? 0xffff : (uint16_t)count);
	put32(cd, z64 ? 0xffffffff : (uint32_t)cdSize);
	put32(cd, z64 ? 0xffffffff : (uint32_t)cdStart);
	put16(cd, 0);
	const bool ok = std::fwrite(cd.data(), 1, cd.size(), f_) == cd.size();
	const bool closed = std::fclose(f_) == 0;
	f_ = nullptr;
	if (!ok || !closed) { error = "Can't write the zip"; return false; }
	return true;
}

//---------------------------------------------------------------------------
// TarGzWriter
//---------------------------------------------------------------------------
namespace {
struct Gz {
	std::FILE* f = nullptr;
	z_stream zs{};
};
}

TarGzWriter::~TarGzWriter()
{
	if (gz_) {
		auto* g = (Gz*)gz_;
		deflateEnd(&g->zs);
		if (g->f) std::fclose(g->f);
		delete g;
	}
}

bool TarGzWriter::open(const fs::path& file, std::string& error)
{
	auto* g = new Gz;
	g->f = openFile(file, "wb");
	if (!g->f) { delete g; error = "Can't create " + krt::fromPath(file); return false; }
	if (deflateInit2(&g->zs, 6, Z_DEFLATED, 15 + 16, 8, Z_DEFAULT_STRATEGY) != Z_OK) { std::fclose(g->f); delete g; error = "zlib"; return false; }
	gz_ = g;
	return true;
}

bool TarGzWriter::write(const void* data, size_t n, std::string& error)
{
	auto* g = (Gz*)gz_;
	char out[1 << 16];
	g->zs.next_in = (Bytef*)data;
	g->zs.avail_in = (uInt)n;
	while (g->zs.avail_in) {
		g->zs.next_out = (Bytef*)out;
		g->zs.avail_out = sizeof(out);
		deflate(&g->zs, Z_NO_FLUSH);
		const size_t got = sizeof(out) - g->zs.avail_out;
		if (got && std::fwrite(out, 1, got, g->f) != got) { error = "Can't write the archive"; return false; }
	}
	return true;
}

namespace {
void octal(char* field, size_t len, uint64_t v)
{
	std::string s;
	do { s.insert(s.begin(), (char)('0' + (v & 7))); v >>= 3; } while (v);
	while (s.size() < len - 1) s.insert(s.begin(), '0');
	std::memcpy(field, s.data(), std::min(s.size(), len - 1));
	field[len - 1] = 0;
}
std::string paxRecord(const std::string& key, const std::string& value)
{
	const std::string body = " " + key + "=" + value + "\n";
	size_t len = body.size() + 1;
	while (std::to_string(len).size() + body.size() != len) ++len;
	return std::to_string(len) + body;
}
}

bool TarGzWriter::header(const std::string& name, char type, uint64_t size, uint32_t mode, uint64_t mtime,
                         const std::string& link, std::string& error)
{
	std::string pax;
	if (name.size() > 100) pax += paxRecord("path", name);
	if (link.size() > 100) pax += paxRecord("linkpath", link);
	if (size > 077777777777ull) pax += paxRecord("size", std::to_string(size));
	if (!pax.empty()) {
		const std::string base = name.substr(name.find_last_of('/') == std::string::npos ? 0 : name.find_last_of('/') + 1);
		if (!header("PaxHeaders/" + base.substr(0, 80), 'x', pax.size(), 0100644, mtime, "", error)) return false;
		std::string padded = pax;
		padded.resize((pax.size() + 511) / 512 * 512, '\0');
		if (!write(padded.data(), padded.size(), error)) return false;
	}
	char h[512] = {};
	std::memcpy(h, name.data(), std::min<size_t>(name.size(), 100));
	octal(h + 100, 8, mode & 07777);
	octal(h + 108, 8, 0);
	octal(h + 116, 8, 0);
	octal(h + 124, 12, size > 077777777777ull ? 0 : size);
	octal(h + 136, 12, mtime);
	std::memset(h + 148, ' ', 8);
	h[156] = type;
	std::memcpy(h + 157, link.data(), std::min<size_t>(link.size(), 100));
	std::memcpy(h + 257, "ustar", 6);
	std::memcpy(h + 263, "00", 2);
	unsigned sum = 0;
	for (unsigned char c : h) sum += c;
	char ck[8];
	octal(ck, 7, sum);
	std::memcpy(h + 148, ck, 7);
	h[155] = ' ';
	return write(h, 512, error);
}

bool TarGzWriter::addFile(const std::string& name, const fs::path& source, std::string& error, uint32_t unixMode)
{
	std::FILE* in = openFile(source, "rb");
	if (!in) { error = "Can't read " + krt::fromPath(source); return false; }
	const uint64_t size = fileSize(in);
	seek(in, 0);
	if (!header(name, '0', size, unixMode ? unixMode : diskMode(source, false), (uint64_t)mtimeOf(source), "", error)) { std::fclose(in); return false; }
	std::vector<char> buf(1 << 17);
	uint64_t left = size;
	while (left) {
		const size_t n = std::fread(buf.data(), 1, (size_t)std::min<uint64_t>(left, buf.size()), in);
		if (n == 0) { std::fclose(in); error = "Can't read " + krt::fromPath(source); return false; }
		if (!write(buf.data(), n, error)) { std::fclose(in); return false; }
		left -= n;
	}
	std::fclose(in);
	const size_t pad = (size_t)((512 - size % 512) % 512);
	static const char zeros[512] = {};
	return write(zeros, pad, error);
}

bool TarGzWriter::addDir(const std::string& name, std::string& error)
{
	const std::string n = name.empty() || name.back() == '/' ? name : name + "/";
	return header(n, '5', 0, 0755, (uint64_t)std::time(nullptr), "", error);
}

bool TarGzWriter::addSymlink(const std::string& name, const std::string& target, std::string& error)
{
	return header(name, '2', 0, 0777, (uint64_t)std::time(nullptr), target, error);
}

bool TarGzWriter::close(std::string& error)
{
	if (!gz_) return true;
	static const char zeros[1024] = {};
	if (!write(zeros, sizeof(zeros), error)) return false;
	auto* g = (Gz*)gz_;
	char out[1 << 16];
	int r;
	do {
		g->zs.next_out = (Bytef*)out;
		g->zs.avail_out = sizeof(out);
		r = deflate(&g->zs, Z_FINISH);
		const size_t got = sizeof(out) - g->zs.avail_out;
		if (got && std::fwrite(out, 1, got, g->f) != got) { error = "Can't write the archive"; return false; }
	} while (r != Z_STREAM_END);
	deflateEnd(&g->zs);
	const bool ok = std::fclose(g->f) == 0;
	delete g;
	gz_ = nullptr;
	if (!ok) { error = "Can't write the archive"; return false; }
	return true;
}

//---------------------------------------------------------------------------
// Folders
//---------------------------------------------------------------------------
namespace {
struct Item {
	std::string name;
	fs::path path;
	bool dir;
	bool link;
	std::string target;
};

std::vector<Item> listFolder(const fs::path& dir)
{
	std::vector<Item> items;
	std::error_code ec;
	for (fs::recursive_directory_iterator it(dir, ec), end; it != end; it.increment(ec)) {
		if (ec) break;
		Item i;
		i.path = it->path();
		i.name = krt::fromPath(fs::relative(it->path(), dir, ec));
		i.link = it->is_symlink(ec);
		i.dir = !i.link && it->is_directory(ec);
		if (i.link) i.target = krt::fromPath(fs::read_symlink(it->path(), ec));
		items.push_back(std::move(i));
	}
	std::sort(items.begin(), items.end(), [](const Item& a, const Item& b) { return a.name < b.name; });
	return items;
}
}

bool zipFolder(const fs::path& dir, const fs::path& out, const std::string& prefix, std::string& error,
               const std::function<uint32_t(const std::string&, uint32_t)>& modeOf)
{
	ZipWriter z;
	if (!z.open(out, error)) return false;
	if (!prefix.empty() && !z.addDir(prefix, error)) return false;
	for (const auto& i : listFolder(dir)) {
		const std::string name = prefix + i.name;
		bool ok;
		if (i.link) ok = z.addSymlink(name, i.target, error);
		else if (i.dir) ok = z.addDir(name, error);
		else ok = z.addFile(name, i.path, !isCompressedAlready(name), error,
		                    modeOf ? modeOf(i.name, diskMode(i.path, false)) : 0);
		if (!ok) return false;
	}
	return z.close(error);
}

bool tarGzFolder(const fs::path& dir, const fs::path& out, const std::string& prefix, std::string& error,
                 const std::function<uint32_t(const std::string&, uint32_t)>& modeOf)
{
	TarGzWriter t;
	if (!t.open(out, error)) return false;
	if (!prefix.empty() && !t.addDir(prefix, error)) return false;
	for (const auto& i : listFolder(dir)) {
		const std::string name = prefix + i.name;
		bool ok;
		if (i.link) ok = t.addSymlink(name, i.target, error);
		else if (i.dir) ok = t.addDir(name, error);
		else ok = t.addFile(name, i.path, error, modeOf ? modeOf(i.name, diskMode(i.path, false)) : 0);
		if (!ok) return false;
	}
	return t.close(error);
}

//---------------------------------------------------------------------------
// SHA-256
//---------------------------------------------------------------------------
namespace {
const uint32_t K[64] = {
	0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
	0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
	0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
	0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
	0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
	0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
	0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
	0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
};
inline uint32_t rotr(uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }
}

Sha256::Sha256()
{
	const uint32_t init[8] = { 0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19 };
	std::memcpy(h_, init, sizeof(h_));
}

void Sha256::block(const uint8_t* p)
{
	uint32_t w[64];
	for (int i = 0; i < 16; ++i) w[i] = (uint32_t)p[i * 4] << 24 | (uint32_t)p[i * 4 + 1] << 16 | (uint32_t)p[i * 4 + 2] << 8 | p[i * 4 + 3];
	for (int i = 16; i < 64; ++i) {
		const uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
		const uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
		w[i] = w[i - 16] + s0 + w[i - 7] + s1;
	}
	uint32_t a = h_[0], b = h_[1], c = h_[2], d = h_[3], e = h_[4], f = h_[5], g = h_[6], h = h_[7];
	for (int i = 0; i < 64; ++i) {
		const uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
		const uint32_t ch = (e & f) ^ (~e & g);
		const uint32_t t1 = h + S1 + ch + K[i] + w[i];
		const uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
		const uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
		const uint32_t t2 = S0 + maj;
		h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
	}
	h_[0] += a; h_[1] += b; h_[2] += c; h_[3] += d; h_[4] += e; h_[5] += f; h_[6] += g; h_[7] += h;
}

void Sha256::update(const void* data, size_t n)
{
	const uint8_t* p = (const uint8_t*)data;
	total_ += n;
	while (n) {
		const size_t k = std::min(n, 64 - bufLen_);
		std::memcpy(buf_ + bufLen_, p, k);
		bufLen_ += k;
		p += k;
		n -= k;
		if (bufLen_ == 64) { block(buf_); bufLen_ = 0; }
	}
}

std::string Sha256::hex()
{
	const uint64_t bits = total_ * 8;
	const uint8_t one = 0x80, zero = 0;
	update(&one, 1);
	while (bufLen_ != 56) update(&zero, 1);
	uint8_t len[8];
	for (int i = 0; i < 8; ++i) len[i] = (uint8_t)(bits >> (56 - 8 * i));
	update(len, 8);
	static const char* hexd = "0123456789abcdef";
	std::string out;
	for (uint32_t v : h_)
		for (int i = 28; i >= 0; i -= 4) out += hexd[(v >> i) & 15];
	return out;
}

bool sha256File(const fs::path& file, std::string& hex, std::string& error)
{
	std::FILE* f = openFile(file, "rb");
	if (!f) { error = "Can't read " + krt::fromPath(file); return false; }
	Sha256 s;
	std::vector<char> buf(1 << 17);
	size_t n;
	while ((n = std::fread(buf.data(), 1, buf.size(), f)) > 0) s.update(buf.data(), n);
	const bool bad = std::ferror(f) != 0;
	std::fclose(f);
	if (bad) { error = "Can't read " + krt::fromPath(file); return false; }
	hex = s.hex();
	return true;
}

} // namespace kr
