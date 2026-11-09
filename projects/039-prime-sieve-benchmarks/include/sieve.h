/*
 * sieve.h - public interface for the prime sieve library.
 *
 * Every algorithm reports primes through a callback, in ascending order. That
 * keeps memory use under the caller's control: the benchmark only counts, while
 * sieve_collect() stores results in a growable array.
 */
#ifndef SIEVE_H
#define SIEVE_H

#include <stddef.h>
#include <stdint.h>

/* Status codes returned by every sieve function. */
typedef enum {
    SIEVE_OK = 0,
    SIEVE_ENOMEM = -1, /* an allocation failed */
    SIEVE_ERANGE = -2  /* a bound exceeds what the algorithm supports */
} sieve_status;

/* Largest limit for the algorithms that hold the entire range in memory. */
#define SIEVE_MAX_DENSE UINT64_C(4000000000)
/* Largest bound for the segmented sieve (base primes stay under 10^7). */
#define SIEVE_MAX_SEGMENTED UINT64_C(100000000000000)

/* Called once per prime, in ascending order. */
typedef void (*sieve_emit_fn)(uint64_t prime, void *ctx);

/* Each of these reports all primes p with p <= limit. */
sieve_status sieve_eratosthenes(uint64_t limit, sieve_emit_fn emit, void *ctx);
sieve_status sieve_eratosthenes_odd(uint64_t limit, sieve_emit_fn emit, void *ctx);
sieve_status sieve_atkin(uint64_t limit, sieve_emit_fn emit, void *ctx);
sieve_status sieve_segmented(uint64_t limit, sieve_emit_fn emit, void *ctx);

/* Reports all primes p with lo <= p <= hi. An empty range (lo > hi) is valid. */
sieve_status sieve_segmented_range(uint64_t lo, uint64_t hi,
                                   sieve_emit_fn emit, void *ctx);

/* A named algorithm, so tools and tests can iterate over all of them. */
typedef struct {
    const char *name;
    const char *description;
    sieve_status (*run)(uint64_t limit, sieve_emit_fn emit, void *ctx);
} sieve_algorithm;

const sieve_algorithm *sieve_algorithms(size_t *count);
const sieve_algorithm *sieve_find(const char *name);

/* A heap-allocated array of primes. */
typedef struct {
    uint64_t *items;
    size_t count;
    size_t capacity;
    int failed; /* set if growing the array ran out of memory */
} prime_list;

/* Runs an algorithm and stores its primes. Free with prime_list_free(). */
sieve_status sieve_collect(const sieve_algorithm *algo, uint64_t limit,
                           prime_list *out);
void prime_list_push(uint64_t prime, void *list);
void prime_list_free(prime_list *list);

/* Runs an algorithm and returns only the number of primes found. */
sieve_status sieve_count(const sieve_algorithm *algo, uint64_t limit,
                         uint64_t *count);

/* Floor of the square root of n, exact for all 64-bit values. */
uint64_t sieve_isqrt(uint64_t n);

/* Human-readable text for a status code. */
const char *sieve_strerror(sieve_status status);

#endif /* SIEVE_H */
