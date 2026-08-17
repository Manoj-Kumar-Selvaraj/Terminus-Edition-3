package controlplane

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"fleetrollout/internal/types"
)

type Client struct {
	Base string
	HTTP *http.Client
}

func New(base string) *Client {
	if base == "" {
		base = "http://127.0.0.1:18080"
	}
	return &Client{Base: strings.TrimRight(base, "/"), HTTP: http.DefaultClient}
}

func (c *Client) Inventory() (types.Value, error) {
	resp, err := c.HTTP.Get(c.Base + "/v1/inventory")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("inventory status %d: %s", resp.StatusCode, body)
	}
	result := types.Value{}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (c *Client) Commit(owner string, state types.Value, lost bool) (int, error) {
	payload, _ := json.Marshal(types.Value{
		"owner_token":                 owner,
		"state":                       state,
		"control_plane_response_lost": lost,
	})
	resp, err := c.HTTP.Post(c.Base+"/v1/commit", "application/json", bytes.NewReader(payload))
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	_, _ = io.ReadAll(resp.Body)
	return resp.StatusCode, nil
}

func (c *Client) Reset() error {
	resp, err := c.HTTP.Post(c.Base+"/v1/reset", "application/json", bytes.NewReader([]byte("{}")))
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	_, _ = io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusNoContent && resp.StatusCode != http.StatusOK {
		return fmt.Errorf("reset status %d", resp.StatusCode)
	}
	return nil
}
