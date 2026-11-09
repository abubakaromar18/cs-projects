/*
 * sieve.c - algorithm registry and helpers shared by the sieves.
 */
#include "sieve.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

static const sieve_algorithm ALGORITHMS[] = {
    {"eratosthenes", "classic, one byte per integer", sieve_eratosthenes},
    {"odd-bitset", "Eratosthenes, one bit per odd integer", sieve_eratosthenes_odd},
    {"atkin", "quadratic forms, one byte per integer", sieve_atkin},
    {"segmented", "Eratosthenes in 32 KiB blocks", sieve_segmented},
};

const sieve_algorithm *sieve_algorithms(size_t *count)
{
    *count = sizeof ALGORITHMS / sizeof ALGORITHMS[0];
    return ALGORITHMS;
}

const sieve_algorithm *sieve_find(const char *name)
{
    size_t count;
    const sieve_algorithm *algos = sieve_algorithms(&count);
    for (size_t i = 0; i < count; i++)
        if (strcmp(algos[i].name, name) == 0)
            return &algos[i];
    return NULL;
}

void prime_list_push(uint64_t prime, void *ctx)
{
    prime_list *list = ctx;
    if (list->failed)
        return;
    if (list->count == list->capacity) {
        size_t cap = list->capacity ? list->capacity * 2 : 64;
        uint64_t *grown = realloc(list->items, cap * sizeof *grown);
        if (!grown) {
            list->failed = 1;
            return;
        }
        list->items = grown;
        list->capacity = cap;
    }
    list->items[list->count++] = prime;
}

void prime_list_free(prime_list *list)
{
    free(list->items);
    memset(list, 0, sizeof *list);
}

sieve_status sieve_collect(const sieve_algorithm *algo, uint64_t limit,
                           prime_list *out)
{
    memset(out, 0, sizeof *out);
    sieve_status status = algo->run(limit, prime_list_push, out);
    if (status == SIEVE_OK && out->failed)
        status = SIEVE_ENOMEM;
    if (status != SIEVE_OK)
        prime_list_free(out);
    return status;
}

static void count_one(uint64_t prime, void *ctx)
{
    (void)prime;
    ++*(uint64_t *)ctx;
}

sieve_status sieve_count(const sieve_algorithm *algo, uint64_t limit,
                         uint64_t *count)
{
    *count = 0;
    return algo->run(limit, count_one, count);
}

uint64_t sieve_isqrt(uint64_t n)
{
    /* sqrt() on a double can be off by one for large n, so correct it. */
    uint64_t r = (uint64_t)sqrt((double)n);
    if (r > UINT64_C(4294967295))
        r = UINT64_C(4294967295);
    while (r * r > n)
        r--;
    while (r < UINT64_C(4294967295) && (r + 1) * (r + 1) <= n)
        r++;
    return r;
}

const char *sieve_strerror(sieve_status status)
{
    switch (status) {
    case SIEVE_OK:
        return "success";
    case SIEVE_ENOMEM:
        return "out of memory";
    case SIEVE_ERANGE:
        return "bound too large for this algorithm";
    }
    return "unknown error";
}
