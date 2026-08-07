package codecx

const hexDigits = "0123456789abcdef"
const upperHex = "0123456789ABCDEF"
const base32Alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
const base64Alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

var xorPad = [8]byte{0x5A, 0x3C, 0x71, 0x0F, 0xC3, 0xA5, 0x69, 0x96}

func hexValue(c byte) int {
	switch {
	case c >= '0' && c <= '9':
		return int(c - '0')
	case c >= 'a' && c <= 'f':
		return int(c-'a') + 10
	case c >= 'A' && c <= 'F':
		return int(c-'A') + 10
	}
	return -1
}

func base32Value(c byte) int {
	switch {
	case c >= 'A' && c <= 'Z':
		return int(c - 'A')
	case c >= '2' && c <= '7':
		return int(c-'2') + 26
	}
	return -1
}

func base64Value(c byte) int {
	switch {
	case c >= 'A' && c <= 'Z':
		return int(c - 'A')
	case c >= 'a' && c <= 'z':
		return int(c-'a') + 26
	case c >= '0' && c <= '9':
		return int(c-'0') + 52
	case c == '+':
		return 62
	case c == '/':
		return 63
	}
	return -1
}
