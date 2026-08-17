package observe

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"os/user"
	"path/filepath"
	"strconv"
	"syscall"
)

type PathState struct {
	Path       string
	Exists     bool
	Kind       string
	Mode       string
	UID        int
	GID        int
	Owner      string
	Group      string
	Size       int64
	Digest     string
	LinkTarget string
}

func InspectPath(path string, withDigest bool) (PathState, error) {
	state := PathState{Path: path}
	info, err := os.Lstat(path)
	if os.IsNotExist(err) {
		return state, nil
	}
	if err != nil {
		return state, fmt.Errorf("lstat %s: %w", path, err)
	}
	state.Exists = true
	state.Mode = fmt.Sprintf("%04o", info.Mode().Perm())
	state.Size = info.Size()
	state.Kind = classify(info.Mode())
	if stat, ok := info.Sys().(*syscall.Stat_t); ok {
		state.UID = int(stat.Uid)
		state.GID = int(stat.Gid)
		state.Owner = username(stat.Uid)
		state.Group = groupname(stat.Gid)
	}
	if info.Mode()&os.ModeSymlink != 0 {
		target, err := os.Readlink(path)
		if err != nil {
			return state, fmt.Errorf("readlink %s: %w", path, err)
		}
		state.LinkTarget = target
	}
	if withDigest && info.Mode().IsRegular() {
		digest, err := digestFile(path)
		if err != nil {
			return state, err
		}
		state.Digest = digest
	}
	return state, nil
}

func classify(mode os.FileMode) string {
	switch {
	case mode.IsRegular():
		return "file"
	case mode.IsDir():
		return "directory"
	case mode&os.ModeSymlink != 0:
		return "symlink"
	case mode&os.ModeNamedPipe != 0:
		return "fifo"
	case mode&os.ModeSocket != 0:
		return "socket"
	case mode&os.ModeDevice != 0:
		return "device"
	default:
		return "other"
	}
}

func digestFile(path string) (string, error) {
	f, err := os.Open(filepath.Clean(path))
	if err != nil {
		return "", fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()
	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", fmt.Errorf("hash %s: %w", path, err)
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

func username(uid uint32) string {
	u, err := user.LookupId(strconv.FormatUint(uint64(uid), 10))
	if err != nil {
		return strconv.FormatUint(uint64(uid), 10)
	}
	return u.Username
}

func groupname(gid uint32) string {
	g, err := user.LookupGroupId(strconv.FormatUint(uint64(gid), 10))
	if err != nil {
		return strconv.FormatUint(uint64(gid), 10)
	}
	return g.Name
}
