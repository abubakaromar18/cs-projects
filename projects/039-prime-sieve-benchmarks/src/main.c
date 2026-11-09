/*
 * main.c - command-line front end: benchmark, count, list, and range queries.
 */
#include "sieve.h"

#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static void usage(FILE *out)
{
    fputs("usage:\n"
          "  primes bench [--limit N] [--reps R]   compare every algorithm\n"
          "  primes count [--algo NAME] N          count primes <= N\n"
          "  primes list  [--algo NAME] N          print primes <= N\n"
          "  primes range LO HI                    print primes in [LO, HI]\n"
          "  primes algos                          list algorithm names\n",
          out);
}

/* Strict decimal parser; unlike atoll it rejects junk and negative numbers. */
static int parse_u64(const char *text, uint64_t *value)
{
    if (*text < '0' || *text > '9')
        return -1;
    char *end;
    errno = 0;
    unsigned long long parsed = strtoull(text, &end, 10);
    if (errno != 0 || *end != '\0')
        return -1;
    *value = parsed;
    return 0;
}

static double now_seconds(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

static int fail_status(sieve_status status)
{
    fprintf(stderr, "error: %s\n", sieve_strerror(status));
    return 1;
}

static int fail_number(const char *text)
{
    fprintf(stderr, "error: not a valid non-negative integer: %s\n", text);
    return 2;
}

static int cmd_bench(int argc, char **argv)
{
    uint64_t limit = 100000000, reps = 3;

    for (int i = 0; i < argc; i++) {
        uint64_t *target = NULL;
        if (strcmp(argv[i], "--limit") == 0)
            target = &limit;
        else if (strcmp(argv[i], "--reps") == 0)
            target = &reps;
        if (!target || i + 1 >= argc) {
            usage(stderr);
            return 2;
        }
        if (parse_u64(argv[++i], target) != 0)
            return fail_number(argv[i]);
    }
    if (reps == 0) {
        fputs("error: --reps must be at least 1\n", stderr);
        return 2;
    }

    size_t n;
    const sieve_algorithm *algos = sieve_algorithms(&n);
    printf("limit = %" PRIu64 ", best of %" PRIu64 " run(s)\n\n", limit, reps);
    printf("%-14s %14s %12s  %s\n", "algorithm", "primes", "seconds", "notes");

    for (size_t a = 0; a < n; a++) {
        uint64_t count = 0;
        double best = -1.0;
        /* The minimum is the run least disturbed by other system activity. */
        for (uint64_t r = 0; r < reps; r++) {
            double start = now_seconds();
            sieve_status status = sieve_count(&algos[a], limit, &count);
            double elapsed = now_seconds() - start;
            if (status != SIEVE_OK)
                return fail_status(status);
            if (best < 0.0 || elapsed < best)
                best = elapsed;
        }
        printf("%-14s %14" PRIu64 " %12.4f  %s\n", algos[a].name, count, best,
               algos[a].description);
    }
    return 0;
}

/* Handles "[--algo NAME] N" for the count and list commands. */
static int parse_algo_args(int argc, char **argv, const sieve_algorithm **algo,
                           uint64_t *limit)
{
    int i = 0;
    *algo = sieve_find("segmented");
    if (argc >= 2 && strcmp(argv[0], "--algo") == 0) {
        *algo = sieve_find(argv[1]);
        if (!*algo) {
            fprintf(stderr, "error: unknown algorithm: %s\n", argv[1]);
            return 2;
        }
        i = 2;
    }
    if (argc - i != 1) {
        usage(stderr);
        return 2;
    }
    if (parse_u64(argv[i], limit) != 0)
        return fail_number(argv[i]);
    return 0;
}

static void print_prime(uint64_t prime, void *ctx)
{
    (void)ctx;
    printf("%" PRIu64 "\n", prime);
}

static int cmd_range(int argc, char **argv)
{
    uint64_t lo, hi;
    if (argc != 2) {
        usage(stderr);
        return 2;
    }
    if (parse_u64(argv[0], &lo) != 0)
        return fail_number(argv[0]);
    if (parse_u64(argv[1], &hi) != 0)
        return fail_number(argv[1]);
    sieve_status status = sieve_segmented_range(lo, hi, print_prime, NULL);
    return status == SIEVE_OK ? 0 : fail_status(status);
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        usage(stderr);
        return 2;
    }

    const char *cmd = argv[1];
    int rest = argc - 2;
    char **args = argv + 2;

    if (strcmp(cmd, "bench") == 0)
        return cmd_bench(rest, args);
    if (strcmp(cmd, "range") == 0)
        return cmd_range(rest, args);

    if (strcmp(cmd, "count") == 0 || strcmp(cmd, "list") == 0) {
        const sieve_algorithm *algo;
        uint64_t limit;
        int rc = parse_algo_args(rest, args, &algo, &limit);
        if (rc != 0)
            return rc;
        if (cmd[0] == 'l') {
            sieve_status status = algo->run(limit, print_prime, NULL);
            return status == SIEVE_OK ? 0 : fail_status(status);
        }
        uint64_t count;
        sieve_status status = sieve_count(algo, limit, &count);
        if (status != SIEVE_OK)
            return fail_status(status);
        printf("%" PRIu64 "\n", count);
        return 0;
    }

    if (strcmp(cmd, "algos") == 0) {
        size_t n;
        const sieve_algorithm *algos = sieve_algorithms(&n);
        for (size_t i = 0; i < n; i++)
            printf("%-14s %s\n", algos[i].name, algos[i].description);
        return 0;
    }

    if (strcmp(cmd, "-h") == 0 || strcmp(cmd, "--help") == 0) {
        usage(stdout);
        return 0;
    }

    usage(stderr);
    return 2;
}
