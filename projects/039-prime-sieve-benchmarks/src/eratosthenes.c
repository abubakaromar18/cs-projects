/*
 * eratosthenes.c - two versions of the Sieve of Eratosthenes.
 *
 * Both run in O(n log log n) time. They differ only in memory layout, which is
 * exactly what the benchmark is meant to expose:
 *   - the classic version spends one byte per integer;
 *   - the odd-only version spends one bit per odd integer, 16x less memory.
 */
#include "sieve.h"

#include <stdlib.h>

sieve_status sieve_eratosthenes(uint64_t limit, sieve_emit_fn emit, void *ctx)
{
    if (limit > SIEVE_MAX_DENSE)
        return SIEVE_ERANGE;
    if (limit < 2)
        return SIEVE_OK;

    /* composite[n] != 0 means n has been crossed off. */
    unsigned char *composite = calloc(limit + 1, 1);
    if (!composite)
        return SIEVE_ENOMEM;

    for (uint64_t i = 2; i * i <= limit; i++) {
        if (composite[i])
            continue;
        /* Smaller multiples were already crossed off by smaller factors. */
        for (uint64_t j = i * i; j <= limit; j += i)
            composite[j] = 1;
    }

    for (uint64_t n = 2; n <= limit; n++)
        if (!composite[n])
            emit(n, ctx);

    free(composite);
    return SIEVE_OK;
}

/* Bit index i represents the odd number 2i + 1. */
#define BIT_TEST(words, i) (((words)[(i) >> 6] >> ((i) & 63)) & 1u)
#define BIT_SET(words, i) ((words)[(i) >> 6] |= UINT64_C(1) << ((i) & 63))

sieve_status sieve_eratosthenes_odd(uint64_t limit, sieve_emit_fn emit, void *ctx)
{
    if (limit > SIEVE_MAX_DENSE)
        return SIEVE_ERANGE;
    if (limit < 2)
        return SIEVE_OK;

    emit(2, ctx);
    if (limit < 3)
        return SIEVE_OK;

    uint64_t bits = (limit - 1) / 2 + 1; /* odd numbers in [1, limit] */
    uint64_t *composite = calloc((bits >> 6) + 1, sizeof *composite);
    if (!composite)
        return SIEVE_ENOMEM;

    /* Index 0 is the number 1, so begin at index 1 (the number 3). */
    for (uint64_t i = 1; (2 * i + 1) * (2 * i + 1) <= limit; i++) {
        if (BIT_TEST(composite, i))
            continue;
        uint64_t p = 2 * i + 1;
        /*
         * p*p sits at index (p*p - 1) / 2. Stepping the index by p moves the
         * value by 2p, which visits only the odd multiples of p.
         */
        for (uint64_t j = (p * p - 1) / 2; j < bits; j += p)
            BIT_SET(composite, j);
    }

    for (uint64_t i = 1; i < bits; i++)
        if (!BIT_TEST(composite, i))
            emit(2 * i + 1, ctx);

    free(composite);
    return SIEVE_OK;
}
