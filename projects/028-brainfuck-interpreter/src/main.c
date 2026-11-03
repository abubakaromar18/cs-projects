/*
 * main.c - Command-line front end: `bf [options] [FILE]`.
 */
#define _GNU_SOURCE /* getopt_long */
#include "bf.h"

#include <getopt.h>
#include <stdlib.h>
#include <string.h>

static void usage(FILE *fp)
{
    fputs("usage: bf [options] [FILE]\n"
          "Run a Brainfuck program from FILE, -e CODE, or standard input.\n\n"
          "  -e, --expr CODE     program text given on the command line\n"
          "  -O, --opt LEVEL     optimization level 0, 1 or 2 (default 2)\n"
          "  -t, --tape CELLS    tape size in cells (default 30000)\n"
          "      --eof MODE      ',' at end of input: zero | neg | keep (default zero)\n"
          "  -m, --max-steps N   abort after N instructions (default unlimited)\n"
          "  -d, --dump          print the compiled IR and exit\n"
          "  -s, --stats         print instruction counts to stderr\n"
          "  -h, --help          show this help\n",
          fp);
}

/* Read a whole stream into a heap buffer. */
static char *slurp(FILE *fp, size_t *len)
{
    size_t cap = 4096, n = 0;
    char *buf = malloc(cap);
    if (!buf)
        return NULL;
    size_t got;
    while ((got = fread(buf + n, 1, cap - n, fp)) > 0) {
        n += got;
        if (n == cap) {
            char *nb = realloc(buf, cap *= 2);
            if (!nb) {
                free(buf);
                return NULL;
            }
            buf = nb;
        }
    }
    *len = n;
    return buf;
}

int main(int argc, char **argv)
{
    static const struct option longopts[] = {
        {"expr", required_argument, 0, 'e'},
        {"opt", required_argument, 0, 'O'},
        {"tape", required_argument, 0, 't'},
        {"eof", required_argument, 0, 'E'},
        {"max-steps", required_argument, 0, 'm'},
        {"dump", no_argument, 0, 'd'},
        {"stats", no_argument, 0, 's'},
        {"help", no_argument, 0, 'h'},
        {0, 0, 0, 0},
    };

    const char *expr = NULL;
    int opt_level = 2, dump = 0, show_stats = 0;
    bf_config cfg = bf_default_config();

    int c;
    while ((c = getopt_long(argc, argv, "e:O:t:m:dsh", longopts, NULL)) != -1) {
        switch (c) {
        case 'e': expr = optarg; break;
        case 'O':
            opt_level = atoi(optarg);
            if (opt_level < 0 || opt_level > 2) {
                fprintf(stderr, "bf: -O must be 0, 1 or 2\n");
                return 2;
            }
            break;
        case 't':
            cfg.tape_size = strtoul(optarg, NULL, 10);
            if (cfg.tape_size == 0) {
                fprintf(stderr, "bf: tape size must be positive\n");
                return 2;
            }
            break;
        case 'E':
            if (!strcmp(optarg, "zero"))      cfg.eof = BF_EOF_ZERO;
            else if (!strcmp(optarg, "neg"))  cfg.eof = BF_EOF_MINUS_ONE;
            else if (!strcmp(optarg, "keep")) cfg.eof = BF_EOF_UNCHANGED;
            else {
                fprintf(stderr, "bf: --eof must be zero, neg or keep\n");
                return 2;
            }
            break;
        case 'm': cfg.max_steps = strtoull(optarg, NULL, 10); break;
        case 'd': dump = 1; break;
        case 's': show_stats = 1; break;
        case 'h': usage(stdout); return 0;
        default:  usage(stderr); return 2;
        }
    }

    /* Load the program text. */
    char *src = NULL;
    size_t len = 0;
    const char *name = "<expr>";
    if (expr) {
        len = strlen(expr);
        src = malloc(len + 1);
        if (src)
            memcpy(src, expr, len + 1);
    } else if (optind < argc) {
        name = argv[optind];
        FILE *fp = fopen(name, "rb");
        if (!fp) {
            perror(name);
            return 1;
        }
        src = slurp(fp, &len);
        fclose(fp);
    } else {
        usage(stderr);
        return 2;
    }
    if (!src) {
        fprintf(stderr, "bf: out of memory\n");
        return 1;
    }

    bf_program prog;
    bf_error err;
    if (bf_compile(src, len, opt_level, &prog, &err) != BF_OK) {
        fprintf(stderr, "%s:%zu:%zu: error: %s\n", name, err.line, err.col,
                bf_strerror(err.status));
        free(src);
        return 1;
    }
    free(src);

    if (dump) {
        bf_dump(&prog, stdout);
        bf_program_free(&prog);
        return 0;
    }

    bf_file_io fio = {stdin, stdout};
    bf_stats stats;
    bf_status st = bf_run(&prog, &cfg, bf_io_files(&fio), &stats, &err);
    fflush(stdout);

    if (show_stats)
        fprintf(stderr, "bf: -O%d  %zu ops  %llu steps executed\n", opt_level,
                prog.len, (unsigned long long)stats.steps);
    if (st != BF_OK)
        fprintf(stderr, "bf: runtime error at op %zu: %s\n", err.pc, bf_strerror(st));

    bf_program_free(&prog);
    return st == BF_OK ? 0 : 1;
}
