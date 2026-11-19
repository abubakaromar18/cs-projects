/*
 * report.h - formatting counts into aligned columns.
 */
#ifndef WC_REPORT_H
#define WC_REPORT_H

#include <stdio.h>

#include "counts.h"

/* Number of decimal digits needed to print v (at least 1). */
int wc_digits(uint64_t v);

/*
 * Print one row: the selected columns right-aligned to width, separated by
 * single spaces, followed by " name" when name is not NULL.
 */
void wc_print_row(FILE *out, const wc_counts *c, unsigned show, int width,
                  const char *name);

#endif
