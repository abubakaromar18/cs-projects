// Package units models physical and digital units of measure and converts
// values between them.
//
// Every unit belongs to exactly one Category (length, mass, ...). Within a
// category, each unit is described by an affine map onto the category's base
// unit:
//
//	base = value*Scale + Offset
//	value = (base - Offset) / Scale
//
// Most units are purely linear (Offset == 0), e.g. 1 km = 1000 m. Temperature
// scales are the classic counter-example: Celsius and Fahrenheit have
// different zero points, so a simple multiplication is not enough. Modelling
// every unit as an affine transform lets a single code path handle both.
package units

import (
	"errors"
	"fmt"
	"math"
	"sort"
	"strings"
)

// Category groups units that measure the same quantity. Conversions are only
// defined between units of the same category.
type Category string

const (
	Length      Category = "length"
	Mass        Category = "mass"
	Temperature Category = "temperature"
	DataSize    Category = "data"
)

// Unit is a single unit of measure.
type Unit struct {
	Symbol   string   // canonical, case-sensitive symbol, e.g. "km", "MiB"
	Name     string   // human-readable singular name, e.g. "kilometre"
	Aliases  []string // alternative spellings, e.g. "kilometer", "kilometers"
	Category Category
	Scale    float64 // multiplier onto the base unit
	Offset   float64 // additive offset onto the base unit (affine units only)
}

// ToBase converts v (expressed in u) to the category's base unit.
func (u Unit) ToBase(v float64) float64 { return v*u.Scale + u.Offset }

// FromBase converts v (expressed in the base unit) into u.
//
// Subtracting a large offset from a nearly equal base value suffers from
// catastrophic cancellation: 491.67 °R -> °C should be exactly 0 but yields
// ~5.7e-14. Differences smaller than the rounding error of the offset itself
// carry no information, so they are snapped to zero.
func (u Unit) FromBase(v float64) float64 {
	d := v - u.Offset
	if u.Offset != 0 && math.Abs(d) <= 1e-12*math.Abs(u.Offset) {
		d = 0
	}
	return d / u.Scale
}

// Errors returned by the registry.
var (
	ErrUnknownUnit       = errors.New("unknown unit")
	ErrAmbiguousUnit     = errors.New("ambiguous unit")
	ErrIncompatibleUnits = errors.New("incompatible units")
	ErrBelowAbsoluteZero = errors.New("temperature below absolute zero")
)

// Registry is a lookup table of units. Lookup is exact (case-sensitive) first
// because symbols like "Mb" (megabit) and "MB" (megabyte) or "mm" and "Mm"
// differ only in case. If no exact match exists, a case-insensitive lookup is
// tried and accepted only when it resolves to a single unit.
type Registry struct {
	units []*Unit
	exact map[string]*Unit   // symbol/alias -> unit
	fold  map[string][]*Unit // lower-cased symbol/alias -> candidate units
}

// NewRegistry builds an empty registry.
func NewRegistry() *Registry {
	return &Registry{exact: map[string]*Unit{}, fold: map[string][]*Unit{}}
}

// Add registers a unit. It returns an error if any of its names collide
// exactly with a unit that is already registered.
func (r *Registry) Add(u Unit) error {
	if u.Scale == 0 {
		return fmt.Errorf("unit %q: scale must be non-zero", u.Symbol)
	}
	p := &u
	// The symbol, the human-readable name and all aliases are lookup keys.
	var names []string
	for _, n := range append([]string{u.Symbol, u.Name}, u.Aliases...) {
		if n != "" {
			names = append(names, n)
		}
	}
	for _, n := range names {
		if existing, ok := r.exact[n]; ok && existing != p {
			return fmt.Errorf("name %q already used by %s", n, existing.Symbol)
		}
	}
	r.units = append(r.units, p)
	for _, n := range names {
		r.exact[n] = p
		key := strings.ToLower(n)
		if !containsUnit(r.fold[key], p) {
			r.fold[key] = append(r.fold[key], p)
		}
	}
	return nil
}

func containsUnit(list []*Unit, u *Unit) bool {
	for _, x := range list {
		if x == u {
			return true
		}
	}
	return false
}

// MustAdd is like Add but panics on error; intended for static tables.
func (r *Registry) MustAdd(u Unit) {
	if err := r.Add(u); err != nil {
		panic(err)
	}
}

// Lookup resolves a unit by symbol or alias.
func (r *Registry) Lookup(name string) (Unit, error) {
	name = strings.TrimSpace(name)
	if u, ok := r.exact[name]; ok {
		return *u, nil
	}
	cands := r.fold[strings.ToLower(name)]
	switch len(cands) {
	case 0:
		return Unit{}, fmt.Errorf("%w: %q", ErrUnknownUnit, name)
	case 1:
		return *cands[0], nil
	default:
		syms := make([]string, len(cands))
		for i, c := range cands {
			syms[i] = c.Symbol
		}
		sort.Strings(syms)
		return Unit{}, fmt.Errorf("%w: %q could be %s", ErrAmbiguousUnit, name, strings.Join(syms, ", "))
	}
}

// Convert converts value from one unit to another.
func (r *Registry) Convert(value float64, from, to string) (float64, error) {
	f, err := r.Lookup(from)
	if err != nil {
		return 0, err
	}
	t, err := r.Lookup(to)
	if err != nil {
		return 0, err
	}
	return ConvertUnits(value, f, t)
}

// ConvertUnits converts value between two already-resolved units.
func ConvertUnits(value float64, from, to Unit) (float64, error) {
	if from.Category != to.Category {
		return 0, fmt.Errorf("%w: %s (%s) -> %s (%s)",
			ErrIncompatibleUnits, from.Symbol, from.Category, to.Symbol, to.Category)
	}
	base := from.ToBase(value)
	// Temperature's base unit is kelvin, which cannot be negative. A tiny
	// epsilon tolerates floating-point noise around 0 K.
	if from.Category == Temperature && base < -1e-9 {
		return 0, fmt.Errorf("%w: %g %s", ErrBelowAbsoluteZero, value, from.Symbol)
	}
	return to.FromBase(base), nil
}

// Units returns all units in a category (or all units if cat is empty), in
// registration order.
func (r *Registry) Units(cat Category) []Unit {
	var out []Unit
	for _, u := range r.units {
		if cat == "" || u.Category == cat {
			out = append(out, *u)
		}
	}
	return out
}

// Categories returns the distinct categories in registration order.
func (r *Registry) Categories() []Category {
	seen := map[Category]bool{}
	var out []Category
	for _, u := range r.units {
		if !seen[u.Category] {
			seen[u.Category] = true
			out = append(out, u.Category)
		}
	}
	return out
}
