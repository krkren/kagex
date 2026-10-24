//---------------------------------------------------------------------------
// zip (read and write, with ZIP64, Unix permissions and symbolic links), tar.gz (write) and
// SHA-256, for the engine packages and the release packages
//---------------------------------------------------------------------------
#pragma once
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <functional>
#include <string>
#include <vector>

namespace kr {

//---------------------------------------------------------------------------
// Reading zip files
//---------------------------------------------------------------------------
struct ZipEntry {
	std::string name;           ///< '/' separated; folders end in '/'
	uint64_t    compressedSize = 0;
	uint64_t    size = 0;
	uint64_t    localHeaderOffset = 0;
	uint16_t    method = 0;     ///< 0 = stored, 8 = deflated
	uint32_t    crc = 0;
	uint32_t    unixMode = 0;   ///< 0 when the zip didn't record one
	bool isDir() const { return !name.empty() && name.back() == '/'; }
	bool isSymlink() const { return (unixMode & 0170000) == 0120000; }
};

class ZipReader {
public:
	~ZipReader();
	bool open(const std::filesystem::path& file, std::string& error);
	const std::vector<ZipEntry>& entries() const { return entries_; }
	bool read(const ZipEntry& e, std::string& out, std::string& error);
	/// Extracts everything under dir (names that would leave dir are refused)
	bool extractAll(const std::filesystem::path& dir, std::string& error,
	                const std::function<bool(const ZipEntry&)>& filter = nullptr);

private:
	std::FILE* f_ = nullptr;
	std::vector<ZipEntry> entries_;
	bool dataOffset(const ZipEntry& e, uint64_t& offset, std::string& error);
};

//---------------------------------------------------------------------------
// Writing zip files
//---------------------------------------------------------------------------
class ZipWriter {
public:
	~ZipWriter();
	bool open(const std::filesystem::path& file, std::string& error);
	/// A file from disk. compress = false stores it (for files that are compressed already);
	/// unixMode 0 = the file's own
	bool addFile(const std::string& name, const std::filesystem::path& source, bool compress, std::string& error,
	             uint32_t unixMode = 0);
	bool addData(const std::string& name, const std::string& data, uint32_t unixMode, std::string& error);
	bool addDir(const std::string& name, std::string& error);
	bool addSymlink(const std::string& name, const std::string& target, std::string& error);
	bool close(std::string& error);

private:
	struct Central {
		std::string name;
		uint64_t compressedSize, size, offset;
		uint32_t crc, unixMode, dosTime;
		uint16_t method;
	};
	bool writeEntry(const std::string& name, uint32_t unixMode, uint32_t dosTime, bool compress,
	                const std::function<size_t(char*, size_t)>& source, uint64_t sizeHint, std::string& error);
	std::FILE* f_ = nullptr;
	std::vector<Central> central_;
};

//---------------------------------------------------------------------------
// Writing tar.gz files (POSIX pax: long names, big files, permissions, symbolic links)
//---------------------------------------------------------------------------
class TarGzWriter {
public:
	~TarGzWriter();
	bool open(const std::filesystem::path& file, std::string& error);
	bool addFile(const std::string& name, const std::filesystem::path& source, std::string& error, uint32_t unixMode = 0);
	bool addDir(const std::string& name, std::string& error);
	bool addSymlink(const std::string& name, const std::string& target, std::string& error);
	bool close(std::string& error);

private:
	bool header(const std::string& name, char type, uint64_t size, uint32_t mode, uint64_t mtime,
	            const std::string& link, std::string& error);
	bool write(const void* data, size_t n, std::string& error);
	void* gz_ = nullptr;
};

/// Packs a folder: its contents under prefix ("" or "Game-1.0/"), in name order. Unix modes
/// come from the files (on Windows: executable for executables), or from modeOf when given
bool zipFolder(const std::filesystem::path& dir, const std::filesystem::path& out, const std::string& prefix,
               std::string& error, const std::function<uint32_t(const std::string&, uint32_t)>& modeOf = nullptr);
bool tarGzFolder(const std::filesystem::path& dir, const std::filesystem::path& out, const std::string& prefix,
                 std::string& error, const std::function<uint32_t(const std::string&, uint32_t)>& modeOf = nullptr);

/// Files that gain nothing from deflate (media, archives)
bool isCompressedAlready(const std::string& name);

//---------------------------------------------------------------------------
// SHA-256
//---------------------------------------------------------------------------
class Sha256 {
public:
	Sha256();
	void update(const void* data, size_t n);
	std::string hex();   ///< finishes
private:
	void block(const uint8_t* p);
	uint32_t h_[8];
	uint8_t  buf_[64];
	size_t   bufLen_ = 0;
	uint64_t total_ = 0;
};
bool sha256File(const std::filesystem::path& file, std::string& hex, std::string& error);

} // namespace kr
