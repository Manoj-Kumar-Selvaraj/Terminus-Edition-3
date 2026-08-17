package observe

import (
	"bufio"
	"fmt"
	"os"
	"regexp"
	"strings"
)

type TextMatch struct {
	Exists      bool
	ExactCount  int
	RegexpCount int
	BlockFound  bool
}

func InspectLine(path, line, expression string) (TextMatch, error) {
	f, err := os.Open(path)
	if os.IsNotExist(err) {
		return TextMatch{}, nil
	}
	if err != nil {
		return TextMatch{}, fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()
	match := TextMatch{Exists: true}
	var re *regexp.Regexp
	if strings.TrimSpace(expression) != "" {
		compiled, err := regexp.Compile(expression)
		if err != nil {
			return match, fmt.Errorf("compile regexp: %w", err)
		}
		re = compiled
	}
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		text := scanner.Text()
		if text == line {
			match.ExactCount++
		}
		if re != nil && re.MatchString(text) {
			match.RegexpCount++
		}
	}
	if err := scanner.Err(); err != nil {
		return match, fmt.Errorf("scan %s: %w", path, err)
	}
	return match, nil
}

func InspectBlock(path, block, marker string) (TextMatch, error) {
	payload, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return TextMatch{}, nil
	}
	if err != nil {
		return TextMatch{}, fmt.Errorf("read %s: %w", path, err)
	}
	text := string(payload)
	match := TextMatch{Exists: true}
	if strings.TrimSpace(block) != "" && strings.Contains(text, block) {
		match.BlockFound = true
	}
	if strings.TrimSpace(marker) != "" && strings.Contains(text, strings.ReplaceAll(marker, "{mark}", "BEGIN")) {
		match.BlockFound = match.BlockFound && true
	}
	return match, nil
}
