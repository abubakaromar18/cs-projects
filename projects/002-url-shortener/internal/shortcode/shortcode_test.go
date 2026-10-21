package shortcode

import (
	"errors"
	"math"
	"strings"
	"testing"
)

func TestGenerateLengthAndAlphabet(t *testing.T) {
	for _, n := range []int{1, 7, 20} {
		code, err := Generate(n)
		if err != nil {
			t.Fatalf("Generate(%d): %v", n, err)
		}
		if len(code) != n {
			t.Errorf("Generate(%d) length = %d", n, len(code))
		}
		for _, c := range code {
			if !strings.ContainsRune(Alphabet, c) {
				t.Errorf("Generate(%d) produced non-base62 char %q", n, c)
			}
		}
	}
}

func TestGenerateRejectsBadLength(t *testing.T) {
	if _, err := Generate(0); err == nil {
		t.Error("Generate(0) should fail")
	}
}

func TestGenerateIsUnlikelyToRepeat(t *testing.T) {
	seen := make(map[string]bool)
	for i := 0; i < 10000; i++ {
		c, err := Generate(DefaultLength)
		if err != nil {
			t.Fatal(err)
		}
		if seen[c] {
			t.Fatalf("duplicate code %q after %d draws", c, i)
		}
		seen[c] = true
	}
}

func TestValidateAlias(t *testing.T) {
	cases := []struct {
		alias string
		want  error
	}{
		{"go-docs", nil},
		{"My_Link_2", nil},
		{"abc", nil},
		{"ab", ErrInvalidAlias},
		{strings.Repeat("a", 33), ErrInvalidAlias},
		{"has space", ErrInvalidAlias},
		{"slash/es", ErrInvalidAlias},
		{"emoji😀", ErrInvalidAlias},
		{"api", ErrReservedAlias},
		{"HEALTHZ", ErrReservedAlias},
	}
	for _, tc := range cases {
		if got := ValidateAlias(tc.alias); !errors.Is(got, tc.want) {
			t.Errorf("ValidateAlias(%q) = %v, want %v", tc.alias, got, tc.want)
		}
	}
}

func TestBase62RoundTrip(t *testing.T) {
	cases := map[uint64]string{0: "0", 1: "1", 61: "Z", 62: "10", 3843: "ZZ"}
	for n, want := range cases {
		if got := EncodeBase62(n); got != want {
			t.Errorf("EncodeBase62(%d) = %q, want %q", n, got, want)
		}
	}
	for _, n := range []uint64{0, 1, 62, 12345, 1 << 40, math.MaxUint64} {
		got, err := DecodeBase62(EncodeBase62(n))
		if err != nil || got != n {
			t.Errorf("round trip %d -> %d (err %v)", n, got, err)
		}
	}
}

func TestDecodeBase62Errors(t *testing.T) {
	for _, s := range []string{"", "ab-c", strings.Repeat("Z", 12)} {
		if _, err := DecodeBase62(s); err == nil {
			t.Errorf("DecodeBase62(%q) should fail", s)
		}
	}
}
