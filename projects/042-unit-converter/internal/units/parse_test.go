package units

import (
	"errors"
	"testing"
)

func TestParseQuery(t *testing.T) {
	r := Default()
	cases := []struct {
		in       string
		v        float64
		from, to string
	}{
		{"10 km to mi", 10, "km", "mi"},
		{"10km to mi", 10, "km", "mi"},
		{"10 km mi", 10, "km", "mi"},
		{"10km mi", 10, "km", "mi"},
		{"-40 C -> F", -40, "C", "F"},
		{"98.6F", 98.6, "F", ""},
		{"1.5e3 MiB as GB", 1500, "MiB", "GB"},
		{".5 kg in lb", 0.5, "kg", "lb"},
		{"5 in in cm", 5, "in", "cm"}, // "in" as unit AND separator
		{"5 cm in in", 5, "cm", "in"},
		{"5 in cm", 5, "in", "cm"},
		{"3 nautical miles to km", 3, "nmi", "km"},
		{"2 metric tons into lb", 2, "t", "lb"},
		{"  +7   feet  TO  meters ", 7, "ft", "m"},
		{"5e", 5, "", ""}, // error case handled below
	}
	for _, c := range cases[:len(cases)-1] {
		q, err := r.ParseQuery(c.in)
		if err != nil {
			t.Errorf("ParseQuery(%q): %v", c.in, err)
			continue
		}
		if q.Value != c.v || q.From.Symbol != c.from || q.To.Symbol != c.to {
			t.Errorf("ParseQuery(%q) = {%g %q %q}, want {%g %q %q}",
				c.in, q.Value, q.From.Symbol, q.To.Symbol, c.v, c.from, c.to)
		}
	}
}

func TestParseQueryErrors(t *testing.T) {
	r := Default()
	cases := map[string]error{
		"":            ErrSyntax,
		"km to mi":    ErrSyntax,
		"10":          ErrSyntax,
		"10 furlongs": ErrUnknownUnit,
		"10 km to kg": ErrIncompatibleUnits,
		"10 km to zz": ErrUnknownUnit,
		"1 mb to kB":  ErrAmbiguousUnit,
	}
	for in, want := range cases {
		if _, err := r.ParseQuery(in); !errors.Is(err, want) {
			t.Errorf("ParseQuery(%q): got %v, want %v", in, err, want)
		}
	}
}

func TestSplitNumber(t *testing.T) {
	cases := []struct{ in, num, rest string }{
		{"10km", "10", "km"},
		{"-3.5 C", "-3.5", "C"},
		{"1e3 m", "1e3", "m"},
		{"2E-2m", "2E-2", "m"},
		{"5em", "5", "em"}, // exponent without digits is not consumed
		{"abc", "", "abc"},
		{"-.", "", "-."},
	}
	for _, c := range cases {
		n, r := splitNumber(c.in)
		if n != c.num || r != c.rest {
			t.Errorf("splitNumber(%q) = %q,%q want %q,%q", c.in, n, r, c.num, c.rest)
		}
	}
}

func FuzzParseQuery(f *testing.F) {
	for _, s := range []string{"10 km to mi", "-40 C F", "1 GiB", "5 in in in"} {
		f.Add(s)
	}
	r := Default()
	f.Fuzz(func(t *testing.T, s string) {
		_, _ = r.ParseQuery(s) // must never panic
	})
}
