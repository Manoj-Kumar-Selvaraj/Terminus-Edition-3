// Package hashx holds the checksum family shared with the native engine and
// the Java intake service. Every algorithm must agree byte for byte.
package hashx

// Algorithm is a named checksum over raw bytes.
type Algorithm struct {
	Name  string
	Apply func(data []byte) uint64
}
