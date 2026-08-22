package protocol

import (
	"bufio"
	"encoding/binary"
	"encoding/json"
	"errors"
	"io"
	"sync"

	"sovereign-lb/internal/model"
)

var ErrFrameTooLarge = errors.New("control frame exceeds configured limit")

type Stream struct { reader *bufio.Reader; writer io.Writer; maximum uint32; mutex sync.Mutex }
func New(reader io.Reader, writer io.Writer, maximum uint32) *Stream { return &Stream{reader: bufio.NewReader(reader), writer: writer, maximum: maximum} }

func (stream *Stream) Read() (model.Envelope, error) {
	var prefix [4]byte
	if _, err := io.ReadFull(stream.reader, prefix[:]); err != nil { return model.Envelope{}, err }
	length := binary.BigEndian.Uint32(prefix[:])
	if length == 0 || length > stream.maximum { return model.Envelope{}, ErrFrameTooLarge }
	body := make([]byte, length)
	if _, err := io.ReadFull(stream.reader, body); err != nil { return model.Envelope{}, err }
	var envelope model.Envelope
	if err := json.Unmarshal(body, &envelope); err != nil { return model.Envelope{}, err }
	if err := ValidateEnvelope(envelope); err != nil { return model.Envelope{}, err }
	return envelope, nil
}

func (stream *Stream) Write(envelope model.Envelope) error {
	if err := ValidateEnvelope(envelope); err != nil { return err }
	body, err := json.Marshal(envelope); if err != nil { return err }
	if len(body) == 0 || len(body) > int(stream.maximum) { return ErrFrameTooLarge }
	stream.mutex.Lock(); defer stream.mutex.Unlock()
	var prefix [4]byte; binary.BigEndian.PutUint32(prefix[:], uint32(len(body)))
	if err := writeAll(stream.writer, prefix[:]); err != nil { return err }
	return writeAll(stream.writer, body)
}

func ValidateEnvelope(value model.Envelope) error {
	allowed := map[string]bool{"hello":true,"prepare":true,"prepared":true,"rejected":true,"activate":true,"active":true,"status":true}
	if !allowed[value.Type] { return errors.New("unknown message type") }
	if value.NodeID == "" || value.SessionID == "" || value.Sequence == 0 || value.SentAt == "" || value.Body == nil { return errors.New("incomplete message envelope") }
	if value.Type != "hello" && value.Type != "status" && (value.Generation == 0 || len(value.Digest) != 64) { return errors.New("generation envelope is incomplete") }
	return nil
}

func writeAll(writer io.Writer, data []byte) error { for len(data) > 0 { written, err := writer.Write(data); if err != nil { return err }; if written == 0 { return io.ErrShortWrite }; data = data[written:] }; return nil }