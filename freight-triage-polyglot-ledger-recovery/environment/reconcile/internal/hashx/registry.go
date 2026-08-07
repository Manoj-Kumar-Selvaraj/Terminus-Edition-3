package hashx

// Registry lists every checksum algorithm in catalogue order.
func Registry() []Algorithm {
	return []Algorithm{
		{Name: "fnv1a32", Apply: Fnv1a32},
		{Name: "fnv1a64", Apply: Fnv1a64},
		{Name: "djb2", Apply: Djb2},
		{Name: "sdbm", Apply: Sdbm},
		{Name: "elf_hash", Apply: ElfHash},
		{Name: "adler32", Apply: Adler32},
		{Name: "fletcher16", Apply: Fletcher16},
		{Name: "fletcher32", Apply: Fletcher32},
		{Name: "crc32_ieee", Apply: Crc32Ieee},
		{Name: "crc32c", Apply: Crc32c},
		{Name: "crc16_ccitt", Apply: Crc16Ccitt},
		{Name: "crc8_atm", Apply: Crc8Atm},
		{Name: "jenkins_oaat", Apply: JenkinsOaat},
		{Name: "murmur3_32", Apply: Murmur332},
		{Name: "xor_rotate", Apply: XorRotate},
		{Name: "bsd_sum16", Apply: BsdSum16},
	}
}
