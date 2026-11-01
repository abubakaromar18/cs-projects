/*
 * slist.c - Singly linked list implementation.
 */
#include "slist.h"

#include <stdlib.h>

static slist_node *node_new(int value) {
    slist_node *n = malloc(sizeof *n);
    if (n) {
        n->value = value;
        n->next = NULL;
    }
    return n;
}

/* Returns the node at `index` (caller guarantees index < size). */
static slist_node *node_at(const slist *list, size_t index) {
    slist_node *cur = list->head;
    while (index--) cur = cur->next;
    return cur;
}

/* ---------- Lifecycle ---------- */

slist *slist_create(void) {
    return calloc(1, sizeof(slist));
}

void slist_clear(slist *list) {
    if (!list) return;
    slist_node *cur = list->head;
    while (cur) {
        slist_node *next = cur->next;
        free(cur);
        cur = next;
    }
    list->head = list->tail = NULL;
    list->size = 0;
}

void slist_destroy(slist *list) {
    slist_clear(list);
    free(list);
}

/* ---------- Queries ---------- */

size_t slist_size(const slist *list) { return list ? list->size : 0; }

bool slist_is_empty(const slist *list) { return slist_size(list) == 0; }

ll_status slist_front(const slist *list, int *out) {
    if (!list || !out) return LL_ERR_NULL;
    if (!list->head) return LL_ERR_EMPTY;
    *out = list->head->value;
    return LL_OK;
}

ll_status slist_back(const slist *list, int *out) {
    if (!list || !out) return LL_ERR_NULL;
    if (!list->tail) return LL_ERR_EMPTY;
    *out = list->tail->value;
    return LL_OK;
}

ll_status slist_get(const slist *list, size_t index, int *out) {
    if (!list || !out) return LL_ERR_NULL;
    if (index >= list->size) return LL_ERR_INDEX;
    *out = node_at(list, index)->value;
    return LL_OK;
}

long slist_index_of(const slist *list, int value) {
    if (!list) return -1;
    long i = 0;
    for (const slist_node *n = list->head; n; n = n->next, i++)
        if (n->value == value) return i;
    return -1;
}

bool slist_contains(const slist *list, int value) {
    return slist_index_of(list, value) >= 0;
}

/* ---------- Mutation ---------- */

ll_status slist_push_front(slist *list, int value) {
    if (!list) return LL_ERR_NULL;
    slist_node *n = node_new(value);
    if (!n) return LL_ERR_NOMEM;
    n->next = list->head;
    list->head = n;
    if (!list->tail) list->tail = n;
    list->size++;
    return LL_OK;
}

ll_status slist_push_back(slist *list, int value) {
    if (!list) return LL_ERR_NULL;
    slist_node *n = node_new(value);
    if (!n) return LL_ERR_NOMEM;
    if (list->tail) list->tail->next = n;
    else list->head = n;
    list->tail = n;
    list->size++;
    return LL_OK;
}

ll_status slist_pop_front(slist *list, int *out) {
    if (!list) return LL_ERR_NULL;
    if (!list->head) return LL_ERR_EMPTY;
    slist_node *old = list->head;
    if (out) *out = old->value;
    list->head = old->next;
    if (!list->head) list->tail = NULL;
    free(old);
    list->size--;
    return LL_OK;
}

ll_status slist_pop_back(slist *list, int *out) {
    if (!list) return LL_ERR_NULL;
    if (!list->head) return LL_ERR_EMPTY;
    if (list->head == list->tail) return slist_pop_front(list, out);
    /* Walk to the node just before the tail: the O(n) cost of a singly linked list. */
    slist_node *prev = node_at(list, list->size - 2);
    if (out) *out = list->tail->value;
    free(list->tail);
    prev->next = NULL;
    list->tail = prev;
    list->size--;
    return LL_OK;
}

ll_status slist_insert(slist *list, size_t index, int value) {
    if (!list) return LL_ERR_NULL;
    if (index > list->size) return LL_ERR_INDEX;
    if (index == 0) return slist_push_front(list, value);
    if (index == list->size) return slist_push_back(list, value);
    slist_node *n = node_new(value);
    if (!n) return LL_ERR_NOMEM;
    slist_node *prev = node_at(list, index - 1);
    n->next = prev->next;
    prev->next = n;
    list->size++;
    return LL_OK;
}

ll_status slist_remove_at(slist *list, size_t index, int *out) {
    if (!list) return LL_ERR_NULL;
    if (index >= list->size) return LL_ERR_INDEX;
    if (index == 0) return slist_pop_front(list, out);
    slist_node *prev = node_at(list, index - 1);
    slist_node *victim = prev->next;
    if (out) *out = victim->value;
    prev->next = victim->next;
    if (victim == list->tail) list->tail = prev;
    free(victim);
    list->size--;
    return LL_OK;
}

bool slist_remove_value(slist *list, int value) {
    if (!list) return false;
    /* Pointer-to-pointer walk: removes without special-casing the head. */
    slist_node **link = &list->head;
    slist_node *prev = NULL;
    while (*link) {
        slist_node *cur = *link;
        if (cur->value == value) {
            *link = cur->next;
            if (cur == list->tail) list->tail = prev;
            free(cur);
            list->size--;
            return true;
        }
        prev = cur;
        link = &cur->next;
    }
    return false;
}

/* ---------- Algorithms ---------- */

void slist_reverse(slist *list) {
    if (!list) return;
    slist_node *prev = NULL, *cur = list->head;
    list->tail = list->head;
    while (cur) {
        slist_node *next = cur->next;
        cur->next = prev;
        prev = cur;
        cur = next;
    }
    list->head = prev;
}

/* Merge two sorted chains. Uses `<=` on the left so equal keys keep order (stable). */
static slist_node *merge(slist_node *a, slist_node *b) {
    slist_node dummy = {0, NULL};
    slist_node *tail = &dummy;
    while (a && b) {
        if (a->value <= b->value) { tail->next = a; a = a->next; }
        else                      { tail->next = b; b = b->next; }
        tail = tail->next;
    }
    tail->next = a ? a : b;
    return dummy.next;
}

/* Top-down merge sort: split with slow/fast pointers, sort halves, merge. */
static slist_node *merge_sort(slist_node *head) {
    if (!head || !head->next) return head;
    slist_node *slow = head, *fast = head->next;
    while (fast && fast->next) {
        slow = slow->next;
        fast = fast->next->next;
    }
    slist_node *right = slow->next;
    slow->next = NULL;
    return merge(merge_sort(head), merge_sort(right));
}

void slist_sort(slist *list) {
    if (!list || list->size < 2) return;
    list->head = merge_sort(list->head);
    slist_node *t = list->head;
    while (t->next) t = t->next;
    list->tail = t;
}

ll_status slist_middle(const slist *list, int *out) {
    if (!list || !out) return LL_ERR_NULL;
    if (!list->head) return LL_ERR_EMPTY;
    /* Fast pointer moves two steps per slow step; slow ends at the middle
     * (the second middle for even lengths). */
    const slist_node *slow = list->head, *fast = list->head;
    while (fast && fast->next) {
        slow = slow->next;
        fast = fast->next->next;
    }
    *out = slow->value;
    return LL_OK;
}

void slist_foreach(const slist *list, void (*fn)(int, void *), void *ctx) {
    if (!list || !fn) return;
    for (const slist_node *n = list->head; n; n = n->next) fn(n->value, ctx);
}

size_t slist_to_array(const slist *list, int *buf, size_t cap) {
    if (!list || !buf) return 0;
    size_t i = 0;
    for (const slist_node *n = list->head; n && i < cap; n = n->next) buf[i++] = n->value;
    return i;
}
