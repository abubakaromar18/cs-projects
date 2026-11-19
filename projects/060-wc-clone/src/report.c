/*
 * report.c - output formatting.
 */
#include "report.h"

#include <inttypes.h>

#include "options.h"

int wc_digits(uint64_t v) {
    int d = 1;
    while (v >= 10) {
        v /= 10;
        d++;
    }
    return d;
}

void wc_print_row(FILE *out, const wc_counts *c, unsigned show, int width,
                  const char *name) {
    /* Fixed column order, matching POSIX/GNU wc. */
    const struct { unsigned flag; uint64_t value; } cols[] = {
        {WC_SHOW_LINES,   c->lines},
        {WC_SHOW_WORDS,   c->words},
        {WC_SHOW_CHARS,   c->chars},
        {WC_SHOW_BYTES,   c->bytes},
        {WC_SHOW_MAXLINE, c->max_line},
    };
    int first = 1;

    for (size_t i = 0; i < sizeof cols / sizeof cols[0]; i++) {
        if (!(show & cols[i].flag))
            continue;
        fprintf(out, "%s%*" PRIu64, first ? "" : " ", width, cols[i].value);
        first = 0;
    }
    if (name)
        fprintf(out, " %s", name);
    fputc('\n', out);
}
