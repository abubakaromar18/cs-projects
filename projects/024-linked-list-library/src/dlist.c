/*
 * dlist.c - Doubly linked list implementation.
 */
#include "dlist.h"

#include <stdlib.h>

static dlist_node *node_new(int value) {
    dlist_node *n = malloc(sizeof *n);
    if (n) {
        n->value = value;
        n->prev = n->next = NULL;
    }
    return n;
}

/* Walk from the nearer end: at most size/2 hops. Caller ensures index < size. */
static dlist_node *node_at(const dlist *list, size_t index) {
    dlist_node *cur;
    if (index < list->size / 2) {
        cur = list->head;
        while (index--) cur = cur->next;
    } else {
        cur = list->tail;
        for (size_t i = list->size - 1; i > index; i--) cur = cur->prev;
    }
    return cur;
}

/* Detach a node from the list and free it. */
static void unlink_node(dlist *list, dlist_node *n) {
    if (n->prev) n->prev->next = n->next;
    else list->head = n->next;
    if (n->next) n->next->prev = n->prev;
    else list->tail = n->prev;
    free(n);
    list->size--;
}

/* ---------- Lifecycle ---------- */

dlist *dlist_create(void) { return calloc(1, sizeof(dlist)); }

void dlist_clear(dlist *list) {
    if (!list) return;
    dlist_node *cur = list->head;
    while (cur) {
        dlist_node *next = cur->next;
        free(cur);
        cur = next;
    }
    list->head = list->tail = NULL;
    list->size = 0;
}

void dlist_destroy(dlist *list) {
    dlist_clear(list);
    free(list);
}

/* ---------- Queries ---------- */

size_t dlist_size(const dlist *list) { return list ? list->size : 0; }

bool dlist_is_empty(const dlist *list) { return dlist_size(list) == 0; }

ll_status dlist_front(const dlist *list, int *out) {
    if (!list || !out) return LL_ERR_NULL;
    if (!list->head) return LL_ERR_EMPTY;
    *out = list->head->value;
    return LL_OK;
}

ll_status dlist_back(const dlist *list, int *out) {
    if (!list || !out) return LL_ERR_NULL;
    if (!list->tail) return LL_ERR_EMPTY;
    *out = list->tail->value;
    return LL_OK;
}

ll_status dlist_get(const dlist *list, size_t index, int *out) {
    if (!list || !out) return LL_ERR_NULL;
    if (index >= list->size) return LL_ERR_INDEX;
    *out = node_at(list, index)->value;
    return LL_OK;
}

long dlist_index_of(const dlist *list, int value) {
    if (!list) return -1;
    long i = 0;
    for (const dlist_node *n = list->head; n; n = n->next, i++)
        if (n->value == value) return i;
    return -1;
}

bool dlist_contains(const dlist *list, int value) {
    return dlist_index_of(list, value) >= 0;
}

/* ---------- Mutation ---------- */

ll_status dlist_push_front(dlist *list, int value) {
    if (!list) return LL_ERR_NULL;
    dlist_node *n = node_new(value);
    if (!n) return LL_ERR_NOMEM;
    n->next = list->head;
    if (list->head) list->head->prev = n;
    else list->tail = n;
    list->head = n;
    list->size++;
    return LL_OK;
}

ll_status dlist_push_back(dlist *list, int value) {
    if (!list) return LL_ERR_NULL;
    dlist_node *n = node_new(value);
    if (!n) return LL_ERR_NOMEM;
    n->prev = list->tail;
    if (list->tail) list->tail->next = n;
    else list->head = n;
    list->tail = n;
    list->size++;
    return LL_OK;
}

ll_status dlist_pop_front(dlist *list, int *out) {
    if (!list) return LL_ERR_NULL;
    if (!list->head) return LL_ERR_EMPTY;
    if (out) *out = list->head->value;
    unlink_node(list, list->head);
    return LL_OK;
}

ll_status dlist_pop_back(dlist *list, int *out) {
    if (!list) return LL_ERR_NULL;
    if (!list->tail) return LL_ERR_EMPTY;
    if (out) *out = list->tail->value;
    unlink_node(list, list->tail);   /* O(1) thanks to the prev pointer */
    return LL_OK;
}

ll_status dlist_insert(dlist *list, size_t index, int value) {
    if (!list) return LL_ERR_NULL;
    if (index > list->size) return LL_ERR_INDEX;
    if (index == 0) return dlist_push_front(list, value);
    if (index == list->size) return dlist_push_back(list, value);
    dlist_node *n = node_new(value);
    if (!n) return LL_ERR_NOMEM;
    dlist_node *at = node_at(list, index);   /* new node goes before `at` */
    n->prev = at->prev;
    n->next = at;
    at->prev->next = n;
    at->prev = n;
    list->size++;
    return LL_OK;
}

ll_status dlist_remove_at(dlist *list, size_t index, int *out) {
    if (!list) return LL_ERR_NULL;
    if (index >= list->size) return LL_ERR_INDEX;
    dlist_node *n = node_at(list, index);
    if (out) *out = n->value;
    unlink_node(list, n);
    return LL_OK;
}

bool dlist_remove_value(dlist *list, int value) {
    if (!list) return false;
    for (dlist_node *n = list->head; n; n = n->next) {
        if (n->value == value) {
            unlink_node(list, n);
            return true;
        }
    }
    return false;
}

/* ---------- Algorithms ---------- */

void dlist_reverse(dlist *list) {
    if (!list) return;
    /* Swap prev/next on every node, then swap head and tail. */
    dlist_node *cur = list->head;
    while (cur) {
        dlist_node *next = cur->next;
        cur->next = cur->prev;
        cur->prev = next;
        cur = next;
    }
    dlist_node *tmp = list->head;
    list->head = list->tail;
    list->tail = tmp;
}

void dlist_foreach(const dlist *list, void (*fn)(int, void *), void *ctx) {
    if (!list || !fn) return;
    for (const dlist_node *n = list->head; n; n = n->next) fn(n->value, ctx);
}

void dlist_foreach_reverse(const dlist *list, void (*fn)(int, void *), void *ctx) {
    if (!list || !fn) return;
    for (const dlist_node *n = list->tail; n; n = n->prev) fn(n->value, ctx);
}

size_t dlist_to_array(const dlist *list, int *buf, size_t cap) {
    if (!list || !buf) return 0;
    size_t i = 0;
    for (const dlist_node *n = list->head; n && i < cap; n = n->next) buf[i++] = n->value;
    return i;
}

bool dlist_check_invariants(const dlist *list) {
    if (!list) return false;
    if (list->size == 0) return list->head == NULL && list->tail == NULL;
    if (!list->head || !list->tail) return false;
    if (list->head->prev || list->tail->next) return false;
    size_t count = 0;
    const dlist_node *prev = NULL;
    for (const dlist_node *n = list->head; n; n = n->next) {
        if (n->prev != prev) return false;
        prev = n;
        if (++count > list->size) return false;   /* guards against cycles */
    }
    return prev == list->tail && count == list->size;
}
