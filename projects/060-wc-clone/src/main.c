/*
 * main.c - wc: print newline, word, character and byte counts.
 *
 * Flow: parse options, count every operand (or stdin), then print. All
 * counts are gathered before printing so the columns can be aligned to the
 * widest number, the same way GNU wc lines up its output.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "counts.h"
#include "options.h"
#include "report.h"

#define WC_VERSION "1.0.0"

typedef struct {
    const char *name;   /* NULL for anonymous stdin */
    wc_counts counts;
    int ok;
    int seekable;       /* regular file: size was knowable up front */
} wc_result;

static void usage(FILE *out, const char *prog) {
    fprintf(out,
        "Usage: %s [OPTION]... [FILE]...\n"
        "Print newline, word, and byte counts for each FILE, and a total line\n"
        "if more than one FILE is given. With no FILE, or when FILE is -, read\n"
        "standard input.\n\n"
        "  -c, --bytes            print the byte counts\n"
        "  -m, --chars            print the character (UTF-8) counts\n"
        "  -l, --lines            print the newline counts\n"
        "  -w, --words            print the word counts\n"
        "  -L, --max-line-length  print the maximum display width\n"
        "      --total=WHEN       when to print a total: auto, always, only, never\n"
        "      --help             display this help and exit\n"
        "      --version          output version information and exit\n",
        prog);
}

/* Count one operand. "-" means stdin. Errors are reported here. */
static int count_one(const char *prog, const char *path, wc_counts *out,
                     int *regular) {
    int is_stdin = strcmp(path, "-") == 0;
    FILE *fp = is_stdin ? stdin : fopen(path, "rb");

    if (!fp) {
        fprintf(stderr, "%s: %s: %s\n", prog, path, strerror(errno));
        return 0;
    }
    struct stat st;
    *regular = fstat(fileno(fp), &st) == 0 && S_ISREG(st.st_mode);

    int rc = wc_count_stream(fp, out);
    int saved = errno;
    if (!is_stdin)
        fclose(fp);
    if (rc != 0) {
        fprintf(stderr, "%s: %s: %s\n", prog, path, strerror(saved));
        return 0;
    }
    return 1;
}

int main(int argc, char **argv) {
    const char *prog = "wc";
    wc_options opt;
    int status = EXIT_SUCCESS;

    switch (wc_parse_args(argc, argv, &opt)) {
    case PARSE_HELP:
        usage(stdout, prog);
        wc_options_free(&opt);
        return EXIT_SUCCESS;
    case PARSE_VERSION:
        printf("wc (cs-projects) %s\n", WC_VERSION);
        wc_options_free(&opt);
        return EXIT_SUCCESS;
    case PARSE_ERROR:
        fprintf(stderr, "%s: %s\nTry '%s --help' for more information.\n",
                prog, opt.err, prog);
        wc_options_free(&opt);
        return 2;
    case PARSE_OK:
        break;
    }

    int n = opt.nfiles ? opt.nfiles : 1;
    wc_result *results = calloc((size_t)n, sizeof *results);
    if (!results) {
        fprintf(stderr, "%s: out of memory\n", prog);
        wc_options_free(&opt);
        return EXIT_FAILURE;
    }

    wc_counts total = {0};
    for (int i = 0; i < n; i++) {
        const char *path = opt.nfiles ? opt.files[i] : "-";
        results[i].name = opt.nfiles ? path : NULL;
        results[i].ok = count_one(prog, path, &results[i].counts,
                                  &results[i].seekable);
        if (results[i].ok)
            wc_counts_add(&total, &results[i].counts);
        else
            status = EXIT_FAILURE;
    }

    int show_total = opt.total == TOTAL_ALWAYS || opt.total == TOTAL_ONLY ||
                     (opt.total == TOTAL_AUTO && n > 1);
    int show_rows = opt.total != TOTAL_ONLY;

    /* Count how many columns will be printed. A single column for a single
     * row needs no padding at all. */
    int ncols = 0;
    for (unsigned s = opt.show; s; s >>= 1)
        ncols += s & 1;

    /* Column width: wide enough for the largest value. Byte counts bound
     * every other count except max_line, so the larger of the byte total
     * and max_line decides. If any input was a pipe or terminal, GNU wc
     * could not size it in advance and uses a minimum width of 7; we copy
     * that so the output matches. One column for one input needs no
     * padding at all. */
    uint64_t widest = total.bytes > total.max_line ? total.bytes : total.max_line;
    int width = wc_digits(widest);
    for (int i = 0; i < n; i++)
        if (results[i].ok && !results[i].seekable && width < 7)
            width = 7;
    if ((ncols == 1 && n == 1) || opt.total == TOTAL_ONLY)
        width = 1;

    if (show_rows) {
        for (int i = 0; i < n; i++)
            if (results[i].ok)
                wc_print_row(stdout, &results[i].counts, opt.show, width,
                             results[i].name);
    }
    if (show_total)
        wc_print_row(stdout, &total, opt.show, width,
                     opt.total == TOTAL_ONLY ? NULL : "total");

    free(results);
    wc_options_free(&opt);
    if (fflush(stdout) != 0)
        status = EXIT_FAILURE;
    return status;
}
