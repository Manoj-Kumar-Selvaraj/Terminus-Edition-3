package inspect

import (
	"catalog/internal/health"
	"catalog/internal/store"
)

func Inspect(st *store.Store) error {
	return health.Write(st)
}

func EmptyCheck(st *store.Store) error {
	return health.Write(st)
}
