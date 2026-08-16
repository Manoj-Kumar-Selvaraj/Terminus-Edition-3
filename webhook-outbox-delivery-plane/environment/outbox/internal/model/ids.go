package model

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"sync/atomic"
	"time"
)

var seq uint64

func NewID(prefix string) string {
	n := atomic.AddUint64(&seq, 1)
	var b [8]byte
	_, _ = rand.Read(b[:])
	return fmt.Sprintf("%s%x%016x%s", prefix, time.Now().UnixNano()&0xffffffff, n, hex.EncodeToString(b[:4]))
}

func NewTenantID() string  { return NewID("ten_") }
func NewEndpointID() string { return NewID("ep_") }
func NewEventID() string   { return NewID("evt_") }
func NewAttemptID() string { return NewID("att_") }
func NewAuditID() string   { return NewID("aud_") }
