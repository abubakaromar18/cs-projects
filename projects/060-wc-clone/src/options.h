/*
 * options.h - command-line parsing for wc.
 */
#ifndef WC_OPTIONS_H
#define WC_OPTIONS_H

/* Which columns to print, in the fixed output order. */
enum {
    WC_SHOW_LINES    = 1 << 0,
    WC_SHOW_WORDS    = 1 << 1,
    WC_SHOW_CHARS    = 1 << 2,
    WC_SHOW_BYTES    = 1 << 3,
    WC_SHOW_MAXLINE  = 1 << 4,
};

typedef enum { TOTAL_AUTO, TOTAL_ALWAYS, TOTAL_NEVER, TOTAL_ONLY } wc_total_mode;

typedef enum {
    PARSE_OK,       /* run normally                       */
    PARSE_HELP,     /* print usage, exit 0                */
    PARSE_VERSION,  /* print version, exit 0              */
    PARSE_ERROR,    /* message already in err, exit 2     */
} wc_parse_result;

typedef struct {
    unsigned show;          /* bitmask of WC_SHOW_*            */
    wc_total_mode total;
    char **files;           /* operands (points into argv)     */
    int nfiles;
    char err[128];          /* filled on PARSE_ERROR           */
} wc_options;

/*
 * Parse argv. Supports clustered short flags (-lw), long flags
 * (--lines), --total=WHEN, and "--" to end options. A lone "-" is an
 * operand meaning standard input. The files array is allocated by this
 * function and must be released with wc_options_free().
 */
wc_parse_result wc_parse_args(int argc, char **argv, wc_options *opt);
void wc_options_free(wc_options *opt);

#endif
