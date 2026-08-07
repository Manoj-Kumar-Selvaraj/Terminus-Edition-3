// Package normx holds the ASCII normalizers applied to freight references.
package normx

// Normalizer is a named string normalization.
type Normalizer struct {
	Name  string
	Apply func(text string) string
}
