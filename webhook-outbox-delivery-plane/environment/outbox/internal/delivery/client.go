package delivery

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"time"

	"outbox/internal/sign"
)

type Result struct {
	HTTPStatus int
	Error      string
	OK         bool
	Body       []byte
}

type Client struct {
	HTTP    *http.Client
	Timeout time.Duration
}

func NewClient() *Client {
	return &Client{
		HTTP: &http.Client{Timeout: 10 * time.Second},
		Timeout: 10 * time.Second,
	}
}

func (c *Client) Post(ctx context.Context, url, secret, eventID string, unixTS int64, body []byte) Result {
	headers := sign.SignHeaders(secret, eventID, unixTS, body)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return Result{Error: err.Error()}
	}
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return Result{Error: err.Error()}
	}
	defer resp.Body.Close()
	respBody, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	ok := resp.StatusCode >= 200 && resp.StatusCode < 300
	errMsg := ""
	if !ok {
		errMsg = fmt.Sprintf("http_%d", resp.StatusCode)
	}
	return Result{HTTPStatus: resp.StatusCode, Error: errMsg, OK: ok, Body: respBody}
}
