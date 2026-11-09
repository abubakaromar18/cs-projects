/*
 * segmented.c - a segmented Sieve of Eratosthenes.
 *
 * Primes up to sqrt(hi) are found first. The target range is then processed in
 * blocks small enough to fit in the L1 cache, so memory use is O(sqrt(hi))
 * rather than O(hi), and the range need not start at zero.
 */
#include "sieve.h"

#include <stdlib.h>
#include <string.h>

/* Bytes per segment. Each byte is one odd number, so a block spans 64 KiB. */
#define SEGMENT_BYTES 32768u

typedef struct {
    uint32_t *items;
    size_t count;
    size_t capacity;
    int failed;
} base_primes;

static void base_push(uint64_t prime, void *ctx)
{
    base_primes *b = ctx;
    if (b->failed)
        return;
    if (b->count == b->capacity) {
        size_t cap = b->capacity ? b->capacity * 2 : 256;
        uint32_t *grown = realloc(b->items, cap * sizeof *grown);
        if (!grown) {
            b->failed = 1;
            return;
        }
        b->items = grown;
        b->capacity = cap;
    }
    b->items[b->count++] = (uint32_t)prime;
}

/* First odd multiple of p that is >= max(p*p, start); start is odd. */
static uint64_t first_multiple(uint64_t p, uint64_t start)
{
    uint64_t square = p * p;
    if (square >= start)
        return square; /* p is odd, so p*p is odd */
    uint64_t m = start + (p - start % p) % p;
    return (m % 2 == 0) ? m + p : m;
}

sieve_status sieve_segmented_range(uint64_t lo, uint64_t hi,
                                   sieve_emit_fn emit, void *ctx)
{
    if (hi > SIEVE_MAX_SEGMENTED)
        return SIEVE_ERANGE;
    if (lo > hi || hi < 2)
        return SIEVE_OK;

    if (lo <= 2)
        emit(2, ctx);

    /* From here on only odd numbers >= 3 are considered. */
    uint64_t start = lo <= 3 ? 3 : (lo | 1);
    if (start > hi)
        return SIEVE_OK;

    base_primes base = {0};
    sieve_status status = sieve_eratosthenes_odd(sieve_isqrt(hi), base_push, &base);
    if (status != SIEVE_OK || base.failed) {
        free(base.items);
        return status != SIEVE_OK ? status : SIEVE_ENOMEM;
    }

    /* next[i] is the next odd multiple to cross off for base prime i. */
    uint64_t *next = malloc((base.count + 1) * sizeof *next);
    unsigned char *segment = malloc(SEGMENT_BYTES);
    if (!next || !segment) {
        free(base.items);
        free(next);
        free(segment);
        return SIEVE_ENOMEM;
    }

    /* Index 0 of the base list is 2; even numbers are never represented. */
    for (size_t i = 1; i < base.count; i++)
        next[i] = first_multiple(base.items[i], start);

    for (uint64_t seg_lo = start; seg_lo <= hi; seg_lo += 2ull * SEGMENT_BYTES) {
        uint64_t seg_hi = seg_lo + 2ull * (SEGMENT_BYTES - 1);
        if (seg_hi > hi)
            seg_hi = hi;
        size_t len = (size_t)((seg_hi - seg_lo) / 2) + 1;
        memset(segment, 0, len);

        for (size_t i = 1; i < base.count; i++) {
            uint64_t p = base.items[i];
            uint64_t m = next[i];
            /* Each step of 2p lands on the next odd multiple. */
            for (; m <= seg_hi; m += 2 * p)
                segment[(m - seg_lo) / 2] = 1;
            next[i] = m;
        }

        for (size_t i = 0; i < len; i++)
            if (!segment[i])
                emit(seg_lo + 2 * (uint64_t)i, ctx);
    }

    free(base.items);
    free(next);
    free(segment);
    return SIEVE_OK;
}

sieve_status sieve_segmented(uint64_t limit, sieve_emit_fn emit, void *ctx)
{
    return sieve_segmented_range(0, limit, emit, ctx);
}
