/*
 * test_util.h - A tiny assertion framework (no external dependencies).
 */
#ifndef TEST_UTIL_H
#define TEST_UTIL_H

#include <stdio.h>
#include <string.h>

static int tests_run = 0;
static int tests_failed = 0;
static int current_failed = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "    FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            current_failed = 1;                                              \
        }                                                                    \
    } while (0)

#define CHECK_EQ(a, b) CHECK((a) == (b))

/* Compare list contents against an expected int array. */
#define CHECK_ARRAY(to_array_fn, list, ...)                                  \
    do {                                                                     \
        int expected_[] = {__VA_ARGS__};                                     \
        size_t n_ = sizeof expected_ / sizeof expected_[0];                  \
        int got_[64];                                                        \
        size_t m_ = to_array_fn(list, got_, 64);                             \
        CHECK(m_ == n_ && memcmp(got_, expected_, n_ * sizeof(int)) == 0);   \
    } while (0)

#define RUN_TEST(fn)                                                         \
    do {                                                                     \
        current_failed = 0;                                                  \
        fn();                                                                \
        tests_run++;                                                         \
        if (current_failed) tests_failed++;                                  \
        printf("  [%s] %s\n", current_failed ? "FAIL" : " OK ", #fn);        \
    } while (0)

#define TEST_SUMMARY(name)                                                   \
    (printf("%s: %d/%d passed\n", name, tests_run - tests_failed, tests_run), \
     tests_failed ? 1 : 0)

#endif /* TEST_UTIL_H */
