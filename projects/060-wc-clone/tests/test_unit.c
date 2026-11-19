/*
 * test_unit.c - unit tests for the counter, option parser and formatter.
 *
 * A tiny assertion harness: each CHECK records a failure and keeps going,
 * so one run reports every broken case.
 */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "counts.h"
#include "options.h"
#include "report.h"

static int checks, failures;

#define CHECK(cond) do {                                               \
        checks++;                                                      \
        if (!(cond)) {                                                 \
            failures++;                                                \
            fprintf(stderr, "%s:%d: FAIL: %s\n", __FILE__, __LINE__, #cond); \
        }                                                              \
    } while (0)

#define CHECK_U64(got, want) do {                                      \
        uint64_t g_ = (got), w_ = (want);                              \
        checks++;                                                      \
        if (g_ != w_) {                                                \
            failures++;                                                \
            fprintf(stderr, "%s:%d: FAIL: %s = %" PRIu64 ", want %" PRIu64 "\n", \
                    __FILE__, __LINE__, #got, g_, w_);                 \
        }                                                              \
    } while (0)

static wc_counts cnt(const char *s) {
    return wc_count_buffer(s, strlen(s));
}

static void test_basic_counts(void) {
    wc_counts c = cnt("");
    CHECK_U64(c.lines, 0); CHECK_U64(c.words, 0); CHECK_U64(c.bytes, 0);

    c = cnt("hello world\n");
    CHECK_U64(c.lines, 1); CHECK_U64(c.words, 2); CHECK_U64(c.bytes, 12);
    CHECK_U64(c.chars, 12); CHECK_U64(c.max_line, 11);

    /* No trailing newline: zero lines, but the word still counts. */
    c = cnt("word");
    CHECK_U64(c.lines, 0); CHECK_U64(c.words, 1); CHECK_U64(c.max_line, 4);

    /* Runs of mixed whitespace separate words exactly once. */
    c = cnt("  a \t\t b\r\n\n\v\fc  ");
    CHECK_U64(c.words, 3); CHECK_U64(c.lines, 2);

    c = cnt("\n\n\n");
    CHECK_U64(c.lines, 3); CHECK_U64(c.words, 0); CHECK_U64(c.max_line, 0);
}

static void test_utf8(void) {
    /* "héllo wörld" : é and ö are 2 bytes each. */
    wc_counts c = cnt("h\xC3\xA9llo w\xC3\xB6rld\n");
    CHECK_U64(c.bytes, 14); CHECK_U64(c.chars, 12); CHECK_U64(c.words, 2);
    CHECK_U64(c.max_line, 11);

    /* 4-byte emoji is one character. */
    c = cnt("\xF0\x9F\x98\x80");
    CHECK_U64(c.bytes, 4); CHECK_U64(c.chars, 1); CHECK_U64(c.words, 1);

    /* A lone invalid lead byte still counts as a character. */
    c = cnt("\xFF");
    CHECK_U64(c.chars, 1);
}

static void test_max_line(void) {
    /* Tabs advance to the next multiple of 8. */
    CHECK_U64(cnt("\tx\n").max_line, 9);
    CHECK_U64(cnt("abc\tx\n").max_line, 9);
    CHECK_U64(cnt("abcdefgh\tx").max_line, 17);
    /* Widest of several lines, including the unterminated last one. */
    CHECK_U64(cnt("ab\nabcdef\nabc").max_line, 6);
    CHECK_U64(cnt("ab\nabc\nabcdefgh").max_line, 8);
    /* Carriage return restarts the column. */
    CHECK_U64(cnt("abcdef\rxy\n").max_line, 6);
}

/* Feeding byte-by-byte must equal feeding all at once: chunk boundaries
 * are invisible to the state machine. */
static void test_chunking(void) {
    const char *s = "The quick\tbr\xC3\xB8wn fox\r\njumps  over\n\n the lazy \xF0\x9F\x90\xB6";
    size_t len = strlen(s);
    wc_counts whole = wc_count_buffer(s, len);

    for (size_t chunk = 1; chunk <= len; chunk++) {
        wc_counter wc;
        wc_counter_init(&wc);
        for (size_t off = 0; off < len; off += chunk) {
            size_t n = len - off < chunk ? len - off : chunk;
            wc_counter_feed(&wc, (const unsigned char *)s + off, n);
        }
        wc_counts part = wc_counter_finish(&wc);
        CHECK(memcmp(&part, &whole, sizeof whole) == 0);
    }
    CHECK_U64(whole.words, 9);
    CHECK_U64(whole.lines, 3);
}

static void test_stream(void) {
    FILE *fp = tmpfile();
    CHECK(fp != NULL);
    if (!fp) return;
    /* Larger than the internal 64 KiB buffer to cross read boundaries. */
    for (int i = 0; i < 20000; i++)
        fputs("one two\n", fp);
    rewind(fp);
    wc_counts c;
    CHECK(wc_count_stream(fp, &c) == 0);
    CHECK_U64(c.lines, 20000); CHECK_U64(c.words, 40000);
    CHECK_U64(c.bytes, 160000);
    fclose(fp);
}

static void test_add(void) {
    wc_counts a = cnt("aaaa\n"), b = cnt("b b\nbbbbbbb\n");
    wc_counts_add(&a, &b);
    CHECK_U64(a.lines, 3); CHECK_U64(a.words, 4); CHECK_U64(a.bytes, 17);
    CHECK_U64(a.max_line, 7); /* max, not sum */
}

static wc_parse_result parse(wc_options *o, int argc, char **argv) {
    return wc_parse_args(argc, argv, o);
}

static void test_options(void) {
    wc_options o;

    char *a1[] = {"wc", NULL};
    CHECK(parse(&o, 1, a1) == PARSE_OK);
    CHECK(o.show == (WC_SHOW_LINES | WC_SHOW_WORDS | WC_SHOW_BYTES));
    CHECK(o.nfiles == 0);
    wc_options_free(&o);

    char *a2[] = {"wc", "-lw", "f1", "-", "--chars", "f2", NULL};
    CHECK(parse(&o, 6, a2) == PARSE_OK);
    CHECK(o.show == (WC_SHOW_LINES | WC_SHOW_WORDS | WC_SHOW_CHARS));
    CHECK(o.nfiles == 3);
    CHECK(o.nfiles == 3 && strcmp(o.files[1], "-") == 0);
    wc_options_free(&o);

    char *a3[] = {"wc", "--", "-l", NULL};
    CHECK(parse(&o, 3, a3) == PARSE_OK);
    CHECK(o.nfiles == 1 && strcmp(o.files[0], "-l") == 0);
    wc_options_free(&o);

    char *a4[] = {"wc", "-x", NULL};
    CHECK(parse(&o, 2, a4) == PARSE_ERROR);
    CHECK(strstr(o.err, "'x'") != NULL);
    wc_options_free(&o);

    char *a5[] = {"wc", "--total=only", "-L", NULL};
    CHECK(parse(&o, 3, a5) == PARSE_OK);
    CHECK(o.total == TOTAL_ONLY && o.show == WC_SHOW_MAXLINE);
    wc_options_free(&o);

    char *a6[] = {"wc", "--total=sometimes", NULL};
    CHECK(parse(&o, 2, a6) == PARSE_ERROR);
    wc_options_free(&o);

    char *a7[] = {"wc", "--help", NULL};
    CHECK(parse(&o, 2, a7) == PARSE_HELP);
    wc_options_free(&o);
}

static void test_report(void) {
    CHECK(wc_digits(0) == 1);
    CHECK(wc_digits(9) == 1);
    CHECK(wc_digits(10) == 2);
    CHECK(wc_digits(1234567) == 7);

    char buf[128] = {0};
    FILE *fp = tmpfile();
    if (!fp) { CHECK(0); return; }
    wc_counts c = cnt("hi there\nyou\n");
    wc_print_row(fp, &c, WC_SHOW_LINES | WC_SHOW_WORDS | WC_SHOW_BYTES, 3, "f.txt");
    rewind(fp);
    CHECK(fgets(buf, sizeof buf, fp) != NULL);
    CHECK(strcmp(buf, "  2   3  13 f.txt\n") == 0);
    fclose(fp);
}

int main(void) {
    test_basic_counts();
    test_utf8();
    test_max_line();
    test_chunking();
    test_stream();
    test_add();
    test_options();
    test_report();

    printf("%d checks, %d failures\n", checks, failures);
    return failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
