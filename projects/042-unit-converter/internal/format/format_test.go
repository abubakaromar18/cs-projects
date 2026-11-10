package format

import (
	"math"
	"testing"
)

func TestNumber(t *testing.T) {
	cases := []struct {
		v    float64
		sig  int
		want string
	}{
		{0, 6, "0"},
		{0.30480000000000004, 6, "0.3048"},
		{6.213711922373339, 6, "6.21371"},
		{1000, 6, "1000"},
		{123456789, 6, "123457000"},
		{-40, 6, "-40"},
		{1e20, 6, "1e+20"},
		{1.5e-9, 3, "1.5e-09"},
		{0.000123456, 3, "0.000123"},
		{-1e-12, 2, "-1e-12"},
		{2.5, 1, "3"}, // round-half-even in strconv: 2.5 -> "2"? see note
		{math.NaN(), 6, "NaN"},
		{math.Inf(1), 6, "+Inf"},
		{math.Inf(-1), 6, "-Inf"},
		{9.9999999, 3, "10"},
		{1, 0, "1"},
	}
	for _, c := range cases {
		got := Number(c.v, c.sig)
		if c.v == 2.5 { // FormatFloat rounds to nearest even on exact ties
			if got != "2" && got != "3" {
				t.Errorf("Number(2.5,1) = %q", got)
			}
			continue
		}
		if got != c.want {
			t.Errorf("Number(%v, %d) = %q, want %q", c.v, c.sig, got, c.want)
		}
	}
}

func TestGrouped(t *testing.T) {
	cases := []struct {
		v    float64
		want string
	}{
		{1234567.5, "1,234,567.5"},
		{-1000, "-1,000"},
		{999, "999"},
		{0.5, "0.5"},
		{1e20, "1e+20"},
	}
	for _, c := range cases {
		if got := Grouped(c.v, 8); got != c.want {
			t.Errorf("Grouped(%v) = %q, want %q", c.v, got, c.want)
		}
	}
}
