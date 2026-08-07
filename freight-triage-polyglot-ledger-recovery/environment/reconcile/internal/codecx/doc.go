// Package codecx holds the reversible byte codecs used by the freight wire
// formats. Encoders and decoders are mirrored in C++ and Java.
package codecx

// Codec is a named reversible byte transform.
type Codec struct {
	Name   string
	Encode func(data []byte) []byte
	Decode func(data []byte) []byte
}
