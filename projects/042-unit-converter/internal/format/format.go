// Package format renders floating-point results for humans.
//
// Converting units produces values like 0.30480000000000004 (because 0.3048
// has no exact binary representation). Printing raw float64s is ugly, so we
// round to a fixed number of significant digits and strip trailing zeros.
package format

import (
	"math"
	"strconv"
	"strings"
)

// Number formats v with at most sig significant digits. Values with very
// large or very small magnitude switch to scientific notation.
func Number(v float64, sig int) string {
	if sig < 1 {
		sig = 1
	}
	switch {
	case math.IsNaN(v):
		return "NaN"
	case math.IsInf(v, 1):
		return "+Inf"
	case math.IsInf(v, -1):
		return "-Inf"
	case v == 0:
		return "0"
	}

	// Round to sig significant digits first; 'e' formatting does this exactly.
	rounded, _ := strconv.ParseFloat(strconv.FormatFloat(v, 'e', sig-1, 64), 64)
	if rounded == 0 { // e.g. -0 after rounding
		return "0"
	}
	abs := math.Abs(rounded)
	if abs >= 1e15 || abs < 1e-6 {
		return trimExp(strconv.FormatFloat(rounded, 'e', sig-1, 64))
	}
	// Fixed notation: decimals needed = sig - (digits before the point).
	intDigits := int(math.Floor(math.Log10(abs))) + 1
	decimals := sig - intDigits
	if decimals < 0 {
		decimals = 0
	}
	return trimZeros(strconv.FormatFloat(rounded, 'f', decimals, 64))
}

// Grouped is like Number but inserts thousands separators into the integer
// part, e.g. 1234567.5 -> "1,234,567.5".
func Grouped(v float64, sig int) string {
	s := Number(v, sig)
	if strings.ContainsAny(s, "eIN") {
		return s
	}
	sign := ""
	if strings.HasPrefix(s, "-") {
		sign, s = "-", s[1:]
	}
	intPart, frac := s, ""
	if i := strings.IndexByte(s, '.'); i >= 0 {
		intPart, frac = s[:i], s[i:]
	}
	var b strings.Builder
	for i, c := range intPart {
		if i > 0 && (len(intPart)-i)%3 == 0 {
			b.WriteByte(',')
		}
		b.WriteRune(c)
	}
	return sign + b.String() + frac
}

func trimZeros(s string) string {
	if !strings.Contains(s, ".") {
		return s
	}
	s = strings.TrimRight(s, "0")
	return strings.TrimSuffix(s, ".")
}

// trimExp turns "1.500000e+20" into "1.5e+20".
func trimExp(s string) string {
	i := strings.IndexByte(s, 'e')
	if i < 0 {
		return s
	}
	return trimZeros(s[:i]) + s[i:]
}
