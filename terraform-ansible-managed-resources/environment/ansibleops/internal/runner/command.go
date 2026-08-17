package runner

import (
	"fmt"
	"strings"
)

type CommandPreview struct {
	Binary    string
	Inventory string
	Playbook  string
}

func (p CommandPreview) Argv() []string {
	return []string{p.Binary, "-i", p.Inventory, p.Playbook}
}

func (p CommandPreview) String() string {
	return strings.Join(p.Argv(), " ")
}

func ValidateBinary(binary string) error {
	if strings.TrimSpace(binary) == "" {
		return fmt.Errorf("empty ansible binary")
	}
	if strings.ContainsRune(binary, '\x00') {
		return fmt.Errorf("ansible binary contains NUL")
	}
	return nil
}
