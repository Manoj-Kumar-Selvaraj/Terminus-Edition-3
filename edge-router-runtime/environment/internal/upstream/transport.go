package upstream

import (
	"context"
	"errors"
	"io"
	"net"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	rt "edge-router/internal/runtime"
)

type Result struct {
	StatusCode int
	Header     http.Header
	Body       []byte
	Duration   time.Duration
}

type Transport struct {
	mu         sync.Mutex
	clients    map[string]*http.Client
	transports map[string]*http.Transport
	maxBody    int64
}

func New() *Transport {
	return &Transport{
		clients:    make(map[string]*http.Client),
		transports: make(map[string]*http.Transport),
		maxBody:    8 << 20,
	}
}

func (t *Transport) client(endpoint *rt.EndpointRuntime) *http.Client {
	key := endpoint.PoolID + "\x00" + endpoint.Identity
	t.mu.Lock()
	defer t.mu.Unlock()
	if client := t.clients[key]; client != nil {
		return client
	}
	transport := &http.Transport{
		Proxy:                 http.ProxyFromEnvironment,
		DialContext:           (&net.Dialer{Timeout: 2 * time.Second, KeepAlive: 30 * time.Second}).DialContext,
		ForceAttemptHTTP2:     false,
		MaxIdleConns:          256,
		MaxIdleConnsPerHost:   32,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   3 * time.Second,
		ResponseHeaderTimeout: 5 * time.Second,
	}
	client := &http.Client{Transport: transport, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	t.clients[key] = client
	t.transports[key] = transport
	endpoint.AddConnection()
	return client
}

func (t *Transport) Do(ctx context.Context, endpoint *rt.EndpointRuntime, incoming *http.Request, body []byte) (Result, error) {
	if endpoint == nil {
		return Result{}, errors.New("nil endpoint runtime")
	}
	if !endpoint.BeginRequest() {
		return Result{}, errors.New("endpoint is retired")
	}
	defer endpoint.EndRequest()
	target := &url.URL{Scheme: "http", Host: endpoint.Address, Path: incoming.URL.Path, RawQuery: incoming.URL.RawQuery}
	request, err := http.NewRequestWithContext(ctx, incoming.Method, target.String(), strings.NewReader(string(body)))
	if err != nil {
		return Result{}, err
	}
	copyHeaders(request.Header, incoming.Header)
	request.Host = incoming.Host
	request.Header.Set("X-Forwarded-Host", incoming.Host)
	request.Header.Set("X-Forwarded-Proto", forwardedProto(incoming))
	request.Header.Set("X-Edge-Endpoint", endpoint.Identity)
	started := time.Now()
	response, err := t.client(endpoint).Do(request)
	if err != nil {
		return Result{Duration: time.Since(started)}, err
	}
	defer response.Body.Close()
	payload, err := io.ReadAll(io.LimitReader(response.Body, t.maxBody+1))
	if err != nil {
		return Result{Duration: time.Since(started)}, err
	}
	if int64(len(payload)) > t.maxBody {
		return Result{Duration: time.Since(started)}, errors.New("upstream response exceeds body limit")
	}
	return Result{StatusCode: response.StatusCode, Header: response.Header.Clone(), Body: payload, Duration: time.Since(started)}, nil
}

func (t *Transport) CloseEndpoint(endpoint *rt.EndpointRuntime) {
	if endpoint == nil {
		return
	}
	key := endpoint.PoolID + "\x00" + endpoint.Identity
	t.mu.Lock()
	transport := t.transports[key]
	delete(t.transports, key)
	delete(t.clients, key)
	t.mu.Unlock()
	if transport != nil {
		transport.CloseIdleConnections()
	}
	endpoint.DropConnection()
}

func (t *Transport) CloseAll() {
	t.mu.Lock()
	transports := make([]*http.Transport, 0, len(t.transports))
	for _, transport := range t.transports {
		transports = append(transports, transport)
	}
	t.clients = make(map[string]*http.Client)
	t.transports = make(map[string]*http.Transport)
	t.mu.Unlock()
	for _, transport := range transports {
		transport.CloseIdleConnections()
	}
}

func copyHeaders(destination, source http.Header) {
	for key, values := range source {
		if hopByHop(key) {
			continue
		}
		for _, value := range values {
			destination.Add(key, value)
		}
	}
}

func hopByHop(key string) bool {
	switch strings.ToLower(key) {
	case "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade":
		return true
	default:
		return false
	}
}

func forwardedProto(request *http.Request) string {
	if request.TLS != nil {
		return "https"
	}
	return "http"
}
