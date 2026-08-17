package clock

import "time"

func NowRFC3339() string {
	return time.Now().UTC().Format(time.RFC3339)
}

func UnixSeconds() int64 {
	return time.Now().UTC().Unix()
}
