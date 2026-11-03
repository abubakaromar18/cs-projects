/*
 * test_bf.c - Unit and differential tests for the compiler and VM.
 *
 * The key property: every optimization level must produce exactly the same
 * output and final status as the naive -O0 interpreter. Besides hand-picked
 * programs, a fuzz test generates thousands of random bracket-balanced
 * programs and checks the levels agree.
 */
#include "bf.h"

#include <stdlib.h>
#include <string.h>

static int tests_run, tests_failed, current_failed;

#define CHECK(cond)                                                           \
    do {                                                                      \
        if (!(cond)) {                                                        \
            fprintf(stderr, "    FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            current_failed = 1;                                               \
        }                                                                     \
    } while (0)

#define RUN_TEST(fn)                                                          \
    do {                                                                      \
        current_failed = 0;                                                   \
        tests_run++;                                                          \
        fn();                                                                 \
        printf("  %-40s %s\n", #fn, current_failed ? "FAIL" : "ok");         \
        tests_failed += current_failed;                                       \
    } while (0)

/* --------------------------------------------------------------- helpers -- */

typedef struct {
    bf_status status;
    char out[4096];
    size_t out_len;
    bf_stats stats;
    size_t prog_len;
} result;

/* Compile and run `src` at `level` with in-memory I/O. */
static result run_with(const char *src, int level, const char *input,
                       bf_config cfg)
{
    result r;
    memset(&r, 0, sizeof r);
    bf_program p;
    bf_error err;
    r.status = bf_compile(src, strlen(src), level, &p, &err);
    if (r.status != BF_OK)
        return r;
    r.prog_len = p.len;
    bf_mem_io m = {(const unsigned char *)(input ? input : ""),
                   input ? strlen(input) : 0, 0,
                   (unsigned char *)r.out, sizeof r.out - 1, 0};
    r.status = bf_run(&p, &cfg, bf_io_memory(&m), &r.stats, &err);
    r.out_len = m.out_len;
    r.out[r.out_len] = '\0';
    bf_program_free(&p);
    return r;
}

static result run(const char *src, int level, const char *input)
{
    return run_with(src, level, input, bf_default_config());
}

static const char *HELLO =
    "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>."
    "<-.<.+++.------.--------.>>+.>++.";

/* ----------------------------------------------------------------- tests -- */

static void test_hello_world_all_levels(void)
{
    for (int lvl = 0; lvl <= 2; lvl++) {
        result r = run(HELLO, lvl, NULL);
        CHECK(r.status == BF_OK);
        CHECK(strcmp(r.out, "Hello World!\n") == 0);
    }
}

static void test_comments_are_ignored(void)
{
    result r = run("This prints A: ++++++++[>++++++++<-]>+. (65) done", 2, NULL);
    CHECK(r.status == BF_OK);
    CHECK(strcmp(r.out, "A") == 0);
}

static void test_cat_echoes_input(void)
{
    /* With EOF -> 0 this is the canonical cat program. */
    result r = run(",[.,]", 2, "copy me!");
    CHECK(r.status == BF_OK);
    CHECK(strcmp(r.out, "copy me!") == 0);
}

static void test_cell_wraps(void)
{
    /* 0 - 1 = 255; +1 more wraps back to 0 so the loop is skipped. */
    result r = run("-[+[>+++++++++++++++++++++++++++++++++.<-]]", 0, NULL);
    CHECK(r.status == BF_OK);
    CHECK(r.out_len == 0);
    /* 256 increments == 0 */
    char buf[300];
    memset(buf, '+', 256);
    strcpy(buf + 256, "[.]");
    r = run(buf, 1, NULL);
    CHECK(r.status == BF_OK && r.out_len == 0);
}

static void test_unmatched_brackets(void)
{
    bf_program p;
    bf_error err;
    CHECK(bf_compile("++\n+]", 5, 2, &p, &err) == BF_ERR_UNMATCHED_CLOSE);
    CHECK(err.line == 2 && err.col == 2);
    CHECK(bf_compile("[[]\n", 4, 2, &p, &err) == BF_ERR_UNMATCHED_OPEN);
    CHECK(err.line == 1 && err.col == 1);
    CHECK(bf_compile("[ok] [x", 7, 0, &p, &err) == BF_ERR_UNMATCHED_OPEN);
    CHECK(err.col == 6);
}

static void test_tape_bounds(void)
{
    result r = run("<", 0, NULL);
    CHECK(r.status == BF_ERR_TAPE_BOUNDS);
    bf_config cfg = bf_default_config();
    cfg.tape_size = 4;
    r = run_with(">>>.>", 1, NULL, cfg);
    CHECK(r.status == BF_ERR_TAPE_BOUNDS);
    CHECK(r.out_len == 1); /* the '.' ran before the fault */
    r = run_with("+[>+]", 2, NULL, cfg); /* runs off the right edge */
    CHECK(r.status == BF_ERR_TAPE_BOUNDS);
}

static void test_scan_bounds(void)
{
    bf_config cfg = bf_default_config();
    cfg.tape_size = 8;
    /* All cells non-zero, so [>] scans off the end of the tape. */
    result r = run_with("+>+>+>+>+>+>+>+<<<<<<<[>]", 2, NULL, cfg);
    CHECK(r.status == BF_ERR_TAPE_BOUNDS);
}

static void test_eof_modes(void)
{
    bf_config cfg = bf_default_config();
    const char *prog = "+++++,."; /* cell = 5, read at EOF, print */
    cfg.eof = BF_EOF_ZERO;
    result r = run_with(prog, 2, NULL, cfg);
    CHECK(r.out_len == 1 && (unsigned char)r.out[0] == 0);
    cfg.eof = BF_EOF_MINUS_ONE;
    r = run_with(prog, 2, NULL, cfg);
    CHECK(r.out_len == 1 && (unsigned char)r.out[0] == 255);
    cfg.eof = BF_EOF_UNCHANGED;
    r = run_with(prog, 2, NULL, cfg);
    CHECK(r.out_len == 1 && (unsigned char)r.out[0] == 5);
}

static void test_step_limit(void)
{
    bf_config cfg = bf_default_config();
    cfg.max_steps = 1000;
    result r = run_with("+[]", 2, NULL, cfg);
    CHECK(r.status == BF_ERR_STEP_LIMIT);
    CHECK(r.stats.steps == 1000);
}

static void test_output_overflow_reports_io_error(void)
{
    bf_program p;
    bf_compile("+[.]", 4, 0, &p, NULL);
    unsigned char out[3];
    bf_mem_io m = {NULL, 0, 0, out, sizeof out, 0};
    bf_error err;
    CHECK(bf_run(&p, NULL, bf_io_memory(&m), NULL, &err) == BF_ERR_IO);
    CHECK(m.out_len == 3);
    bf_program_free(&p);
}

/* ---- IR shape: check what the optimizer actually emits ---- */

static void test_run_length_folding(void)
{
    bf_program p;
    bf_compile("+++--->>><<+++++>", 17, 1, &p, NULL);
    /* "+++---" cancels to nothing; ">>><<" -> MOVE 1; "+++++" -> ADD 5; ">" */
    CHECK(p.len == 3);
    CHECK(p.ops[0].kind == BF_OP_MOVE && p.ops[0].arg == 1);
    CHECK(p.ops[1].kind == BF_OP_ADD && p.ops[1].arg == 5);
    CHECK(p.ops[2].kind == BF_OP_MOVE && p.ops[2].arg == 1);
    bf_program_free(&p);

    bf_compile("+++", 3, 0, &p, NULL);
    CHECK(p.len == 3); /* level 0 does no folding */
    bf_program_free(&p);
}

static void test_clear_and_scan_idioms(void)
{
    bf_program p;
    bf_compile("[-][+][<<]", 10, 2, &p, NULL);
    CHECK(p.len == 3);
    CHECK(p.ops[0].kind == BF_OP_SET && p.ops[0].arg == 0);
    CHECK(p.ops[1].kind == BF_OP_SET && p.ops[1].arg == 0);
    CHECK(p.ops[2].kind == BF_OP_SCAN && p.ops[2].arg == -2);
    bf_program_free(&p);
}

static void test_multiply_idiom(void)
{
    bf_program p;
    const char *src = "[->+++>>--<<<]";
    bf_compile(src, strlen(src), 2, &p, NULL);
    CHECK(p.len == 3);
    CHECK(p.ops[0].kind == BF_OP_MULADD && p.ops[0].offset == 1 && p.ops[0].arg == 3);
    CHECK(p.ops[1].kind == BF_OP_MULADD && p.ops[1].offset == 3 && p.ops[1].arg == 254);
    CHECK(p.ops[2].kind == BF_OP_SET);
    bf_program_free(&p);

    /* 7 * 9 = 63 = '?', computed by a multiply loop. */
    result r = run("+++++++[>+++++++++<-]>.", 2, NULL);
    CHECK(strcmp(r.out, "?") == 0);
    CHECK(r.prog_len == 5); /* ADD 7, MULADD, SET, MOVE, OUT */
}

static void test_loops_with_io_not_rewritten(void)
{
    bf_program p;
    bf_compile("[-.]", 4, 2, &p, NULL);
    CHECK(p.len == 4 && p.ops[0].kind == BF_OP_JZ);
    CHECK(p.ops[0].arg == 3 && p.ops[3].arg == 0); /* jumps linked */
    bf_program_free(&p);
}

static void test_optimizer_reduces_steps(void)
{
    result naive = run(HELLO, 0, NULL);
    result opt = run(HELLO, 2, NULL);
    CHECK(naive.status == BF_OK && opt.status == BF_OK);
    CHECK(opt.stats.steps * 3 < naive.stats.steps);
    CHECK(opt.prog_len < naive.prog_len);
}

/* ---- differential fuzzing: -O1 and -O2 must match -O0 exactly ---- */

static unsigned rng_state = 12345;
static unsigned rng(void)
{
    rng_state = rng_state * 1103515245u + 12345u;
    return (rng_state >> 16) & 0x7FFF;
}

/* Generate a random balanced program biased toward optimizable idioms. */
static void gen(char *buf, size_t cap)
{
    static const char *pieces[] = {
        "+", "-", ">", "<", "+++", "--", ">>", "<<", ".", ",",
        "[-]", "[+]", "[>]", "[<]", "[->+<]", "[->++>+++<<]", "[+<-->]",
        "[->-<]", "[<<+>>-]",
    };
    /* Start in the middle of the tape so '<' does not fault immediately. */
    size_t n = 0, depth = 0;
    memset(buf, '>', 16);
    n = 16;
    size_t target = 10 + rng() % 60;
    while (n + 16 < cap && target--) {
        unsigned k = rng() % 24;
        const char *s;
        if (k < 19) s = pieces[k];
        else if (k < 22) { s = "["; depth++; }
        else if (depth) { s = "]"; depth--; }
        else s = "+";
        size_t l = strlen(s);
        memcpy(buf + n, s, l);
        n += l;
    }
    while (depth--) buf[n++] = ']';
    buf[n] = '\0';
}

static void test_fuzz_levels_agree(void)
{
    char src[512];
    bf_config cfg = bf_default_config();
    cfg.tape_size = 32; /* small tape so bounds errors are exercised too */
    cfg.max_steps = 20000;
    int compared = 0, mismatches = 0;

    for (int i = 0; i < 5000; i++) {
        gen(src, sizeof src);
        result a = run_with(src, 0, "fuzz input", cfg);
        /*
         * Two documented, intentional differences are skipped:
         *  - step limits: optimized code executes fewer steps;
         *  - tape faults: folding "<<>>" checks only the net movement, so a
         *    transient excursion off the tape faults at -O0 but not above.
         * Whenever -O0 succeeds, every level must match it exactly (which
         * also proves optimized code never faults where -O0 does not).
         */
        if (a.status != BF_OK)
            continue;
        for (int lvl = 1; lvl <= 2; lvl++) {
            result b = run_with(src, lvl, "fuzz input", cfg);
            compared++;
            if (a.status != b.status || a.out_len != b.out_len ||
                memcmp(a.out, b.out, a.out_len) != 0 || a.stats.ptr != b.stats.ptr) {
                if (mismatches++ < 3)
                    fprintf(stderr, "    mismatch at -O%d: %s\n", lvl, src);
            }
        }
    }
    CHECK(mismatches == 0);
    printf("    (%d differential comparisons)\n", compared);
    CHECK(compared > 2000);
}

int main(void)
{
    puts("brainfuck tests");
    RUN_TEST(test_hello_world_all_levels);
    RUN_TEST(test_comments_are_ignored);
    RUN_TEST(test_cat_echoes_input);
    RUN_TEST(test_cell_wraps);
    RUN_TEST(test_unmatched_brackets);
    RUN_TEST(test_tape_bounds);
    RUN_TEST(test_scan_bounds);
    RUN_TEST(test_eof_modes);
    RUN_TEST(test_step_limit);
    RUN_TEST(test_output_overflow_reports_io_error);
    RUN_TEST(test_run_length_folding);
    RUN_TEST(test_clear_and_scan_idioms);
    RUN_TEST(test_multiply_idiom);
    RUN_TEST(test_loops_with_io_not_rewritten);
    RUN_TEST(test_optimizer_reduces_steps);
    RUN_TEST(test_fuzz_levels_agree);
    printf("%d tests, %d failed\n", tests_run, tests_failed);
    return tests_failed ? 1 : 0;
}
