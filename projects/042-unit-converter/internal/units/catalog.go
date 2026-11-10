package units

import "math"

// Default returns a registry pre-populated with the built-in unit catalog:
// length (base: metre), mass (base: kilogram), temperature (base: kelvin) and
// data size (base: byte).
func Default() *Registry {
	r := NewRegistry()
	addLength(r)
	addMass(r)
	addTemperature(r)
	addDataSize(r)
	return r
}

// linear is a small helper for units with no offset.
func linear(cat Category, sym, name string, scale float64, aliases ...string) Unit {
	return Unit{Symbol: sym, Name: name, Category: cat, Scale: scale, Aliases: aliases}
}

func addLength(r *Registry) {
	// Imperial units are defined exactly in terms of the metre by the 1959
	// international yard and pound agreement: 1 in = 25.4 mm exactly.
	const inch = 0.0254
	for _, u := range []Unit{
		linear(Length, "nm", "nanometre", 1e-9, "nanometer", "nanometres", "nanometers"),
		linear(Length, "µm", "micrometre", 1e-6, "um", "micron", "microns", "micrometer", "micrometres", "micrometers"),
		linear(Length, "mm", "millimetre", 1e-3, "millimeter", "millimetres", "millimeters"),
		linear(Length, "cm", "centimetre", 1e-2, "centimeter", "centimetres", "centimeters"),
		linear(Length, "m", "metre", 1, "meter", "metres", "meters"),
		linear(Length, "km", "kilometre", 1e3, "kilometer", "kilometres", "kilometers"),
		linear(Length, "in", "inch", inch, "inches", `"`),
		linear(Length, "ft", "foot", 12*inch, "feet", "'"),
		linear(Length, "yd", "yard", 36*inch, "yards"),
		linear(Length, "mi", "mile", 63360*inch, "miles"),
		linear(Length, "nmi", "nautical mile", 1852, "nautical miles", "NM"),
	} {
		r.MustAdd(u)
	}
}

func addMass(r *Registry) {
	// 1 lb = 0.45359237 kg exactly (international avoirdupois pound).
	const pound = 0.45359237
	for _, u := range []Unit{
		linear(Mass, "µg", "microgram", 1e-9, "ug", "mcg", "micrograms"),
		linear(Mass, "mg", "milligram", 1e-6, "milligrams"),
		linear(Mass, "g", "gram", 1e-3, "grams", "gramme", "grammes"),
		linear(Mass, "kg", "kilogram", 1, "kilograms", "kilo", "kilos"),
		linear(Mass, "t", "tonne", 1e3, "tonnes", "metric ton", "metric tons"),
		linear(Mass, "oz", "ounce", pound/16, "ounces"),
		linear(Mass, "lb", "pound", pound, "lbs", "pounds"),
		linear(Mass, "st", "stone", 14*pound, "stones"),
		linear(Mass, "ton", "short ton", 2000*pound, "tons", "short tons"),
	} {
		r.MustAdd(u)
	}
}

func addTemperature(r *Registry) {
	// Base unit: kelvin. Fahrenheit: K = (F + 459.67) * 5/9
	//                                  = F*(5/9) + 459.67*(5/9)
	const nine5 = 5.0 / 9.0
	for _, u := range []Unit{
		{Symbol: "K", Name: "kelvin", Category: Temperature, Scale: 1, Aliases: []string{"kelvins"}},
		{Symbol: "C", Name: "degree Celsius", Category: Temperature, Scale: 1, Offset: 273.15,
			Aliases: []string{"°C", "celsius", "centigrade", "degC"}},
		{Symbol: "F", Name: "degree Fahrenheit", Category: Temperature, Scale: nine5, Offset: 459.67 * nine5,
			Aliases: []string{"°F", "fahrenheit", "degF"}},
		{Symbol: "R", Name: "degree Rankine", Category: Temperature, Scale: nine5,
			Aliases: []string{"°R", "rankine", "degR"}},
	} {
		r.MustAdd(u)
	}
}

func addDataSize(r *Registry) {
	// Base unit: byte. Two prefix systems coexist:
	//   SI (decimal):  kB = 10^3,  MB = 10^6,  ...  (used by disk vendors, networking)
	//   IEC (binary):  KiB = 2^10, MiB = 2^20, ...  (used by RAM, most OSes)
	// Bits ("b") are 1/8 of a byte; network speeds are usually quoted in bits.
	r.MustAdd(linear(DataSize, "b", "bit", 1.0/8, "bit", "bits"))
	r.MustAdd(linear(DataSize, "B", "byte", 1, "byte", "bytes", "octet", "octets"))

	si := []struct{ p, name string }{
		{"k", "kilo"}, {"M", "mega"}, {"G", "giga"}, {"T", "tera"}, {"P", "peta"}, {"E", "exa"},
	}
	for i, s := range si {
		scale := math.Pow(1000, float64(i+1))
		byteAliases := []string{s.name + "byte", s.name + "bytes"}
		if s.p == "k" {
			byteAliases = append(byteAliases, "KB") // very common informal spelling
		}
		r.MustAdd(linear(DataSize, s.p+"B", s.name+"byte", scale, byteAliases...))
		r.MustAdd(linear(DataSize, s.p+"b", s.name+"bit", scale/8, s.name+"bit", s.name+"bits"))
	}

	iec := []struct{ p, name string }{
		{"Ki", "kibi"}, {"Mi", "mebi"}, {"Gi", "gibi"}, {"Ti", "tebi"}, {"Pi", "pebi"}, {"Ei", "exbi"},
	}
	for i, s := range iec {
		scale := math.Pow(1024, float64(i+1))
		r.MustAdd(linear(DataSize, s.p+"B", s.name+"byte", scale, s.name+"byte", s.name+"bytes"))
		r.MustAdd(linear(DataSize, s.p+"b", s.name+"bit", scale/8, s.name+"bit", s.name+"bits"))
	}
}
