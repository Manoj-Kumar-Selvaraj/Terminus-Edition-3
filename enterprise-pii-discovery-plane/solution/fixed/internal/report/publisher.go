package report

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

type Publisher struct {
	Root string
}

func NewPublisher(root string) *Publisher {
	return &Publisher{Root: root}
}

func (p *Publisher) Publish(value Report) (Manifest, error) {
	if !value.Completeness.Complete {
		return Manifest{}, errors.New("cannot publish incomplete report")
	}
	jsonBody, err := JSON(value)
	if err != nil {
		return Manifest{}, err
	}
	csvBody, err := CSV(value)
	if err != nil {
		return Manifest{}, err
	}
	manifest, err := BuildManifest(value, jsonBody, csvBody)
	if err != nil {
		return Manifest{}, err
	}
	manifestBody, err := json.Marshal(manifest)
	if err != nil {
		return Manifest{}, err
	}
	jobRoot := filepath.Join(p.Root, safe(value.JobID))
	if err := os.MkdirAll(jobRoot, 0755); err != nil {
		return Manifest{}, err
	}
	name := fmt.Sprintf("%020d", value.Generation)
	temporary := filepath.Join(jobRoot, "."+name+".tmp")
	final := filepath.Join(jobRoot, name)
	if err := os.RemoveAll(temporary); err != nil {
		return Manifest{}, err
	}
	if err := os.Mkdir(temporary, 0755); err != nil {
		return Manifest{}, err
	}
	files := map[string][]byte{
		"report.json":   jsonBody,
		"report.csv":    csvBody,
		"manifest.json": manifestBody,
	}
	for fileName, body := range files {
		if err := os.WriteFile(filepath.Join(temporary, fileName), body, 0644); err != nil {
			return Manifest{}, err
		}
	}
	if err := p.VerifyPath(temporary); err != nil {
		return Manifest{}, err
	}
	if err := os.Rename(temporary, final); err != nil {
		return Manifest{}, err
	}
	pointerTemp := filepath.Join(jobRoot, "CURRENT.tmp")
	if err := os.WriteFile(pointerTemp, []byte(name+"\n"), 0644); err != nil {
		return Manifest{}, err
	}
	if err := os.Rename(pointerTemp, filepath.Join(jobRoot, "CURRENT")); err != nil {
		return Manifest{}, err
	}
	return manifest, nil
}

func (p *Publisher) Verify(jobID string, generation uint64) (Manifest, error) {
	path := filepath.Join(p.Root, safe(jobID), fmt.Sprintf("%020d", generation))
	return p.verify(path)
}

func (p *Publisher) VerifyPath(path string) error {
	_, err := p.verify(path)
	return err
}

func (p *Publisher) verify(path string) (Manifest, error) {
	body, err := os.ReadFile(filepath.Join(path, "manifest.json"))
	if err != nil {
		return Manifest{}, err
	}
	var manifest Manifest
	if err := json.Unmarshal(body, &manifest); err != nil {
		return Manifest{}, errors.New("invalid report manifest")
	}
	for _, file := range manifest.Files {
		content, err := os.ReadFile(filepath.Join(path, file.Name))
		if err != nil {
			return Manifest{}, err
		}
		if len(content) != file.Bytes || digest(content) != file.SHA256 {
			return Manifest{}, errors.New("report content digest mismatch")
		}
	}
	copy := manifest
	copy.Digest = ""
	canonical, err := json.Marshal(copy)
	if err != nil || digest(canonical) != manifest.Digest {
		return Manifest{}, errors.New("manifest digest mismatch")
	}
	return manifest, nil
}

func (p *Publisher) Recover(jobID string) (Manifest, error) {
	jobRoot := filepath.Join(p.Root, safe(jobID))
	if currentBody, err := os.ReadFile(filepath.Join(jobRoot, "CURRENT")); err == nil {
		name := strings.TrimSpace(string(currentBody))
		if number, parseErr := strconv.ParseUint(name, 10, 64); parseErr == nil {
			if manifest, verifyErr := p.Verify(jobID, number); verifyErr == nil {
				return manifest, nil
			}
		}
	}
	entries, err := os.ReadDir(jobRoot)
	if err != nil {
		return Manifest{}, err
	}
	var generations []uint64
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		number, err := strconv.ParseUint(entry.Name(), 10, 64)
		if err == nil {
			generations = append(generations, number)
		}
	}
	sortDescending(generations)
	for _, generation := range generations {
		manifest, err := p.Verify(jobID, generation)
		if err == nil {
			return manifest, nil
		}
	}
	return Manifest{}, errors.New("no valid report generation")
}

func sortDescending(values []uint64) {
	for left := 0; left < len(values); left++ {
		for right := left + 1; right < len(values); right++ {
			if values[right] > values[left] {
				values[left], values[right] = values[right], values[left]
			}
		}
	}
}

func safe(value string) string {
	if value == "" || strings.ContainsAny(value, `/\\`) || value == "." || value == ".." {
		panic("unsafe report identity")
	}
	return value
}
