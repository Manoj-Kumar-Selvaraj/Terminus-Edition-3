#include "freight/hashes.h"

namespace freight {

const std::vector<HashAlgorithm>& hashRegistry() {
  static const std::vector<HashAlgorithm> registry = {
      HashAlgorithm{"fnv1a32", &hash_fnv1a32},
      HashAlgorithm{"fnv1a64", &hash_fnv1a64},
      HashAlgorithm{"djb2", &hash_djb2},
      HashAlgorithm{"sdbm", &hash_sdbm},
      HashAlgorithm{"elf_hash", &hash_elf_hash},
      HashAlgorithm{"adler32", &hash_adler32},
      HashAlgorithm{"fletcher16", &hash_fletcher16},
      HashAlgorithm{"fletcher32", &hash_fletcher32},
      HashAlgorithm{"crc32_ieee", &hash_crc32_ieee},
      HashAlgorithm{"crc32c", &hash_crc32c},
      HashAlgorithm{"crc16_ccitt", &hash_crc16_ccitt},
      HashAlgorithm{"crc8_atm", &hash_crc8_atm},
      HashAlgorithm{"jenkins_oaat", &hash_jenkins_oaat},
      HashAlgorithm{"murmur3_32", &hash_murmur3_32},
      HashAlgorithm{"xor_rotate", &hash_xor_rotate},
      HashAlgorithm{"bsd_sum16", &hash_bsd_sum16},
  };
  return registry;
}

}  // namespace freight
