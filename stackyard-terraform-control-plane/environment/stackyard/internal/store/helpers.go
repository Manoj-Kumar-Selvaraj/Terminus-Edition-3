package store

import (
	"context"
	"database/sql"
	"errors"
	"path/filepath"
)

// WorkspacePath returns the on-disk root for a workspace under dataDir.
func WorkspacePath(dataDir, workspaceID, workingDirectory string) string {
	return filepath.Join(dataDir, workspaceID, workingDirectory)
}

// HasActiveRun reports whether a non-terminal run exists for the workspace.
func (s *Store) HasActiveRun(ctx context.Context, workspaceID string) (bool, error) {
	n, err := s.CountNonTerminalRuns(ctx, workspaceID)
	if err != nil {
		return false, err
	}
	return n > 0, nil
}

// IsLocked reports whether a lock row exists for the workspace.
func (s *Store) IsLocked(ctx context.Context, workspaceID string) (bool, error) {
	_, err := s.GetLock(ctx, workspaceID)
	if err == nil {
		return true, nil
	}
	if errors.Is(err, sql.ErrNoRows) {
		return false, nil
	}
	return false, err
}
