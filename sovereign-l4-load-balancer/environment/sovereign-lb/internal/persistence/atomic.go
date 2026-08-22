package persistence

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
)

func WriteFile(path string, data []byte, mode os.FileMode) error {
	if err := os.MkdirAll(filepath.Dir(path), 0750); err != nil { return err }
	temporary, err := os.CreateTemp(filepath.Dir(path), ".pending-*")
	if err != nil { return err }
	temporaryName := temporary.Name()
	defer os.Remove(temporaryName)
	if err := temporary.Chmod(mode); err != nil { temporary.Close(); return err }
	if _, err := temporary.Write(data); err != nil { temporary.Close(); return err }
	if err := temporary.Sync(); err != nil { temporary.Close(); return err }
	if err := temporary.Close(); err != nil { return err }
	if err := os.Rename(temporaryName, path); err != nil { return err }
	directory, err := os.Open(filepath.Dir(path))
	if err != nil { return err }
	defer directory.Close()
	return directory.Sync()
}

func WriteJSON(path string, value any) error {
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil { return err }
	data = append(data, '\n')
	return WriteFile(path, data, 0640)
}

func ReadJSON(path string, value any) error {
	data, err := os.ReadFile(path)
	if err != nil { return err }
	if err := json.Unmarshal(data, value); err != nil { return fmt.Errorf("decode %s: %w", path, err) }
	return nil
}

func ReplaceDirectory(staging, destination string) error {
	if _, err := os.Stat(staging); err != nil { return err }
	backup := destination + ".previous"
	_ = os.RemoveAll(backup)
	if err := os.Rename(destination, backup); err != nil && !errors.Is(err, os.ErrNotExist) { return err }
	if err := os.Rename(staging, destination); err != nil { _ = os.Rename(backup, destination); return err }
	_ = os.RemoveAll(backup)
	directory, err := os.Open(filepath.Dir(destination))
	if err != nil { return err }
	defer directory.Close()
	return directory.Sync()
}