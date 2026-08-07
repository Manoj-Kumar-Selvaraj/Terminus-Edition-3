#ifndef FREIGHT_SHA256_H
#define FREIGHT_SHA256_H

// FIPS 180-4 SHA-256 used for every ledger and audit digest.

#include <cstddef>
#include <cstdint>
#include <string>

namespace freight {

class Sha256 {
 public:
  Sha256();
  void reset();
  void update(const void* data, size_t length);
  void update(const std::string& text);
  std::string hexDigest();

 private:
  void compress(const uint8_t block[64]);

  uint32_t state_[8];
  uint64_t length_;
  uint8_t buffer_[64];
  size_t buffered_;
};

std::string sha256Hex(const std::string& text);

}  // namespace freight

#endif  // FREIGHT_SHA256_H
