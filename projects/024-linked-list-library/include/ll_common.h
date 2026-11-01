/*
 * ll_common.h - Shared status codes for the linked list library.
 */
#ifndef LL_COMMON_H
#define LL_COMMON_H

typedef enum {
    LL_OK = 0,
    LL_ERR_NULL,      /* a required pointer argument was NULL */
    LL_ERR_EMPTY,     /* operation needs at least one element */
    LL_ERR_INDEX,     /* index out of range */
    LL_ERR_NOMEM      /* allocation failed */
} ll_status;

/* Human-readable description of a status code. */
const char *ll_strerror(ll_status status);

#endif /* LL_COMMON_H */
