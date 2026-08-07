#ifndef FREIGHT_HASHES_H
#define FREIGHT_HASHES_H

// Checksum and hash family shared with the Java intake service and the Go
// reconciler. Every algorithm must return identical values in all three.

#include <cstdint>
#include <string>
#include <vector>

namespace freight {

uint64_t hash_fnv1a32(const std::string& data);
uint64_t hash_fnv1a64(const std::string& data);
uint64_t hash_djb2(const std::string& data);
uint64_t hash_sdbm(const std::string& data);
uint64_t hash_elf_hash(const std::string& data);
uint64_t hash_adler32(const std::string& data);
uint64_t hash_fletcher16(const std::string& data);
uint64_t hash_fletcher32(const std::string& data);
uint64_t hash_crc32_ieee(const std::string& data);
uint64_t hash_crc32c(const std::string& data);
uint64_t hash_crc16_ccitt(const std::string& data);
uint64_t hash_crc8_atm(const std::string& data);
uint64_t hash_jenkins_oaat(const std::string& data);
uint64_t hash_murmur3_32(const std::string& data);
uint64_t hash_xor_rotate(const std::string& data);
uint64_t hash_bsd_sum16(const std::string& data);

struct HashAlgorithm {
  const char* name;
  uint64_t (*apply)(const std::string& data);
};

const std::vector<HashAlgorithm>& hashRegistry();

}  // namespace freight

#endif  // FREIGHT_HASHES_H
