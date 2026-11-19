/*
 * counts.c - the counting state machine.
 *
 * Word rule: a word is a maximal run of bytes that are not ASCII
 * whitespace (space, \t, \n, \v, \f, \r). We test bytes ourselves instead
 * of calling isspace() so results do not depend on the process locale.
 *
 * Character rule: in UTF-8 every code point starts with a byte that is NOT
 * of the form 10xxxxxx. Counting the non-continuation bytes therefore
 * counts code points, and a stray invalid byte still counts as one
 * character, which is a simple, total definition.
 *
 * Max line length counts display columns: printable code points are one
 * column wide, a tab advances to the next multiple of 8, and \r or \f
 * start a fresh line segment (as GNU wc does).
 */
#include "counts.h"

#include <string.h>

#define TAB_WIDTH 8
#define BUF_SIZE  (64 * 1024)

static int is_ws(unsigned char ch) {
    return ch == ' ' || (ch >= '\t' && ch <= '\r');
}

static int is_utf8_continuation(unsigned char ch) {
    return (ch & 0xC0) == 0x80;
}

void wc_counter_init(wc_counter *wc) {
    memset(wc, 0, sizeof *wc);
}

/* Close the current line segment, updating the widest-line record. */
static void end_segment(wc_counter *wc) {
    if (wc->col > wc->c.max_line)
        wc->c.max_line = wc->col;
    wc->col = 0;
}

void wc_counter_feed(wc_counter *wc, const unsigned char *buf, size_t len) {
    wc->c.bytes += len;

    for (size_t i = 0; i < len; i++) {
        unsigned char ch = buf[i];

        /* Continuation bytes belong to a code point already counted,
         * and never change word or line state. */
        if (is_utf8_continuation(ch))
            continue;
        wc->c.chars++;

        if (!is_ws(ch)) {
            if (!wc->in_word) {
                wc->in_word = 1;
                wc->c.words++;
            }
            /* Control characters take no columns; everything else one. */
            if (ch >= 0x20 && ch != 0x7F)
                wc->col++;
            continue;
        }

        wc->in_word = 0;
        switch (ch) {
        case '\n':
            wc->c.lines++;
            end_segment(wc);
            break;
        case '\r':
        case '\f':
            end_segment(wc);
            break;
        case '\t':
            wc->col += TAB_WIDTH - (wc->col % TAB_WIDTH);
            break;
        case ' ':
            wc->col++;
            break;
        default: /* \v has no width */
            break;
        }
    }
}

wc_counts wc_counter_finish(wc_counter *wc) {
    end_segment(wc);
    return wc->c;
}

int wc_count_stream(FILE *fp, wc_counts *out) {
    static unsigned char buf[BUF_SIZE];
    wc_counter wc;
    size_t n;

    wc_counter_init(&wc);
    while ((n = fread(buf, 1, sizeof buf, fp)) > 0)
        wc_counter_feed(&wc, buf, n);

    *out = wc_counter_finish(&wc);
    return ferror(fp) ? -1 : 0;
}

wc_counts wc_count_buffer(const char *buf, size_t len) {
    wc_counter wc;
    wc_counter_init(&wc);
    wc_counter_feed(&wc, (const unsigned char *)buf, len);
    return wc_counter_finish(&wc);
}

void wc_counts_add(wc_counts *a, const wc_counts *b) {
    a->lines += b->lines;
    a->words += b->words;
    a->bytes += b->bytes;
    a->chars += b->chars;
    /* The total's max line is the max over files, not a sum. */
    if (b->max_line > a->max_line)
        a->max_line = b->max_line;
}
