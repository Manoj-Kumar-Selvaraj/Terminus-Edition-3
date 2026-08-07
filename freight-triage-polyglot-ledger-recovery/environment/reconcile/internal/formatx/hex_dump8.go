package formatx

import "fmt"

// HexDump8 renders a value with the hex dump8 rule.
func HexDump8(value int64) string {
	return fmt.Sprintf("%08x", uint32(uint64(value)&0xFFFFFFFF))
}
