/*
 * dlist.h - Doubly linked list of ints.
 *
 * Every node links to both neighbours, so insertion and removal at
 * either end are O(1), and positional access walks from whichever end
 * is closer (at most n/2 steps).
 */
#ifndef DLIST_H
#define DLIST_H

#include <stdbool.h>
#include <stddef.h>

#include "ll_common.h"

typedef struct dlist_node {
    int value;
    struct dlist_node *prev;
    struct dlist_node *next;
} dlist_node;

typedef struct dlist {
    dlist_node *head;
    dlist_node *tail;
    size_t size;
} dlist;

/* Lifecycle */
dlist *dlist_create(void);
void dlist_destroy(dlist *list);
void dlist_clear(dlist *list);

/* Queries */
size_t dlist_size(const dlist *list);
bool dlist_is_empty(const dlist *list);
ll_status dlist_front(const dlist *list, int *out);
ll_status dlist_back(const dlist *list, int *out);
ll_status dlist_get(const dlist *list, size_t index, int *out);
long dlist_index_of(const dlist *list, int value);
bool dlist_contains(const dlist *list, int value);

/* Mutation */
ll_status dlist_push_front(dlist *list, int value);
ll_status dlist_push_back(dlist *list, int value);
ll_status dlist_pop_front(dlist *list, int *out);
ll_status dlist_pop_back(dlist *list, int *out);
ll_status dlist_insert(dlist *list, size_t index, int value);
ll_status dlist_remove_at(dlist *list, size_t index, int *out);
bool dlist_remove_value(dlist *list, int value);

/* Algorithms */
void dlist_reverse(dlist *list);
void dlist_foreach(const dlist *list, void (*fn)(int value, void *ctx), void *ctx);
void dlist_foreach_reverse(const dlist *list, void (*fn)(int value, void *ctx), void *ctx);
size_t dlist_to_array(const dlist *list, int *buf, size_t cap);

/* Debug helper: verifies prev/next symmetry, head/tail and size. */
bool dlist_check_invariants(const dlist *list);

#endif /* DLIST_H */
