package units

import (
	"errors"
	"math"
	"testing"
)

func approx(a, b float64) bool {
	if a == b {
		return true
	}
	return math.Abs(a-b) <= 1e-9*math.Max(math.Abs(a), math.Abs(b))
}

func TestConvertTable(t *testing.T) {
	r := Default()
	cases := []struct {
		v        float64
		from, to string
		want     float64
	}{
		// length
		{1, "km", "m", 1000},
		{1, "in", "cm", 2.54},
		{1, "mi", "km", 1.609344},
		{1, "ft", "in", 12},
		{3, "ft", "yd", 1},
		{1, "nmi", "m", 1852},
		{1, "micron", "nm", 1000},
		{2, "nautical miles", "km", 3.704},
		// mass
		{1, "kg", "lb", 1 / 0.45359237},
		{16, "oz", "lb", 1},
		{1, "st", "lb", 14},
		{1, "t", "kg", 1000},
		{1, "ton", "lb", 2000},
		{1, "mcg", "mg", 0.001},
		// temperature
		{0, "C", "F", 32},
		{100, "C", "F", 212},
		{-40, "C", "F", -40},
		{0, "K", "C", -273.15},
		{98.6, "F", "C", 37},
		{0, "F", "R", 459.67},
		{491.67, "R", "C", 0},
		{300, "kelvin", "celsius", 26.85},
		// data size
		{1, "B", "b", 8},
		{1, "KiB", "B", 1024},
		{1, "kB", "B", 1000},
		{1, "GiB", "MiB", 1024},
		{1, "GB", "MB", 1000},
		{1, "TB", "GiB", 1e12 / (1 << 30)},
		{100, "Mb", "MB", 12.5},
		{1, "Gib", "MiB", 128},
		{1, "KB", "kB", 1},
	}
	for _, c := range cases {
		got, err := r.Convert(c.v, c.from, c.to)
		if err != nil {
			t.Errorf("%g %s->%s: unexpected error %v", c.v, c.from, c.to, err)
			continue
		}
		if !approx(got, c.want) {
			t.Errorf("%g %s->%s = %.12g, want %.12g", c.v, c.from, c.to, got, c.want)
		}
	}
}

// Round-tripping through every pair of units in a category must return the
// original value (up to floating-point tolerance).
func TestRoundTripAllPairs(t *testing.T) {
	r := Default()
	for _, cat := range r.Categories() {
		us := r.Units(cat)
		for _, a := range us {
			for _, b := range us {
				v := 123.456
				x, err := ConvertUnits(v, a, b)
				if err != nil {
					t.Fatalf("%s->%s: %v", a.Symbol, b.Symbol, err)
				}
				y, err := ConvertUnits(x, b, a)
				if err != nil {
					t.Fatalf("%s->%s: %v", b.Symbol, a.Symbol, err)
				}
				if !approx(y, v) {
					t.Errorf("%s->%s->%s: got %.15g want %g", a.Symbol, b.Symbol, a.Symbol, y, v)
				}
			}
		}
	}
}

func TestIdentity(t *testing.T) {
	r := Default()
	for _, u := range r.Units("") {
		got, err := ConvertUnits(42, u, u)
		if err != nil || !approx(got, 42) {
			t.Errorf("%s identity: got %v, %v", u.Symbol, got, err)
		}
	}
}

func TestIncompatible(t *testing.T) {
	_, err := Default().Convert(1, "kg", "m")
	if !errors.Is(err, ErrIncompatibleUnits) {
		t.Fatalf("want ErrIncompatibleUnits, got %v", err)
	}
}

func TestBelowAbsoluteZero(t *testing.T) {
	r := Default()
	for _, c := range []struct {
		v float64
		u string
	}{{-1, "K"}, {-274, "C"}, {-460, "F"}, {-0.5, "R"}} {
		if _, err := r.Convert(c.v, c.u, "K"); !errors.Is(err, ErrBelowAbsoluteZero) {
			t.Errorf("%g %s: want ErrBelowAbsoluteZero, got %v", c.v, c.u, err)
		}
	}
	// Exactly absolute zero is fine.
	if _, err := r.Convert(-273.15, "C", "F"); err != nil {
		t.Errorf("-273.15 C should be valid: %v", err)
	}
}

func TestLookupCaseSensitivity(t *testing.T) {
	r := Default()
	cases := map[string]string{
		"mb":         "", // ambiguous: megabit vs megabyte
		"Mb":         "Mb",
		"MB":         "MB",
		"mm":         "mm",
		"KM":         "km", // unambiguous case-insensitive fallback
		"Lbs":        "lb",
		"°C":         "C",
		"Kilometers": "km",
	}
	for in, want := range cases {
		u, err := r.Lookup(in)
		if want == "" {
			if !errors.Is(err, ErrAmbiguousUnit) {
				t.Errorf("Lookup(%q): want ambiguous error, got %v (%v)", in, u.Symbol, err)
			}
			continue
		}
		if err != nil || u.Symbol != want {
			t.Errorf("Lookup(%q) = %q, %v; want %q", in, u.Symbol, err, want)
		}
	}
	if _, err := r.Lookup("furlong"); !errors.Is(err, ErrUnknownUnit) {
		t.Errorf("want ErrUnknownUnit, got %v", err)
	}
}

func TestRegistryRejectsDuplicates(t *testing.T) {
	r := NewRegistry()
	r.MustAdd(Unit{Symbol: "x", Category: Length, Scale: 1})
	if err := r.Add(Unit{Symbol: "y", Aliases: []string{"x"}, Category: Length, Scale: 2}); err == nil {
		t.Fatal("expected duplicate-name error")
	}
	if err := r.Add(Unit{Symbol: "z", Category: Length}); err == nil {
		t.Fatal("expected zero-scale error")
	}
}

func TestCategoriesOrder(t *testing.T) {
	got := Default().Categories()
	want := []Category{Length, Mass, Temperature, DataSize}
	if len(got) != len(want) {
		t.Fatalf("got %v", got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("got %v want %v", got, want)
		}
	}
}
