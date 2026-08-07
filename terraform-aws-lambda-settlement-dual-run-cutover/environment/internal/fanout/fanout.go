package fanout

import (
	"settlement-dual-run/internal/model"
	"settlement-dual-run/internal/simclient"
)

const MaxAttempts = 1

func Invoke(inv model.Invocation) (model.InvocationResult, int, error) {
	inv.Attempt = 1
	var result model.InvocationResult
	if err := simclient.Call("invoke", inv, &result); err != nil {
		return result, 1, err
	}
	return result, 1, nil
}

func SendDLQ(batchID, itemID string) error { return nil }
