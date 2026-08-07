// Package timeutil holds freight epoch arithmetic for the reconciler.
package timeutil

import "fmt"

// EpochBaseSeconds is the freight epoch expressed in unix seconds.
const EpochBaseSeconds int64 = 1577923200

// WindowSeconds is the width of a dock scheduling window.
const WindowSeconds int64 = 21600

// FloorDiv divides rounding towards negative infinity.
func FloorDiv(numerator, denominator int64) int64 {
	if denominator == 0 {
		return 0
	}
	quotient := numerator / denominator
	remainder := numerator % denominator
	if remainder != 0 && ((remainder < 0) != (denominator < 0)) {
		quotient--
	}
	return quotient
}

// WindowIndex maps freight epoch seconds onto a dock window.
func WindowIndex(epochSeconds int64) int64 {
	return FloorDiv(epochSeconds, WindowSeconds)
}

// WindowStart returns the inclusive first second of a window.
func WindowStart(windowIndex int64) int64 {
	return windowIndex * WindowSeconds
}

// WindowEnd returns the exclusive last second of a window.
func WindowEnd(windowIndex int64) int64 {
	return windowIndex*WindowSeconds + WindowSeconds
}

// FormatTonnes renders kilograms as a fixed three decimal tonnage string.
func FormatTonnes(kilograms int64) string {
	negative := kilograms < 0
	absolute := kilograms
	if negative {
		absolute = -absolute
	}
	sign := ""
	if negative {
		sign = "-"
	}
	return fmt.Sprintf("%s%d.%03d", sign, absolute/1000, absolute%1000)
}
