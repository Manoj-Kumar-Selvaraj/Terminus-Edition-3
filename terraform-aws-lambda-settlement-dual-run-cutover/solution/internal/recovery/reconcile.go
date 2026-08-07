package recovery

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"settlement-dual-run/internal/model"
	"settlement-dual-run/internal/simclient"
	"settlement-dual-run/internal/store"
)

func Normalize(req model.Request) (model.Request, error) {
	switch req.ProtocolVersion {
	case 0, 1:
		req.ProtocolVersion = 1
		if req.Owner == "" {
			req.Owner = "legacy-jenkins/" + req.BatchID
		}
	case 2:
		if strings.TrimSpace(req.Owner) == "" {
			return req, errors.New("protocol v2 requires owner")
		}
	default:
		return req, fmt.Errorf("unsupported protocol version %d", req.ProtocolVersion)
	}
	if req.ExecutionID == "" || req.BatchID == "" || req.ArtifactDigest == "" {
		return req, errors.New("execution_id, batch_id, and artifact_digest are required")
	}
	if len(req.Items) == 0 {
		return req, errors.New("at least one item is required")
	}
	seen := map[string]bool{}
	for _, it := range req.Items {
		if it.ID == "" || seen[it.ID] {
			return req, errors.New("item ids must be non-empty and unique")
		}
		seen[it.ID] = true
	}
	if req.Metadata == nil {
		req.Metadata = map[string]string{}
	}
	return req, nil
}

type RuntimeState struct {
	ActiveGeneration int             `json:"active_generation"`
	Writer           string          `json:"writer"`
	Epoch            int64           `json:"epoch"`
	Drift            map[string]bool `json:"drift"`
}

func RepairJournal() (bool, error) {
	records, corrupt, err := store.ReadJournalTolerant()
	if err != nil {
		return false, err
	}
	if !corrupt {
		return false, nil
	}
	return true, store.RewriteJournal(records)
}

func RepairDrift() (bool, error) {
	var runtime RuntimeState
	if err := simclient.CallArgs([]string{"inspect", "state"}, nil, &runtime); err != nil {
		return false, err
	}
	key := fmt.Sprintf("generation:%d", runtime.ActiveGeneration)
	if !runtime.Drift[key] {
		return false, nil
	}
	d, err := store.LoadDeployment(runtime.ActiveGeneration)
	if err != nil {
		return false, err
	}
	var response struct {
		OK      bool   `json:"ok"`
		Message string `json:"message"`
	}
	if err := simclient.Call("deploy", d, &response); err != nil {
		return false, err
	}
	if !response.OK {
		return false, errors.New(response.Message)
	}
	if err := simclient.Call("clear-drift", nil, nil); err != nil {
		return false, err
	}
	return true, nil
}

func PendingExecutions() ([]string, error) {
	all, err := store.ListCheckpoints()
	if err != nil {
		return nil, err
	}
	var ids []string
	for _, cp := range all {
		if cp.Status == "RUNNING" || cp.Status == "RETRY_PENDING" {
			ids = append(ids, cp.ExecutionID)
		}
	}
	sort.Strings(ids)
	return ids, nil
}

func LoadRequestForCheckpoint(cp model.Checkpoint) (model.Request, error) {
	path := filepath.Join(store.StateRoot, "requests", cp.ExecutionID+".json")
	b, err := os.ReadFile(path)
	if err != nil {
		return model.Request{}, err
	}
	return decodeRequest(b)
}

var decodeRequest = func(b []byte) (model.Request, error) {
	var r model.Request
	err := json.Unmarshal(b, &r)
	return r, err
}
