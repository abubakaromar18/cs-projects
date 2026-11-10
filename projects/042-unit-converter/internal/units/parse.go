package units

import (
	"errors"
	"fmt"
	"strconv"
	"strings"
	"unicode"
)

// Query is a parsed conversion request such as "12.5 km to mi".
type Query struct {
	Value float64
	From  Unit
	To    Unit // zero Unit if no target was given
}

// HasTarget reports whether the query named a target unit.
func (q Query) HasTarget() bool { return q.To.Symbol != "" }

// ErrSyntax is returned for input that cannot be parsed as a query.
var ErrSyntax = errors.New("syntax error")

// separators are the words accepted between source and target units.
var separators = map[string]bool{"to": true, "in": true, "into": true, "as": true, "->": true, "=>": true}

// ParseQuery parses free-form conversion requests. Accepted shapes:
//
//	"10 km to mi"     "10km in mi"     "10 km mi"
//	"-40 C -> F"      "1.5e3 MiB as GB" "3 nautical miles to km"
//	"98.6 F"          (no target: caller decides what to show)
//
// The word "in" is both a separator and the inch symbol, so "5 in in cm" is
// ambiguous to a naive splitter. We therefore tokenise and try every possible
// separator position, accepting the first split where both sides resolve to
// real units. This is a tiny example of parsing by search rather than by a
// fixed grammar.
func (r *Registry) ParseQuery(input string) (Query, error) {
	numStr, rest := splitNumber(strings.TrimSpace(input))
	if numStr == "" {
		return Query{}, fmt.Errorf("%w: expected a number at the start of %q", ErrSyntax, input)
	}
	v, err := strconv.ParseFloat(numStr, 64)
	if err != nil {
		return Query{}, fmt.Errorf("%w: invalid number %q", ErrSyntax, numStr)
	}
	toks := strings.Fields(rest)
	if len(toks) == 0 {
		return Query{}, fmt.Errorf("%w: missing unit after %q", ErrSyntax, numStr)
	}

	// 1. Whole remainder is a single (possibly multi-word) unit: "98.6 F".
	if u, err := r.Lookup(strings.Join(toks, " ")); err == nil {
		return Query{Value: v, From: u}, nil
	}

	// 2. Explicit separator somewhere in the middle.
	var firstErr error
	for k := 1; k < len(toks)-1; k++ {
		if !separators[strings.ToLower(toks[k])] {
			continue
		}
		q, err := r.tryPair(v, toks[:k], toks[k+1:])
		if err == nil {
			return q, nil
		}
		if firstErr == nil {
			firstErr = err
		}
	}

	// 3. No separator: "10 km mi". Try each split into two non-empty halves.
	for k := 1; k < len(toks); k++ {
		if q, err := r.tryPair(v, toks[:k], toks[k:]); err == nil {
			return q, nil
		}
	}

	if firstErr != nil {
		return Query{}, firstErr
	}
	// Re-run the single-unit lookup to surface the most useful error.
	_, err = r.Lookup(strings.Join(toks, " "))
	if len(toks) > 1 {
		_, err = r.Lookup(toks[0])
		if err == nil {
			_, err = r.Lookup(strings.Join(toks[1:], " "))
		}
	}
	return Query{}, err
}

func (r *Registry) tryPair(v float64, from, to []string) (Query, error) {
	f, err := r.Lookup(strings.Join(from, " "))
	if err != nil {
		return Query{}, err
	}
	t, err := r.Lookup(strings.Join(to, " "))
	if err != nil {
		return Query{}, err
	}
	if f.Category != t.Category {
		return Query{}, fmt.Errorf("%w: %s (%s) -> %s (%s)",
			ErrIncompatibleUnits, f.Symbol, f.Category, t.Symbol, t.Category)
	}
	return Query{Value: v, From: f, To: t}, nil
}

// splitNumber separates a leading floating-point literal from the rest of the
// string, so "10km" and "10 km" both work. It is a small hand-written scanner
// (sign, digits, optional fraction, optional exponent) rather than a regexp.
func splitNumber(s string) (num, rest string) {
	i := 0
	if i < len(s) && (s[i] == '+' || s[i] == '-') {
		i++
	}
	digits := 0
	for i < len(s) && isDigit(s[i]) {
		i++
		digits++
	}
	if i < len(s) && s[i] == '.' {
		i++
		for i < len(s) && isDigit(s[i]) {
			i++
			digits++
		}
	}
	if digits == 0 {
		return "", s
	}
	// Exponent: only consume if followed by digits, so "5e" stays a unit-ish suffix.
	if i < len(s) && (s[i] == 'e' || s[i] == 'E') {
		j := i + 1
		if j < len(s) && (s[j] == '+' || s[j] == '-') {
			j++
		}
		k := j
		for k < len(s) && isDigit(s[k]) {
			k++
		}
		if k > j {
			i = k
		}
	}
	return s[:i], strings.TrimLeftFunc(s[i:], unicode.IsSpace)
}

func isDigit(b byte) bool { return b >= '0' && b <= '9' }
