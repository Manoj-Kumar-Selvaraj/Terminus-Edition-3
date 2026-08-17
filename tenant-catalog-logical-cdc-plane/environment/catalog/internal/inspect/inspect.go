package inspect

import (
	"catalog/internal/health"
	"catalog/internal/recover"
	"catalog/internal/store"
)

// Inspect is the starter implementation: recover as a side effect.
func Inspect(st *store.Store) error {
	if err := recover.Recover(st); err != nil {
		return err
	}
	return health.Write(st)
}

func EmptyCheck(st *store.Store) error {
	return Inspect(st)
}
