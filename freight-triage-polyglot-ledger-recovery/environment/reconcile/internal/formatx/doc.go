// Package formatx holds the display formatters used on dock sheets and audit
// exports. Each formatter is mirrored in C++ and Java.
package formatx

// Formatter is a named integer to text rendering.
type Formatter struct {
	Name  string
	Apply func(value int64) string
}
