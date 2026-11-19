/*
 * counts.h - streaming line/word/byte/char counter.
 *
 * The counter is a small state machine that is fed arbitrary chunks of
 * bytes. Chunk boundaries never matter: a word or a UTF-8 sequence split
 * across two reads is counted exactly once. That property is what lets
 * main.c read files with a fixed-size buffer.
 */
#ifndef WC_COUNTS_H
#define WC_COUNTS_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

typedef struct {
    uint64_t lines;     /* number of '\n' bytes, like POSIX wc       */
    uint64_t words;     /* maximal runs of non-whitespace bytes      */
    uint64_t bytes;     /* raw byte count                            */
    uint64_t chars;     /* UTF-8 code points (lead bytes + invalid)  */
    uint64_t max_line;  /* widest line in display columns (tab = 8)  */
} wc_counts;

typedef struct {
    wc_counts c;
    int in_word;        /* 1 if the previous byte was part of a word */
    uint64_t col;       /* display column of the current line        */
} wc_counter;

/* Reset a counter to zero. */
void wc_counter_init(wc_counter *wc);

/* Feed len bytes. May be called any number of times. */
void wc_counter_feed(wc_counter *wc, const unsigned char *buf, size_t len);

/* Finish counting (folds the last unterminated line into max_line). */
wc_counts wc_counter_finish(wc_counter *wc);

/* Count everything from a stream. Returns 0 on success, -1 on read error. */
int wc_count_stream(FILE *fp, wc_counts *out);

/* Convenience: count an in-memory buffer in one call. */
wc_counts wc_count_buffer(const char *buf, size_t len);

/* Add b into a (used for the "total" line). */
void wc_counts_add(wc_counts *a, const wc_counts *b);

#endif
