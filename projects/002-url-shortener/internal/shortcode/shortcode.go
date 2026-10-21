// Package shortcode generates and validates the short codes used in links.
//
// Generated codes are random base62 strings drawn from crypto/rand. With the
// default length of 7 there are 62^7 ≈ 3.5 trillion possible codes, so
// collisions are rare; the caller still retries on the occasional clash.
package shortcode

import (
	"crypto/rand"
	"errors"
	"fmt"
	"math/big"
	"regexp"
	"strings"
)

// Alphabet is the base62 character set: digits, lowercase, uppercase.
const Alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

// DefaultLength is the length of randomly generated codes.
const DefaultLength = 7

var (
	// ErrInvalidAlias is returned when a custom alias has bad characters or length.
	ErrInvalidAlias = errors.New("alias must be 3-32 characters of letters, digits, '-' or '_'")
	// ErrReservedAlias is returned when an alias would shadow a built-in route.
	ErrReservedAlias = errors.New("alias is reserved")

	aliasPattern = regexp.MustCompile(`^[A-Za-z0-9_-]{3,32}$`)

	// reserved holds path segments the HTTP server uses itself.
	reserved = map[string]bool{
		"api": true, "healthz": true, "shorten": true, "static": true,
		"favicon.ico": true, "robots.txt": true,
	}
)

// Generate returns a cryptographically random base62 code of length n.
func Generate(n int) (string, error) {
	if n <= 0 {
		return "", fmt.Errorf("shortcode: length must be positive, got %d", n)
	}
	max := big.NewInt(int64(len(Alphabet)))
	var b strings.Builder
	b.Grow(n)
	for i := 0; i < n; i++ {
		// rand.Int gives a uniform value in [0, 62), avoiding modulo bias.
		idx, err := rand.Int(rand.Reader, max)
		if err != nil {
			return "", fmt.Errorf("shortcode: reading randomness: %w", err)
		}
		b.WriteByte(Alphabet[idx.Int64()])
	}
	return b.String(), nil
}

// ValidateAlias checks a user-chosen custom code.
func ValidateAlias(alias string) error {
	if !aliasPattern.MatchString(alias) {
		return ErrInvalidAlias
	}
	if reserved[strings.ToLower(alias)] {
		return ErrReservedAlias
	}
	return nil
}

// EncodeBase62 converts a non-negative integer to base62. It is not used for
// random codes but is handy for sequential IDs and is shown here because it
// is the classic way URL shorteners map database IDs to short strings.
func EncodeBase62(n uint64) string {
	if n == 0 {
		return string(Alphabet[0])
	}
	var buf [11]byte // 62^11 > 2^64, so 11 digits always suffice
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = Alphabet[n%62]
		n /= 62
	}
	return string(buf[i:])
}

// DecodeBase62 is the inverse of EncodeBase62.
func DecodeBase62(s string) (uint64, error) {
	if s == "" {
		return 0, errors.New("shortcode: empty string")
	}
	var n uint64
	for _, c := range s {
		idx := strings.IndexRune(Alphabet, c)
		if idx < 0 {
			return 0, fmt.Errorf("shortcode: invalid character %q", c)
		}
		next := n*62 + uint64(idx)
		if next/62 != n { // overflow check
			return 0, errors.New("shortcode: value overflows uint64")
		}
		n = next
	}
	return n, nil
}
