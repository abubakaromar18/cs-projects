// Command convert is a small unit-conversion CLI.
//
//	convert 10 km to mi          # one-shot conversion
//	convert -all 1 GiB           # show a value in every unit of its category
//	convert -list data           # list known units
//	convert                      # interactive mode (reads queries from stdin)
package main

import (
	"bufio"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
	"text/tabwriter"

	"github.com/abubakaromar18/cs-projects/projects/042-unit-converter/internal/format"
	"github.com/abubakaromar18/cs-projects/projects/042-unit-converter/internal/units"
)

func main() {
	os.Exit(run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr))
}

// config holds parsed command-line options.
type config struct {
	precision int
	all       bool
	list      bool
	group     bool
}

// run is the real entry point; it is separated from main so tests can drive
// the CLI with in-memory streams and inspect the exit code.
func run(args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("convert", flag.ContinueOnError)
	fs.SetOutput(stderr)
	var cfg config
	fs.IntVar(&cfg.precision, "p", 6, "significant digits in results")
	fs.BoolVar(&cfg.all, "all", false, "convert to every unit in the source unit's category")
	fs.BoolVar(&cfg.list, "list", false, "list known units (optionally for one category)")
	fs.BoolVar(&cfg.group, "g", false, "group thousands with commas")
	fs.Usage = func() {
		fmt.Fprintf(stderr, `usage: convert [flags] <value> <unit> [to <unit>]

Examples:
  convert 10 km to mi
  convert 98.6F C
  convert -all 1 GiB
  convert -list temperature

Run without arguments for interactive mode.

Flags:
`)
		fs.PrintDefaults()
	}
	if err := fs.Parse(protectNegatives(args)); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return 0
		}
		return 2
	}
	if cfg.precision < 1 || cfg.precision > 17 {
		fmt.Fprintln(stderr, "convert: -p must be between 1 and 17")
		return 2
	}

	reg := units.Default()

	if cfg.list {
		return listUnits(reg, units.Category(strings.ToLower(strings.Join(fs.Args(), " "))), stdout, stderr)
	}

	if fs.NArg() == 0 {
		return repl(reg, cfg, stdin, stdout, stderr)
	}

	if err := answer(reg, cfg, strings.Join(fs.Args(), " "), stdout); err != nil {
		fmt.Fprintln(stderr, "convert:", err)
		return 1
	}
	return 0
}

// protectNegatives inserts "--" before the first argument that looks like a
// negative number, so "convert -40 C to F" is not mistaken for a flag "-40".
func protectNegatives(args []string) []string {
	for i, a := range args {
		if a == "--" {
			return args
		}
		if len(a) > 1 && a[0] == '-' && (isDigitByte(a[1]) || a[1] == '.') {
			out := make([]string, 0, len(args)+1)
			out = append(out, args[:i]...)
			out = append(out, "--")
			return append(out, args[i:]...)
		}
	}
	return args
}

func isDigitByte(b byte) bool { return b >= '0' && b <= '9' }

// answer parses and evaluates a single query, writing the result to w.
func answer(reg *units.Registry, cfg config, input string, w io.Writer) error {
	q, err := reg.ParseQuery(input)
	if err != nil {
		return err
	}
	num := func(v float64) string {
		if cfg.group {
			return format.Grouped(v, cfg.precision)
		}
		return format.Number(v, cfg.precision)
	}

	if q.HasTarget() && !cfg.all {
		out, err := units.ConvertUnits(q.Value, q.From, q.To)
		if err != nil {
			return err
		}
		fmt.Fprintf(w, "%s %s = %s %s\n", num(q.Value), q.From.Symbol, num(out), q.To.Symbol)
		return nil
	}

	// No target (or -all): show the value in every unit of the category.
	tw := tabwriter.NewWriter(w, 0, 0, 2, ' ', tabwriter.AlignRight)
	fmt.Fprintf(w, "%s %s (%s) =\n", num(q.Value), q.From.Symbol, q.From.Name)
	for _, u := range reg.Units(q.From.Category) {
		if u.Symbol == q.From.Symbol {
			continue
		}
		out, err := units.ConvertUnits(q.Value, q.From, u)
		if err != nil {
			return err
		}
		fmt.Fprintf(tw, "  %s\t %s\t\n", num(out), u.Symbol)
	}
	return tw.Flush()
}

func listUnits(reg *units.Registry, cat units.Category, stdout, stderr io.Writer) int {
	cats := reg.Categories()
	if cat != "" {
		found := false
		for _, c := range cats {
			if c == cat {
				found = true
			}
		}
		if !found {
			fmt.Fprintf(stderr, "convert: unknown category %q (have: %s)\n", cat, joinCats(cats))
			return 1
		}
		cats = []units.Category{cat}
	}
	tw := tabwriter.NewWriter(stdout, 0, 0, 2, ' ', 0)
	for i, c := range cats {
		if i > 0 {
			fmt.Fprintln(tw)
		}
		fmt.Fprintf(tw, "[%s]\n", c)
		for _, u := range reg.Units(c) {
			fmt.Fprintf(tw, "  %s\t%s\t%s\n", u.Symbol, u.Name, strings.Join(u.Aliases, ", "))
		}
	}
	tw.Flush()
	return 0
}

func joinCats(cs []units.Category) string {
	s := make([]string, len(cs))
	for i, c := range cs {
		s[i] = string(c)
	}
	return strings.Join(s, ", ")
}

// repl reads one query per line until EOF or "quit". Errors are reported but
// do not end the session; the exit code is 1 if any line failed.
func repl(reg *units.Registry, cfg config, stdin io.Reader, stdout, stderr io.Writer) int {
	interactive := isTerminal(stdin)
	if interactive {
		fmt.Fprintln(stdout, `Unit converter. Type e.g. "10 km to mi", "list", or "quit".`)
	}
	sc := bufio.NewScanner(stdin)
	status := 0
	for {
		if interactive {
			fmt.Fprint(stdout, "> ")
		}
		if !sc.Scan() {
			break
		}
		line := strings.TrimSpace(sc.Text())
		switch {
		case line == "" || strings.HasPrefix(line, "#"):
			continue
		case line == "quit" || line == "exit":
			return status
		case line == "list":
			listUnits(reg, "", stdout, stderr)
			continue
		}
		if err := answer(reg, cfg, line, stdout); err != nil {
			fmt.Fprintln(stderr, "error:", err)
			status = 1
		}
	}
	if err := sc.Err(); err != nil {
		fmt.Fprintln(stderr, "convert:", err)
		return 1
	}
	return status
}

// isTerminal reports whether r is an interactive character device, so piped
// input does not get prompts mixed into its output.
func isTerminal(r io.Reader) bool {
	f, ok := r.(*os.File)
	if !ok {
		return false
	}
	st, err := f.Stat()
	return err == nil && st.Mode()&os.ModeCharDevice != 0
}
