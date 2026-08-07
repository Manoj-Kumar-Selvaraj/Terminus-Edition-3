package iac

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"settlement-dual-run/internal/model"
)

const moduleSource = "hashicorp/aws"
const moduleVersion = "lambda-native"

type stageContract struct {
	TimeoutSeconds      int
	MemoryMB            int
	ReservedConcurrency int
	Permissions         []string
}

var expectedStageContracts = map[string]stageContract{
	"intake":            {30, 256, 4, []string{"logs:PutLogEvents", "xray:PutTraceSegments"}},
	"verify_manifest":   {45, 256, 4, []string{"s3:GetObject", "kms:Verify", "logs:PutLogEvents"}},
	"acquire_lock":      {20, 128, 8, []string{"dynamodb:PutItem", "dynamodb:GetItem", "logs:PutLogEvents"}},
	"fetch_inputs":      {120, 512, 12, []string{"s3:GetObject", "logs:PutLogEvents"}},
	"validate_inputs":   {90, 512, 12, []string{"s3:GetObject", "logs:PutLogEvents"}},
	"transform_records": {180, 1024, 8, []string{"s3:GetObject", "s3:PutObject", "logs:PutLogEvents"}},
	"precheck_ledger":   {60, 256, 6, []string{"dynamodb:GetItem", "logs:PutLogEvents"}},
	"write_ledger":      {120, 512, 6, []string{"dynamodb:PutItem", "dynamodb:UpdateItem", "logs:PutLogEvents"}},
	"build_report":      {90, 512, 4, []string{"s3:PutObject", "logs:PutLogEvents"}},
	"notify_partner":    {30, 256, 4, []string{"events:PutEvents", "logs:PutLogEvents"}},
	"archive_batch":     {60, 256, 4, []string{"s3:GetObject", "s3:PutObject", "s3:DeleteObject", "logs:PutLogEvents"}},
	"release_lock":      {20, 128, 8, []string{"dynamodb:DeleteItem", "logs:PutLogEvents"}},
}

func samePermissionSet(actual, expected []string) bool {
	if len(actual) != len(expected) {
		return false
	}
	counts := map[string]int{}
	for _, permission := range expected {
		counts[permission]++
	}
	for _, permission := range actual {
		counts[permission]--
		if counts[permission] < 0 {
			return false
		}
	}
	for _, count := range counts {
		if count != 0 {
			return false
		}
	}
	return true
}

func Load(infraDir string) (model.Deployment, error) {
	var sf model.StageFile
	data, err := os.ReadFile(filepath.Join(infraDir, "stages.json"))
	if err != nil {
		return model.Deployment{}, err
	}
	if err := json.Unmarshal(data, &sf); err != nil {
		return model.Deployment{}, fmt.Errorf("decode stages: %w", err)
	}
	if len(sf.Stages) != len(model.RequiredStages) {
		return model.Deployment{}, fmt.Errorf("expected %d stages, got %d", len(model.RequiredStages), len(sf.Stages))
	}
	seen := map[string]bool{}
	functionNames := map[string]bool{}
	packageHashes := map[string]bool{}
	for i, stage := range sf.Stages {
		if stage.Name != model.RequiredStages[i] {
			return model.Deployment{}, fmt.Errorf("stage %d = %q, want %q", i, stage.Name, model.RequiredStages[i])
		}
		if seen[stage.Name] {
			return model.Deployment{}, fmt.Errorf("duplicate stage %q", stage.Name)
		}
		seen[stage.Name] = true
		if stage.FunctionName != "settlement-pipeline-"+stage.Name {
			return model.Deployment{}, fmt.Errorf("stage %s function name mismatch", stage.Name)
		}
		if functionNames[stage.FunctionName] {
			return model.Deployment{}, fmt.Errorf("shared function identity %q", stage.FunctionName)
		}
		functionNames[stage.FunctionName] = true
		contract, ok := expectedStageContracts[stage.Name]
		if !ok {
			return model.Deployment{}, fmt.Errorf("stage %s has no documented contract", stage.Name)
		}
		if stage.TimeoutSeconds != contract.TimeoutSeconds ||
			stage.MemoryMB != contract.MemoryMB ||
			stage.ReservedConcurrency != contract.ReservedConcurrency {
			return model.Deployment{}, fmt.Errorf("stage %s resource contract mismatch", stage.Name)
		}
		if !samePermissionSet(stage.Permissions, contract.Permissions) {
			return model.Deployment{}, fmt.Errorf("stage %s permission contract mismatch", stage.Name)
		}
		if stage.Alias != "live" {
			return model.Deployment{}, fmt.Errorf("stage %s must use live alias", stage.Name)
		}
		if len(stage.PackageHash) < 16 {
			return model.Deployment{}, fmt.Errorf("stage %s package hash missing", stage.Name)
		}
		if packageHashes[stage.PackageHash] {
			return model.Deployment{}, fmt.Errorf("shared package hash %q", stage.PackageHash)
		}
		packageHashes[stage.PackageHash] = true
		for _, p := range stage.Permissions {
			if p == "*" || strings.HasSuffix(p, ":*") {
				return model.Deployment{}, fmt.Errorf("stage %s has wildcard permission", stage.Name)
			}
		}
	}
	mainTF, err := os.ReadFile(filepath.Join(infraDir, "main.tf"))
	if err != nil {
		return model.Deployment{}, err
	}
	tf := strings.Join(strings.Fields(string(mainTF)), " ")
	required := []string{
		`resource "aws_lambda_function"`,
		`resource "aws_lambda_alias"`,
		`for_each = local.stages`,
		`runtime = "provided.al2023"`,
		`handler = "bootstrap"`,
		`publish = true`,
		`source_code_hash = each.value.package_hash`,
		`function_name = each.value.function_name`,
		`name             = "live"`,
		`principal  = "states.amazonaws.com"`,
	}
	for _, token := range required {
		token = strings.Join(strings.Fields(token), " ")
		if !strings.Contains(tf, token) {
			return model.Deployment{}, fmt.Errorf("Terraform lambda contract missing %s", token)
		}
	}
	if strings.Contains(tf, `principal = "*"`) || strings.Contains(tf, `principal  = "*"`) {
		return model.Deployment{}, fmt.Errorf("wildcard invoke principal is forbidden")
	}
	var deploy struct {
		Generation int    `json:"generation"`
		Alias      string `json:"alias"`
	}
	b, err := os.ReadFile(filepath.Join(infraDir, "deployment.json"))
	if err != nil {
		return model.Deployment{}, err
	}
	if err := json.Unmarshal(b, &deploy); err != nil {
		return model.Deployment{}, err
	}
	if deploy.Generation < 1 || deploy.Alias != "live" {
		return model.Deployment{}, fmt.Errorf("invalid deployment generation")
	}
	canonical, _ := json.Marshal(sf.Stages)
	h := sha256.Sum256(append(canonical, mainTF...))
	return model.Deployment{
		Generation: deploy.Generation,
		Alias:      deploy.Alias,
		Module:     moduleSource,
		Version:    moduleVersion,
		Digest:     hex.EncodeToString(h[:]),
		Stages:     sf.Stages,
	}, nil
}

func StableStageNames(d model.Deployment) []string {
	out := make([]string, 0, len(d.Stages))
	for _, s := range d.Stages {
		out = append(out, s.Name)
	}
	return out
}

func SortedStageNames(d model.Deployment) []string {
	out := StableStageNames(d)
	sort.Strings(out)
	return out
}
