/*
 * slist.h - Singly linked list of ints.
 *
 * The list keeps both a head and a tail pointer so that push_front,
 * push_back and pop_front are all O(1). pop_back is O(n) because a
 * singly linked node cannot reach its predecessor.
 *
 * Functions that can fail return an `ll_status` code; values come back
 * through out-parameters so the return channel stays reserved for errors.
 */
#ifndef SLIST_H
#define SLIST_H

#include <stdbool.h>
#include <stddef.h>

#include "ll_common.h"

typedef struct slist_node {
    int value;
    struct slist_node *next;
} slist_node;

typedef struct slist {
    slist_node *head;
    slist_node *tail;
    size_t size;
} slist;

/* Lifecycle */
slist *slist_create(void);
void slist_destroy(slist *list);   /* frees every node and the list; NULL-safe */
void slist_clear(slist *list);     /* frees every node, keeps the list */

/* Queries */
size_t slist_size(const slist *list);
bool slist_is_empty(const slist *list);
ll_status slist_front(const slist *list, int *out);
ll_status slist_back(const slist *list, int *out);
ll_status slist_get(const slist *list, size_t index, int *out);
long slist_index_of(const slist *list, int value);   /* -1 if absent */
bool slist_contains(const slist *list, int value);

/* Mutation */
ll_status slist_push_front(slist *list, int value);
ll_status slist_push_back(slist *list, int value);
ll_status slist_pop_front(slist *list, int *out);   /* out may be NULL */
ll_status slist_pop_back(slist *list, int *out);    /* out may be NULL */
ll_status slist_insert(slist *list, size_t index, int value); /* 0..size */
ll_status slist_remove_at(slist *list, size_t index, int *out);
bool slist_remove_value(slist *list, int value);    /* first match */

/* Algorithms */
void slist_reverse(slist *list);                    /* in place, O(n) */
void slist_sort(slist *list);                       /* stable merge sort, O(n log n) */
ll_status slist_middle(const slist *list, int *out);/* tortoise & hare */
void slist_foreach(const slist *list, void (*fn)(int value, void *ctx), void *ctx);
size_t slist_to_array(const slist *list, int *buf, size_t cap);

#endif /* SLIST_H */
