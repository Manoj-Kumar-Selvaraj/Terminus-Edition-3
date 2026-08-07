#include "freight/sha256.h"

#include <cstdio>
#include <cstring>

namespace freight {
namespace {

const uint32_t kRoundConstants[64] = {
    0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u, 0x3956c25bu, 0x59f111f1u,
    0x923f82a4u, 0xab1c5ed5u, 0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u,
    0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u, 0xe49b69c1u, 0xefbe4786u,
    0x0fc19dc6u, 0x240ca1ccu, 0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
    0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u, 0xc6e00bf3u, 0xd5a79147u,
    0x06ca6351u, 0x14292967u, 0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u,
    0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u, 0xa2bfe8a1u, 0xa81a664bu,
    0xc24b8b70u, 0xc76c51a3u, 0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
    0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u, 0x391c0cb3u, 0x4ed8aa4au,
    0x5b9cca4fu, 0x682e6ff3u, 0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u,
    0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u};

inline uint32_t rotateRight(uint32_t value, unsigned int bits) {
  return (value >> bits) | (value << (32u - bits));
}

inline uint32_t loadBigEndian32(const uint8_t* data) {
  return (static_cast<uint32_t>(data[0]) << 24) | (static_cast<uint32_t>(data[1]) << 16) |
         (static_cast<uint32_t>(data[2]) << 8) | static_cast<uint32_t>(data[3]);
}

void storeBigEndian32(uint8_t* out, uint32_t value) {
  out[0] = static_cast<uint8_t>((value >> 24) & 0xFFu);
  out[1] = static_cast<uint8_t>((value >> 16) & 0xFFu);
  out[2] = static_cast<uint8_t>((value >> 8) & 0xFFu);
  out[3] = static_cast<uint8_t>(value & 0xFFu);
}

}  // namespace

Sha256::Sha256() { reset(); }

void Sha256::reset() {
  state_[0] = 0x6a09e667u;
  state_[1] = 0xbb67ae85u;
  state_[2] = 0x3c6ef372u;
  state_[3] = 0xa54ff53au;
  state_[4] = 0x510e527fu;
  state_[5] = 0x9b05688cu;
  state_[6] = 0x1f83d9abu;
  state_[7] = 0x5be0cd19u;
  length_ = 0;
  buffered_ = 0;
  std::memset(buffer_, 0, sizeof(buffer_));
}

void Sha256::compress(const uint8_t block[64]) {
  uint32_t w[64];
  for (int i = 0; i < 16; ++i) {
    w[i] = loadBigEndian32(block + i * 4);
  }
  for (int i = 16; i < 64; ++i) {
    uint32_t s0 = rotateRight(w[i - 15], 7) ^ rotateRight(w[i - 15], 18) ^ (w[i - 15] >> 3);
    uint32_t s1 = rotateRight(w[i - 2], 17) ^ rotateRight(w[i - 2], 19) ^ (w[i - 2] >> 10);
    w[i] = w[i - 16] + s0 + w[i - 7] + s1;
  }

  uint32_t a = state_[0];
  uint32_t b = state_[1];
  uint32_t c = state_[2];
  uint32_t d = state_[3];
  uint32_t e = state_[4];
  uint32_t f = state_[5];
  uint32_t g = state_[6];
  uint32_t h = state_[7];

  for (int i = 0; i < 64; ++i) {
    uint32_t s1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
    uint32_t ch = (e & f) ^ ((~e) & g);
    uint32_t temp1 = h + s1 + ch + kRoundConstants[i] + w[i];
    uint32_t s0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22);
    uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
    uint32_t temp2 = s0 + maj;
    h = g;
    g = f;
    f = e;
    e = d + temp1;
    d = c;
    c = b;
    b = a;
    a = temp1 + temp2;
  }

  state_[0] += a;
  state_[1] += b;
  state_[2] += c;
  state_[3] += d;
  state_[4] += e;
  state_[5] += f;
  state_[6] += g;
  state_[7] += h;
}

void Sha256::update(const void* data, size_t length) {
  const uint8_t* cursor = static_cast<const uint8_t*>(data);
  length_ += static_cast<uint64_t>(length) * 8u;
  while (length > 0) {
    size_t take = 64 - buffered_;
    if (take > length) {
      take = length;
    }
    std::memcpy(buffer_ + buffered_, cursor, take);
    buffered_ += take;
    cursor += take;
    length -= take;
    if (buffered_ == 64) {
      compress(buffer_);
      buffered_ = 0;
    }
  }
}

void Sha256::update(const std::string& text) { update(text.data(), text.size()); }

std::string Sha256::hexDigest() {
  uint64_t bitLength = length_;
  uint8_t padding[72];
  std::memset(padding, 0, sizeof(padding));
  padding[0] = 0x80;
  size_t padLength = (buffered_ < 56) ? (56 - buffered_) : (120 - buffered_);
  update(padding, padLength);

  uint8_t tail[8];
  for (int i = 0; i < 8; ++i) {
    tail[7 - i] = static_cast<uint8_t>((bitLength >> (8 * i)) & 0xFFu);
  }
  length_ = bitLength;
  std::memcpy(buffer_ + buffered_, tail, 8);
  buffered_ += 8;
  compress(buffer_);
  buffered_ = 0;

  uint8_t digest[32];
  for (int i = 0; i < 8; ++i) {
    storeBigEndian32(digest + i * 4, state_[i]);
  }
  char hex[65];
  for (int i = 0; i < 32; ++i) {
    std::snprintf(hex + i * 2, 3, "%02x", digest[i]);
  }
  hex[64] = '\0';
  return std::string(hex);
}

std::string sha256Hex(const std::string& text) {
  Sha256 hasher;
  hasher.update(text);
  return hasher.hexDigest();
}

}  // namespace freight
