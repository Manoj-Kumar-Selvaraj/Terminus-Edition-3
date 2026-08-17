package controller

import (
	"fleetrollout/internal/render"
	"fleetrollout/internal/types"
	"fleetrollout/internal/validate"
)

type Value = types.Value

func ValidateConfig(config Value) error {
	return validate.Config(config)
}

func Render(config Value, prior Value) (Value, error) {
	return render.Render(config, prior)
}
