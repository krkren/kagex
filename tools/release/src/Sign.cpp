#include "Sign.h"

#include <cstring>
#include <mutex>
#include <vector>

#include <tomcrypt.h>

#include "krt/sig/Signature.h"
#include "krt/app/Text.h"

namespace fs = std::filesystem;

namespace kr {

namespace {

const char kPubBegin[] = "-----BEGIN PUBLIC KEY-----";
const char kPubEnd[]   = "-----END PUBLIC KEY-----";
const char kPrivBegin[] = "-----BEGIN RSA PRIVATE KEY-----";
const char kPrivEnd[]   = "-----END RSA PRIVATE KEY-----";

void cryptInit()
{
	static std::once_flag once;
	std::call_once(once, [] {
		ltc_mp = ltm_desc;
		if (find_hash("sha256") == -1) register_hash(&sha256_desc);
		if (find_prng("sprng") == -1) register_prng(&sprng_desc);
	});
}

// Base64 of DER, wrapped at 64 columns with CRLF (as krt::sig / the old krkrsign emit).
std::string wrapPem(const char* begin, const char* end, const unsigned char* der, unsigned long len)
{
	std::string b64(len * 4 / 3 + 8, '\0');
	unsigned long outLen = (unsigned long)b64.size();
	base64_encode(der, len, reinterpret_cast<unsigned char*>(b64.data()), &outLen);
	b64.resize(outLen);
	std::string wrapped;
	for (size_t i = 0; i < b64.size(); i += 64) wrapped += b64.substr(i, 64) + "\r\n";
	return std::string(begin) + "\r\n" + wrapped + end + "\r\n";
}

// The DER inside a PEM block (handles stray leading dashes and whitespace, like krt::sig).
bool pemToDer(const std::string& text, const char* begin, const char* end,
              std::vector<unsigned char>& der, std::string& err)
{
	const std::string head(begin, std::strlen(begin) - 1);   // tolerate a varying trailing dash count
	const auto b = text.find(head);
	if (b == std::string::npos) { err = std::string("the key has no \"") + begin + "\" line"; return false; }
	const auto e = text.find(end, b);
	if (e == std::string::npos) { err = std::string("the key has no \"") + end + "\" line"; return false; }
	size_t s = b + head.size();
	while (s < e && text[s] == '-') ++s;
	der.resize((e - s) + 16);
	unsigned long outLen = (unsigned long)der.size();
	const int r = base64_decode(reinterpret_cast<const unsigned char*>(text.data() + s),
	                            (unsigned long)(e - s), der.data(), &outLen);
	if (r != CRYPT_OK) { err = error_to_string(r); return false; }
	der.resize(outLen);
	return true;
}

} // namespace

bool generateSigningKeys(int bits, std::string& publicPem, std::string& privatePem, std::string& error)
{
	krt::sig::KeyPair kp;
	if (!krt::sig::generateKeyPair(bits, kp, error)) return false;
	publicPem = kp.publicKey;
	privatePem = kp.privateKey;
	return true;
}

bool derivePublicKey(const std::string& privatePem, std::string& publicPem, std::string& error)
{
	cryptInit();
	std::vector<unsigned char> der;
	if (!pemToDer(privatePem, kPrivBegin, kPrivEnd, der, error)) return false;
	rsa_key key;
	int e = rsa_import(der.data(), (unsigned long)der.size(), &key);
	if (e != CRYPT_OK) { error = std::string("can't read the private key: ") + error_to_string(e); return false; }
	if (key.type != PK_PRIVATE) { rsa_free(&key); error = "that isn't a private key"; return false; }
	std::vector<unsigned char> out(16 * 1024);
	unsigned long len = (unsigned long)out.size();
	e = rsa_export(out.data(), &len, PK_PUBLIC, &key);   // no PK_STD = PKCS#1, as krt::sig does
	rsa_free(&key);
	if (e != CRYPT_OK) { error = error_to_string(e); return false; }
	publicPem = wrapPem(kPubBegin, kPubEnd, out.data(), len);
	return true;
}

bool signFileWith(const fs::path& file, const std::string& privatePem, std::string& error)
{
	const krt::sig::SignResult r = krt::sig::signFile(file, privatePem);
	if (!r.ok) { error = r.message.empty() ? "signing failed" : r.message; return false; }
	return true;
}

bool verifyFileWith(const fs::path& file, const std::string& publicPem, std::string& error)
{
	const krt::sig::VerifyResult r = krt::sig::verifyFile(file, publicPem);
	if (r.status == krt::sig::Status::Ok) return true;
	error = r.message.empty() ? std::string(krt::sig::statusName(r.status)) : r.message;
	return false;
}

bool readKeyText(const fs::path& file, std::string& text, std::string& error)
{
	if (!krt::readFile(file, text)) { error = "can't read " + krt::fromPath(file); return false; }
	return true;
}

bool looksLikePrivateKey(const std::string& text)
{
	return text.find(kPrivBegin) != std::string::npos;
}

} // namespace kr
