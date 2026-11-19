/*
 * options.c - a small hand-written option parser.
 *
 * getopt_long would also work, but writing the parser out keeps the
 * program portable (no GNU extension) and lets the unit tests call it
 * repeatedly without global state such as optind.
 */
#include "options.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const struct {
    const char *name;
    char shortopt;
    unsigned flag;
} long_flags[] = {
    {"lines",           'l', WC_SHOW_LINES},
    {"words",           'w', WC_SHOW_WORDS},
    {"chars",           'm', WC_SHOW_CHARS},
    {"bytes",           'c', WC_SHOW_BYTES},
    {"max-line-length", 'L', WC_SHOW_MAXLINE},
};
#define NFLAGS (sizeof long_flags / sizeof long_flags[0])

static int short_flag(char c, unsigned *show) {
    for (size_t i = 0; i < NFLAGS; i++) {
        if (long_flags[i].shortopt == c) {
            *show |= long_flags[i].flag;
            return 1;
        }
    }
    return 0;
}

static wc_parse_result fail(wc_options *opt, const char *fmt, const char *arg) {
    snprintf(opt->err, sizeof opt->err, fmt, arg);
    return PARSE_ERROR;
}

static wc_parse_result parse_long(const char *arg, wc_options *opt) {
    if (strcmp(arg, "help") == 0)
        return PARSE_HELP;
    if (strcmp(arg, "version") == 0)
        return PARSE_VERSION;

    if (strncmp(arg, "total=", 6) == 0) {
        const char *when = arg + 6;
        if (strcmp(when, "auto") == 0)        opt->total = TOTAL_AUTO;
        else if (strcmp(when, "always") == 0) opt->total = TOTAL_ALWAYS;
        else if (strcmp(when, "never") == 0)  opt->total = TOTAL_NEVER;
        else if (strcmp(when, "only") == 0)   opt->total = TOTAL_ONLY;
        else return fail(opt, "invalid argument '%s' for '--total'", when);
        return PARSE_OK;
    }

    for (size_t i = 0; i < NFLAGS; i++) {
        if (strcmp(arg, long_flags[i].name) == 0) {
            opt->show |= long_flags[i].flag;
            return PARSE_OK;
        }
    }
    return fail(opt, "unrecognized option '--%s'", arg);
}

wc_parse_result wc_parse_args(int argc, char **argv, wc_options *opt) {
    int options_done = 0;

    memset(opt, 0, sizeof *opt);
    opt->total = TOTAL_AUTO;
    opt->files = calloc((size_t)(argc > 0 ? argc : 1), sizeof *opt->files);
    if (!opt->files)
        return fail(opt, "%s", "out of memory");

    for (int i = 1; i < argc; i++) {
        char *arg = argv[i];

        if (options_done || arg[0] != '-' || arg[1] == '\0') {
            opt->files[opt->nfiles++] = arg;    /* operand, incl. "-" */
        } else if (strcmp(arg, "--") == 0) {
            options_done = 1;
        } else if (arg[1] == '-') {
            wc_parse_result r = parse_long(arg + 2, opt);
            if (r != PARSE_OK)
                return r;
        } else {
            for (char *p = arg + 1; *p; p++) {
                if (!short_flag(*p, &opt->show)) {
                    char bad[2] = {*p, '\0'};
                    return fail(opt, "invalid option -- '%s'", bad);
                }
            }
        }
    }

    /* No column flags means the classic default: lines, words, bytes. */
    if (opt->show == 0)
        opt->show = WC_SHOW_LINES | WC_SHOW_WORDS | WC_SHOW_BYTES;
    return PARSE_OK;
}

void wc_options_free(wc_options *opt) {
    free(opt->files);
    opt->files = NULL;
    opt->nfiles = 0;
}
