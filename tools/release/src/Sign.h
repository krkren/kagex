//---------------------------------------------------------------------------
// Signing (RSA-PSS / SHA-256), for kagex-release's signing option.
//
// The format must match the key-and-signing tool (krkrsign) and the engine's sigcheck plugin,
// so the heavy lifting goes through krkrz_tools' krt::sig (the same library krkrsign uses):
// generate a key pair, sign a file (writes <file>.sig, or embeds into a krkrz executable), and
// verify. Only deriving the public key from a private key isn't in krt::sig, so it is done here
// with libtomcrypt, in the same PKCS#1 PEM form krt::sig emits.
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <string>

namespace kr {

/// A new key pair (1024 / 2048 / 3072 / 4096 bits), as PEM text.
bool generateSigningKeys(int bits, std::string& publicPem, std::string& privatePem, std::string& error);

/// The public key that matches a private key, as PEM text.
bool derivePublicKey(const std::string& privatePem, std::string& publicPem, std::string& error);

/// Signs a file in place: writes <file>.sig, or embeds the signature into a krkrz executable.
bool signFileWith(const std::filesystem::path& file, const std::string& privatePem, std::string& error);

/// Verifies a file against a public key (true only when the signature is valid).
bool verifyFileWith(const std::filesystem::path& file, const std::string& publicPem, std::string& error);

/// Reads a key file as text (the PEM block may have other lines around it).
bool readKeyText(const std::filesystem::path& file, std::string& text, std::string& error);

/// A rough check that text holds an RSA private key block (for validation messages).
bool looksLikePrivateKey(const std::string& text);

} // namespace kr
