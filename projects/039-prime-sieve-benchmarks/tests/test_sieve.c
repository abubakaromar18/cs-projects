/*
 * test_sieve.c - dependency-free tests for the sieve library.
 *
 * Exhaustively compares every algorithm with trial division at small limits
 * (where the edge cases are), then checks published values of pi(x).
 */
#include "sieve.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

static int failures = 0;
static int checks = 0;

#define CHECK(cond, ...)                                   \
    do {                                                   \
        checks++;                                          \
        if (!(cond)) {                                     \
            failures++;                                    \
            printf("FAIL %s:%d: ", __FILE__, __LINE__);    \
            printf(__VA_ARGS__);                           \
            putchar('\n');                                 \
        }                                                  \
    } while (0)

static int is_prime_slow(uint64_t n)
{
    if (n < 2)
        return 0;
    for (uint64_t d = 2; d * d <= n; d++)
        if (n % d == 0)
            return 0;
    return 1;
}

/* Verifies a list is exactly the primes in [lo, hi], in ascending order. */
static void check_exact(const char *name, const prime_list *list, uint64_t lo,
                        uint64_t hi)
{
    size_t idx = 0;
    for (uint64_t n = lo; n <= hi; n++) {
        if (!is_prime_slow(n))
            continue;
        CHECK(idx < list->count && list->items[idx] == n,
              "%s [%" PRIu64 ", %" PRIu64 "]: missing or misplaced %" PRIu64,
              name, lo, hi, n);
        idx++;
    }
    CHECK(idx == list->count, "%s [%" PRIu64 ", %" PRIu64 "]: %zu extra primes",
          name, lo, hi, list->count - idx);
}

static void test_every_small_limit(void)
{
    size_t n;
    const sieve_algorithm *algos = sieve_algorithms(&n);
    for (size_t a = 0; a < n; a++) {
        for (uint64_t limit = 0; limit <= 2000; limit++) {
            prime_list list;
            sieve_status status = sieve_collect(&algos[a], limit, &list);
            CHECK(status == SIEVE_OK, "%s failed", algos[a].name);
            if (status == SIEVE_OK) {
                check_exact(algos[a].name, &list, 0, limit);
                prime_list_free(&list);
            }
        }
    }
}

/* Crosses segment boundaries, including the first one at 3 + 65536. */
static void test_algorithms_agree_at_segment_boundaries(void)
{
    static const uint64_t limits[] = {65537, 65538, 65539, 65540, 131073, 131075, 200000};
    const sieve_algorithm *reference = sieve_find("eratosthenes");
    size_t n;
    const sieve_algorithm *algos = sieve_algorithms(&n);

    for (size_t l = 0; l < sizeof limits / sizeof limits[0]; l++) {
        uint64_t expected;
        CHECK(sieve_count(reference, limits[l], &expected) == SIEVE_OK, "reference");
        for (size_t a = 0; a < n; a++) {
            uint64_t got = 0;
            CHECK(sieve_count(&algos[a], limits[l], &got) == SIEVE_OK, "%s", algos[a].name);
            CHECK(got == expected, "%s at %" PRIu64 ": %" PRIu64 " != %" PRIu64,
                  algos[a].name, limits[l], got, expected);
        }
    }
}

static void test_known_prime_counts(void)
{
    static const struct {
        uint64_t x, pi;
    } known[] = {
        {10, 4},        {100, 25},        {1000, 168},        {10000, 1229},
        {100000, 9592}, {1000000, 78498}, {10000000, 664579},
    };
    size_t n;
    const sieve_algorithm *algos = sieve_algorithms(&n);
    for (size_t a = 0; a < n; a++) {
        for (size_t k = 0; k < sizeof known / sizeof known[0]; k++) {
            uint64_t got = 0;
            CHECK(sieve_count(&algos[a], known[k].x, &got) == SIEVE_OK, "%s", algos[a].name);
            CHECK(got == known[k].pi, "%s: pi(%" PRIu64 ") = %" PRIu64, algos[a].name,
                  known[k].x, got);
        }
    }
}

static void test_segmented_billion(void)
{
    uint64_t got = 0;
    CHECK(sieve_count(sieve_find("segmented"), 1000000000, &got) == SIEVE_OK, "run");
    CHECK(got == 50847534, "pi(10^9) = %" PRIu64, got);
}

static void test_ranges(void)
{
    static const struct {
        uint64_t lo, hi;
    } ranges[] = {
        {0, 0},     {0, 1},       {1, 2},           {2, 2},
        {2, 3},     {3, 3},       {4, 4},           {8, 10},
        {9, 11},    {14, 16},     {7, 7},           {100, 200},
        {1000000000, 1000001000}, {65530, 65550},   {999999000, 1000000100},
    };
    for (size_t r = 0; r < sizeof ranges / sizeof ranges[0]; r++) {
        prime_list list = {0};
        sieve_status status =
            sieve_segmented_range(ranges[r].lo, ranges[r].hi, prime_list_push, &list);
        CHECK(status == SIEVE_OK, "range status");
        check_exact("range", &list, ranges[r].lo, ranges[r].hi);
        prime_list_free(&list);
    }
}

static void test_range_beyond_32_bits(void)
{
    /* The first primes after 10^12 are 10^12+39 and 10^12+61. */
    uint64_t base = UINT64_C(1000000000000);
    prime_list list = {0};
    CHECK(sieve_segmented_range(base, base + 100, prime_list_push, &list) == SIEVE_OK,
          "status");
    CHECK(list.count >= 2 && list.items[0] == base + 39 && list.items[1] == base + 61,
          "unexpected primes after 10^12");
    prime_list_free(&list);
}

static void test_invalid_input(void)
{
    prime_list list = {0};
    CHECK(sieve_segmented_range(100, 50, prime_list_push, &list) == SIEVE_OK, "lo > hi");
    CHECK(list.count == 0, "lo > hi should be empty");

    CHECK(sieve_segmented_range(0, SIEVE_MAX_SEGMENTED + 1, prime_list_push, &list) ==
              SIEVE_ERANGE, "segmented bound");

    size_t n;
    const sieve_algorithm *algos = sieve_algorithms(&n);
    for (size_t a = 0; a < n; a++) {
        if (algos[a].run == sieve_segmented)
            continue;
        uint64_t count;
        CHECK(sieve_count(&algos[a], SIEVE_MAX_DENSE + 1, &count) == SIEVE_ERANGE,
              "%s bound", algos[a].name);
    }
    CHECK(sieve_find("no-such-algorithm") == NULL, "unknown name");
}

static void test_isqrt(void)
{
    static const struct {
        uint64_t n, root;
    } cases[] = {
        {0, 0},
        {1, 1},
        {2, 1},
        {3, 1},
        {4, 2},
        {15, 3},
        {16, 4},
        {UINT64_C(999999999999), 999999},
        {UINT64_C(1000000000000), 1000000},
        {UINT64_C(18446744065119617025), UINT64_C(4294967295)},
        {UINT64_MAX, UINT64_C(4294967295)},
    };
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        uint64_t got = sieve_isqrt(cases[i].n);
        CHECK(got == cases[i].root, "isqrt(%" PRIu64 ") = %" PRIu64, cases[i].n, got);
    }
}

int main(void)
{
    test_every_small_limit();
    test_algorithms_agree_at_segment_boundaries();
    test_known_prime_counts();
    test_segmented_billion();
    test_ranges();
    test_range_beyond_32_bits();
    test_invalid_input();
    test_isqrt();

    printf("%d checks, %d failures\n", checks, failures);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
