package engine

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"

	"settlement-dual-run/internal/cutover"
	"settlement-dual-run/internal/fanout"
	"settlement-dual-run/internal/model"
	"settlement-dual-run/internal/simclient"
	"settlement-dual-run/internal/store"
)

func Deploy(infraDir string, deployment model.Deployment) error {
	var response struct {
		OK      bool   `json:"ok"`
		Class   string `json:"class"`
		Message string `json:"message"`
	}
	for attempt := 0; attempt < 3; attempt++ {
		if err := simclient.Call("deploy", deployment, &response); err != nil {
			return err
		}
		if response.OK {
			break
		}
		if response.Class != "transient" {
			return errors.New(response.Message)
		}
	}
	if !response.OK {
		return errors.New(response.Message)
	}
	if err := store.SaveDeployment(deployment); err != nil {
		return err
	}
	_, err := cutover.Ensure(deployment.Generation)
	return err
}

func NewCheckpoint(req model.Request, generation int, epoch int64) model.Checkpoint {
	items := make([]model.ItemState, 0, len(req.Items))
	for _, it := range req.Items {
		items = append(items, model.ItemState{ID: it.ID, Status: "PENDING"})
	}
	return model.Checkpoint{ExecutionID: req.ExecutionID, BatchID: req.BatchID, Owner: req.Owner, ProtocolVersion: req.ProtocolVersion, ArtifactDigest: req.ArtifactDigest, Generation: generation, Epoch: epoch, Status: "RUNNING", Metadata: req.Metadata, Items: items, CompletedEffects: map[string]string{}, Attempts: map[string]int{}, UpdatedAt: simclient.Now()}
}

func Run(req model.Request) (model.Checkpoint, error) {
	if existing, err := store.LoadCheckpoint(req.ExecutionID); err == nil {
		if existing.BatchID != req.BatchID || existing.Owner != req.Owner || existing.ArtifactDigest != req.ArtifactDigest {
			return existing, fmt.Errorf("execution id reused with conflicting payload")
		}
		return Resume(req, existing)
	}
	c, err := cutover.Load()
	if err != nil {
		return model.Checkpoint{}, err
	}
	cp := NewCheckpoint(req, c.ActiveGeneration, c.Epoch)
	if err := store.SaveCheckpoint(cp); err != nil {
		return cp, err
	}
	return Resume(req, cp)
}

func Resume(req model.Request, cp model.Checkpoint) (model.Checkpoint, error) {
	if cp.Owner != req.Owner {
		return cp, fmt.Errorf("owner mismatch")
	}
	itemByID := map[string]model.Item{}
	for _, it := range req.Items {
		itemByID[it.ID] = it
	}
	for stageIndex := cp.NextStage; stageIndex < len(model.RequiredStages); stageIndex++ {
		stage := model.RequiredStages[stageIndex]
		if isItemStage(stage) {
			for idx := range cp.Items {
				state := &cp.Items[idx]
				if state.Status == "DLQ" {
					continue
				}
				it := itemByID[state.ID]
				meta := copyMap(req.Metadata)
				meta["artifact_digest"] = req.ArtifactDigest
				if it.Poison {
					meta["poison"] = "true"
				}
				inv := model.Invocation{Stage: stage, ExecutionID: req.ExecutionID, BatchID: req.BatchID, ItemID: it.ID, Generation: cp.Generation, Epoch: cp.Epoch, Owner: req.Owner, IdempotencyKey: operationID(req.ExecutionID, stage, it.ID), Metadata: meta}
				result, attempts, callErr := invokeRecorded(inv)
				cp.Attempts[stage+"/"+it.ID] += attempts
				state.Attempts += attempts
				state.LastStage = stage
				if callErr != nil {
					cp.Status = "RETRY_PENDING"
					cp.LastError = callErr.Error()
					cp.UpdatedAt = simclient.Now()
					_ = store.SaveCheckpoint(cp)
					return cp, callErr
				}
				if !result.OK && !result.Duplicate {
					if result.Class == "permanent" && stage == "validate_inputs" {
						state.Status = "DLQ"
						state.Error = result.Message
						if err := fanout.SendDLQ(req.BatchID, it.ID); err != nil {
							return cp, err
						}
						continue
					}
					cp.Status = "FAILED"
					cp.LastError = result.Message
					cp.UpdatedAt = simclient.Now()
					_ = store.SaveCheckpoint(cp)
					return cp, errors.New(result.Message)
				}
				state.Status = "ACTIVE"
				if stage == "write_ledger" {
					state.Status = "COMPLETED"
				}
			}
		} else {
			inv := model.Invocation{Stage: stage, ExecutionID: req.ExecutionID, BatchID: req.BatchID, Generation: cp.Generation, Epoch: cp.Epoch, Owner: req.Owner, IdempotencyKey: operationID(req.ExecutionID, stage, ""), Metadata: map[string]string{"artifact_digest": req.ArtifactDigest}}
			result, attempts, callErr := invokeRecorded(inv)
			cp.Attempts[stage] += attempts
			if callErr != nil {
				cp.Status = "RETRY_PENDING"
				cp.LastError = callErr.Error()
				cp.UpdatedAt = simclient.Now()
				_ = store.SaveCheckpoint(cp)
				return cp, callErr
			}
			if !result.OK && !result.Duplicate {
				cp.Status = "FAILED"
				cp.LastError = result.Message
				cp.UpdatedAt = simclient.Now()
				_ = store.SaveCheckpoint(cp)
				return cp, errors.New(result.Message)
			}
		}
		cp.NextStage = stageIndex + 1
		cp.UpdatedAt = simclient.Now()
		cp.LastError = ""
		if err := store.SaveCheckpoint(cp); err != nil {
			return cp, err
		}
	}
	cp.Status = "SUCCEEDED"
	for _, it := range cp.Items {
		if it.Status == "DLQ" {
			cp.Status = "PARTIAL"
		}
	}
	cp.UpdatedAt = simclient.Now()
	return cp, store.SaveCheckpoint(cp)
}

func invokeRecorded(inv model.Invocation) (model.InvocationResult, int, error) {
	op := inv.IdempotencyKey
	_ = store.AppendJournal(model.JournalRecord{OperationID: op, ExecutionID: inv.ExecutionID, Stage: inv.Stage, ItemID: inv.ItemID, Generation: inv.Generation, Epoch: inv.Epoch, Status: "STARTED", At: simclient.Now()})
	result, attempts, err := fanout.Invoke(inv)
	status := "FAILED"
	if err == nil && (result.OK || result.Duplicate) {
		status = "COMMITTED"
	}
	_ = store.AppendJournal(model.JournalRecord{OperationID: op, ExecutionID: inv.ExecutionID, Stage: inv.Stage, ItemID: inv.ItemID, Generation: inv.Generation, Epoch: inv.Epoch, Status: status, At: simclient.Now()})
	return result, attempts, err
}
func isItemStage(stage string) bool {
	switch stage {
	case "fetch_inputs", "validate_inputs", "transform_records", "precheck_ledger", "write_ledger":
		return true
	}
	return false
}
func operationID(exec, stage, item string) string {
	parts := []string{exec, stage}
	if item != "" {
		parts = append(parts, item)
	}
	return strings.Join(parts, "/")
}
func copyMap(in map[string]string) map[string]string {
	out := map[string]string{}
	for k, v := range in {
		out[k] = v
	}
	return out
}

func LoadRequest(path string) (model.Request, error) {
	var r model.Request
	b, err := os.ReadFile(path)
	if err != nil {
		return r, err
	}
	if err := jsonUnmarshal(b, &r); err != nil {
		return r, err
	}
	return r, nil
}

var jsonUnmarshal = func(data []byte, v any) error { return json.Unmarshal(data, v) }
