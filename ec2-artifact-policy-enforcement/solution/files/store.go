package core

import (
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "os"
    "path/filepath"
    "time"
)

func CacheKey(req Request, policy Policy) string {
    sum := sha256.Sum256([]byte(req.Digest + "|" + policy.Version + "|" + policy.ScannerDBRevision))
    return hex.EncodeToString(sum[:])
}

func LoadCache(stateDir, key string, now time.Time) (CacheEntry, bool, error) {
    var entry CacheEntry
    data, err := os.ReadFile(filepath.Join(stateDir, "cache", key+".json"))
    if os.IsNotExist(err) { return entry, false, nil }
    if err != nil { return entry, false, err }
    if err := json.Unmarshal(data, &entry); err != nil { return entry, false, err }
    expires, err := parseRFC3339(entry.ExpiresAt)
    if err != nil || !now.Before(expires) { return CacheEntry{}, false, nil }
    return entry, true, nil
}

func SaveCache(stateDir, key string, entry CacheEntry) error {
    dir := filepath.Join(stateDir, "cache")
    if err := os.MkdirAll(dir, 0755); err != nil { return err }
    data, err := json.Marshal(entry)
    if err != nil { return err }
    tmp := filepath.Join(dir, key+".tmp")
    final := filepath.Join(dir, key+".json")
    if err := os.WriteFile(tmp, data, 0644); err != nil { return err }
    return os.Rename(tmp, final)
}

func AppendAudit(stateDir string, decision Decision) error {
    if err := os.MkdirAll(stateDir, 0755); err != nil { return err }
    file, err := os.OpenFile(filepath.Join(stateDir, "audit.jsonl"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
    if err != nil { return err }
    defer file.Close()
    data, err := json.Marshal(decision)
    if err != nil { return err }
    if _, err := file.Write(append(data, '\n')); err != nil { return err }
    return file.Sync()
}

func WriteLastDecision(stateDir string, decision Decision) error {
    if err := os.MkdirAll(stateDir, 0755); err != nil { return err }
    data, err := json.MarshalIndent(decision, "", "  ")
    if err != nil { return err }
    tmp := filepath.Join(stateDir, "last-decision.tmp")
    final := filepath.Join(stateDir, "last-decision.json")
    if err := os.WriteFile(tmp, data, 0644); err != nil { return err }
    return os.Rename(tmp, final)
}
