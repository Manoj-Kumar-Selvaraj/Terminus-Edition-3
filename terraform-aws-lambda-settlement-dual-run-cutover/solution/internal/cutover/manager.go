package cutover

import (
	"errors"
	"os"

	"settlement-dual-run/internal/model"
	"settlement-dual-run/internal/simclient"
	"settlement-dual-run/internal/store"
)

type controlResponse struct {
	OK         bool   `json:"ok"`
	Generation int    `json:"generation"`
	Writer     string `json:"writer"`
	Epoch      int64  `json:"epoch"`
	Class      string `json:"class"`
	Message    string `json:"message"`
}

func Ensure(generation int) (model.CutoverState, error) {
	c, err := store.LoadCutover()
	if err == nil {
		return c, nil
	}
	if !errors.Is(err, os.ErrNotExist) {
		return model.CutoverState{}, err
	}
	var response controlResponse
	if err := simclient.Call("control", map[string]any{"generation": generation, "writer": "lambda", "epoch": 1}, &response); err != nil {
		return model.CutoverState{}, err
	}
	if !response.OK {
		return model.CutoverState{}, errors.New(response.Message)
	}
	c = model.CutoverState{ActiveGeneration: generation, Writer: "lambda", Epoch: response.Epoch}
	return c, store.SaveCutover(c)
}

func Load() (model.CutoverState, error) { return store.LoadCutover() }

func Shift(generation int, writer string) (model.CutoverState, error) {
	current, err := store.LoadCutover()
	if err != nil {
		return model.CutoverState{}, err
	}
	var response controlResponse
	if err := simclient.Call("control", map[string]any{"generation": generation, "writer": writer, "epoch": current.Epoch + 1}, &response); err != nil {
		return model.CutoverState{}, err
	}
	if !response.OK {
		var state struct {
			ActiveGeneration int    `json:"active_generation"`
			Writer           string `json:"writer"`
			Epoch            int64  `json:"epoch"`
		}
		if err := simclient.CallArgs([]string{"inspect", "state"}, nil, &state); err != nil {
			return model.CutoverState{}, errors.New(response.Message)
		}
		if state.ActiveGeneration != generation {
			return model.CutoverState{}, errors.New(response.Message)
		}
		response.Generation, response.Writer, response.Epoch = state.ActiveGeneration, state.Writer, state.Epoch
	}
	next := model.CutoverState{ActiveGeneration: response.Generation, PreviousGeneration: current.ActiveGeneration, Writer: response.Writer, Epoch: response.Epoch}
	return next, store.SaveCutover(next)
}
