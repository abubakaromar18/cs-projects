/*
 * atkin.c - the Sieve of Atkin (Atkin & Bernstein, 2004).
 *
 * Instead of crossing off multiples, Atkin uses the number of solutions to
 * three binary quadratic forms. For a squarefree n > 3:
 *
 *   n mod 12 in {1, 5}: prime iff 4x^2 + y^2 = n has an odd solution count
 *   n mod 12 == 7:      prime iff 3x^2 + y^2 = n has an odd solution count
 *   n mod 12 == 11:     prime iff 3x^2 - y^2 = n (x > y) has an odd count
 *
 * Toggling a flag per solution tracks the parity. A final pass removes numbers
 * that are not squarefree. Multiples of 2 and 3 never satisfy these residues,
 * so 2 and 3 are emitted directly.
 */
#include "sieve.h"

#include <stdlib.h>

sieve_status sieve_atkin(uint64_t limit, sieve_emit_fn emit, void *ctx)
{
    if (limit > SIEVE_MAX_DENSE)
        return SIEVE_ERANGE;
    if (limit < 2)
        return SIEVE_OK;

    emit(2, ctx);
    if (limit < 3)
        return SIEVE_OK;
    emit(3, ctx);
    if (limit < 5)
        return SIEVE_OK;

    unsigned char *candidate = calloc(limit + 1, 1);
    if (!candidate)
        return SIEVE_ENOMEM;

    /* 4x^2 + y^2 */
    for (uint64_t x = 1; 4 * x * x < limit; x++) {
        uint64_t base = 4 * x * x;
        for (uint64_t y = 1; base + y * y <= limit; y++) {
            uint64_t n = base + y * y;
            unsigned r = (unsigned)(n % 12);
            if (r == 1 || r == 5)
                candidate[n] ^= 1;
        }
    }

    /* 3x^2 + y^2 */
    for (uint64_t x = 1; 3 * x * x < limit; x++) {
        uint64_t base = 3 * x * x;
        for (uint64_t y = 1; base + y * y <= limit; y++) {
            uint64_t n = base + y * y;
            if (n % 12 == 7)
                candidate[n] ^= 1;
        }
    }

    /*
     * 3x^2 - y^2 with x > y. The smallest value for a given x occurs at
     * y = x - 1, namely 2x^2 + 2x - 1, which bounds the outer loop. Walking y
     * downward makes n grow, so the inner loop can stop once n passes limit.
     */
    for (uint64_t x = 2; 2 * x * x + 2 * x - 1 <= limit; x++) {
        uint64_t base = 3 * x * x;
        for (uint64_t y = x - 1; y >= 1; y--) {
            uint64_t n = base - y * y;
            if (n > limit)
                break;
            if (n % 12 == 11)
                candidate[n] ^= 1;
        }
    }

    /* Remove numbers divisible by the square of a prime. */
    for (uint64_t r = 5; r * r <= limit; r++) {
        if (!candidate[r])
            continue;
        uint64_t square = r * r;
        for (uint64_t k = square; k <= limit; k += square)
            candidate[k] = 0;
    }

    for (uint64_t n = 5; n <= limit; n++)
        if (candidate[n])
            emit(n, ctx);

    free(candidate);
    return SIEVE_OK;
}
