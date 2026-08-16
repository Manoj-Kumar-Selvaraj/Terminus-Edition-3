package sign

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strconv"
)

func Canonical(id string, unixTS int64, body []byte) string {
	return fmt.Sprintf("%s|%s", id, string(body))
}

func SignatureHex(secret, canonical string) string {
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write([]byte(canonical))
	return hex.EncodeToString(mac.Sum(nil))
}

func SignHeaders(secret, id string, unixTS int64, body []byte) map[string]string {
	canon := Canonical(id, unixTS, body)
	return map[string]string{
		"Content-Type":       "application/json",
		"X-Outbox-Id":        id,
		"X-Outbox-Timestamp": strconv.FormatInt(unixTS, 10),
		"X-Outbox-Signature": SignatureHex(secret, canon),
	}
}

func Verify(secret, id string, unixTS int64, body []byte, sigHex string) bool {
	expect := SignatureHex(secret, Canonical(id, unixTS, body))
	return hmac.Equal([]byte(expect), []byte(sigHex))
}
