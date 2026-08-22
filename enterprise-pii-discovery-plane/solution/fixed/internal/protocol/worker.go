package protocol

import (
	"bufio"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"sort"
	"time"

	"enterprise-pii/internal/model"
)

const Version = "1"

type Envelope struct {
	Type            string          `json:"type"`
	ProtocolVersion string          `json:"protocol_version"`
	RequestID       string          `json:"request_id"`
	Body            json.RawMessage `json:"body"`
}

type Hello struct {
	WorkerID       string   `json:"worker_id"`
	SessionID      string   `json:"session_id"`
	DetectorBundle string   `json:"detector_bundle"`
	Formats        []string `json:"formats"`
}

type Heartbeat struct {
	WorkerID     string `json:"worker_id"`
	SessionID    string `json:"session_id"`
	LeaseToken   string `json:"lease_token,omitempty"`
	JobID        string `json:"job_id,omitempty"`
	ShardID      string `json:"shard_id,omitempty"`
	Generation   uint64 `json:"generation,omitempty"`
	Attempt      uint32 `json:"attempt,omitempty"`
	PolicyDigest string `json:"policy_digest,omitempty"`
	Records      int64  `json:"records"`
	Bytes        int64  `json:"bytes"`
}

type Acknowledgement struct {
	RequestID  string `json:"request_id"`
	Status     string `json:"status"`
	BatchID    string `json:"batch_id,omitempty"`
	BodyDigest string `json:"body_digest,omitempty"`
	Message    string `json:"message,omitempty"`
}

type Codec struct {
	maximumFrameBytes int
}

func NewCodec(maximumFrameBytes int) *Codec {
	if maximumFrameBytes <= 0 {
		maximumFrameBytes = 4 << 20
	}
	return &Codec{maximumFrameBytes: maximumFrameBytes}
}

func (c *Codec) Read(reader io.Reader) (Envelope, error) {
	buffered := bufio.NewReaderSize(reader, 64*1024)
	line, err := buffered.ReadBytes('\n')
	if err != nil && !errors.Is(err, io.EOF) {
		return Envelope{}, err
	}
	if len(line) == 0 {
		return Envelope{}, io.EOF
	}
	if len(line) > c.maximumFrameBytes {
		return Envelope{}, errors.New("worker frame exceeds byte budget")
	}
	var envelope Envelope
	decoder := json.NewDecoder(bytesReader(line))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&envelope); err != nil {
		return Envelope{}, errors.New("invalid worker frame")
	}
	if envelope.ProtocolVersion != Version {
		return Envelope{}, errors.New("unsupported protocol version")
	}
	if envelope.Type == "" || envelope.RequestID == "" {
		return Envelope{}, errors.New("worker frame identity missing")
	}
	return envelope, nil
}

func DecodeBody[T any](envelope Envelope) (T, error) {
	var value T
	decoder := json.NewDecoder(bytesReader(envelope.Body))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&value); err != nil {
		return value, err
	}
	return value, nil
}

func Encode(writer io.Writer, message any) error {
	encoder := json.NewEncoder(writer)
	encoder.SetEscapeHTML(false)
	return encoder.Encode(message)
}

func CanonicalBatchDigest(batch model.ResultBatch) (string, error) {
	findings := append([]model.Finding(nil), batch.Findings...)
	sort.Slice(findings, func(i, j int) bool {
		left, right := findings[i], findings[j]
		if left.Location.SourceID != right.Location.SourceID {
			return left.Location.SourceID < right.Location.SourceID
		}
		if left.Location.CanonicalPath != right.Location.CanonicalPath {
			return left.Location.CanonicalPath < right.Location.CanonicalPath
		}
		if left.Location.ArchiveMember != right.Location.ArchiveMember {
			return left.Location.ArchiveMember < right.Location.ArchiveMember
		}
		if left.Location.RecordID != right.Location.RecordID {
			return left.Location.RecordID < right.Location.RecordID
		}
		if left.Location.FieldPath != right.Location.FieldPath {
			return left.Location.FieldPath < right.Location.FieldPath
		}
		if left.Location.ByteStart != right.Location.ByteStart {
			return left.Location.ByteStart < right.Location.ByteStart
		}
		if left.Category != right.Category {
			return left.Category < right.Category
		}
		if left.Fingerprint != right.Fingerprint {
			return left.Fingerprint < right.Fingerprint
		}
		return left.DetectorRevision < right.DetectorRevision
	})
	body, err := json.Marshal(struct {
		Errors         []model.ScanError  `json:"errors"`
		Findings       []model.Finding    `json:"findings"`
		NextCheckpoint string             `json:"next_checkpoint"`
		Sequence       uint64             `json:"sequence"`
		Truncations    []model.Truncation `json:"truncations"`
	}{
		Errors:         batch.Errors,
		Findings:       findings,
		NextCheckpoint: batch.NextCheckpoint,
		Sequence:       batch.Sequence,
		Truncations:    batch.Truncations,
	})
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(body)
	return hex.EncodeToString(sum[:]), nil
}

func LeaseEnvelope(requestID string, lease model.Lease, source model.Source) Envelope {
	body, _ := json.Marshal(map[string]any{
		"lease":       lease,
		"source_id":   source.ID,
		"source_root": source.CanonicalRoot,
		"department":  source.Department,
		"region":      source.Region,
		"issued_at":   time.Now().UTC(),
	})
	return Envelope{Type: "lease", ProtocolVersion: Version, RequestID: requestID, Body: body}
}

type byteReader struct {
	body   []byte
	offset int
}

func bytesReader(body []byte) *byteReader { return &byteReader{body: body} }

func (r *byteReader) Read(target []byte) (int, error) {
	if r.offset >= len(r.body) {
		return 0, io.EOF
	}
	count := copy(target, r.body[r.offset:])
	r.offset += count
	return count, nil
}
