package httpx

import (
	"net"
	"net/http"
	"time"
)

func WaitHTTP(url string, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	var last error
	for time.Now().Before(deadline) {
		resp, err := http.Get(url)
		if err == nil {
			_ = resp.Body.Close()
			if resp.StatusCode == 200 {
				return nil
			}
			last = err
		} else {
			last = err
		}
		time.Sleep(50 * time.Millisecond)
	}
	if last == nil {
		last = net.ErrClosed
	}
	return last
}

func FreePort() (string, error) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return "", err
	}
	defer ln.Close()
	return ln.Addr().String(), nil
}
