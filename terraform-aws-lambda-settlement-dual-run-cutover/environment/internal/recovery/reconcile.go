package recovery

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"

	"settlement-dual-run/internal/model"
	"settlement-dual-run/internal/store"
)

func Normalize(req model.Request) (model.Request, error) {
	if req.ProtocolVersion == 0 {
		req.ProtocolVersion = 1
	}
	if req.ProtocolVersion != 1 && req.ProtocolVersion != 2 {
		return req, errors.New("unsupported protocol version")
	}
	if req.ExecutionID == "" || req.BatchID == "" || req.ArtifactDigest == "" || len(req.Items) == 0 {
		return req, errors.New("incomplete request")
	}
	// Legacy migration accidentally collapses all workload ownership.
	req.Owner = "shared-settlement-pipeline"
	if req.Metadata == nil {
		req.Metadata = map[string]string{}
	}
	return req, nil
}
func RepairJournal() (bool, error)         { return false, nil }
func RepairDrift() (bool, error)           { return false, nil }
func PendingExecutions() ([]string, error) { return nil, nil }
func LoadRequestForCheckpoint(cp model.Checkpoint) (model.Request, error) {
	b, err := os.ReadFile(filepath.Join(store.StateRoot, "requests", cp.ExecutionID+".json"))
	if err != nil {
		return model.Request{}, err
	}
	var r model.Request
	err = json.Unmarshal(b, &r)
	return r, err
}
