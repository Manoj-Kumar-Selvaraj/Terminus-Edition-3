package httpx

import (
	"fmt"
	"net"
	"net/http"
	"time"
)

func WaitHTTP(url string, timeout time.Duration) error {
	return WaitHTTPStatus(url, timeout, 200)
}

func WaitHTTPStatus(url string, timeout time.Duration, want int) error {
	if timeout <= 0 {
		timeout = 10 * time.Second
	}
	deadline := time.Now().Add(timeout)
	var last error
	client := &http.Client{Timeout: 2 * time.Second}
	for time.Now().Before(deadline) {
		resp, err := client.Get(url)
		if err == nil {
			code := resp.StatusCode
			_ = resp.Body.Close()
			if code == want {
				return nil
			}
			last = fmt.Errorf("httpx: status %d want %d", code, want)
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
