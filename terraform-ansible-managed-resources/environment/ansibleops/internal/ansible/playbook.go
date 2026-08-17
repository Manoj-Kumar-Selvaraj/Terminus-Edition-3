package ansible

import (
	"fmt"
	"strings"
)

type Playbook struct {
	Name   string
	Hosts  string
	Gather bool
	Tasks  []Task
}

func SingleTask(task Task) Playbook {
	return Playbook{
		Name:   "ansibleops managed resource mutation",
		Hosts:  "managed",
		Gather: false,
		Tasks:  []Task{task},
	}
}

func (p Playbook) Render() ([]byte, error) {
	if strings.TrimSpace(p.Name) == "" {
		return nil, fmt.Errorf("playbook name is required")
	}
	if strings.TrimSpace(p.Hosts) == "" {
		return nil, fmt.Errorf("playbook hosts are required")
	}
	if len(p.Tasks) == 0 {
		return nil, fmt.Errorf("playbook requires at least one task")
	}

	var b strings.Builder
	b.WriteString("---\n")
	b.WriteString("- name: ")
	b.WriteString(quote(p.Name))
	b.WriteByte('\n')
	b.WriteString("  hosts: ")
	b.WriteString(quote(p.Hosts))
	b.WriteByte('\n')
	if p.Gather {
		b.WriteString("  gather_facts: true\n")
	} else {
		b.WriteString("  gather_facts: false\n")
	}
	b.WriteString("  tasks:\n")
	for _, task := range p.Tasks {
		rendered, err := task.Render(4)
		if err != nil {
			return nil, err
		}
		b.WriteString(rendered)
	}
	return []byte(b.String()), nil
}
