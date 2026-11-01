/*
 * demo.c - Walk through the main features of both list types.
 */
#include <stdio.h>

#include "dlist.h"
#include "slist.h"

static void print_cb(int value, void *ctx) {
    int *first = ctx;
    printf(*first ? "%d" : " -> %d", value);
    *first = 0;
}

static void print_slist(const char *label, const slist *l) {
    int first = 1;
    printf("%-22s [", label);
    slist_foreach(l, print_cb, &first);
    printf("]  (size %zu)\n", slist_size(l));
}

static void print_dlist(const char *label, const dlist *l, int reverse) {
    int first = 1;
    printf("%-22s [", label);
    if (reverse) dlist_foreach_reverse(l, print_cb, &first);
    else dlist_foreach(l, print_cb, &first);
    printf("]  (size %zu)\n", dlist_size(l));
}

int main(void) {
    int v;

    puts("== Singly linked list ==");
    slist *s = slist_create();
    int data[] = {42, 7, 19, 3, 88, 7, 25};
    for (size_t i = 0; i < sizeof data / sizeof *data; i++) slist_push_back(s, data[i]);
    print_slist("built:", s);
    slist_middle(s, &v);
    printf("%-22s %d\n", "middle (tortoise/hare):", v);
    slist_sort(s);
    print_slist("merge-sorted:", s);
    slist_reverse(s);
    print_slist("reversed:", s);
    slist_remove_value(s, 7);
    print_slist("remove first 7:", s);
    printf("%-22s %ld\n", "index_of(19):", slist_index_of(s, 19));
    slist_destroy(s);

    puts("\n== Doubly linked list ==");
    dlist *d = dlist_create();
    for (int i = 1; i <= 5; i++) dlist_push_back(d, i * 10);
    print_dlist("built:", d, 0);
    print_dlist("walked backwards:", d, 1);
    dlist_insert(d, 2, 25);
    print_dlist("insert 25 @2:", d, 0);
    dlist_pop_back(d, &v);
    printf("%-22s %d\n", "pop_back (O(1)):", v);
    dlist_reverse(d);
    print_dlist("reversed:", d, 0);
    printf("%-22s %s\n", "invariants hold:", dlist_check_invariants(d) ? "yes" : "no");
    printf("%-22s %s\n", "get(99):", ll_strerror(dlist_get(d, 99, &v)));
    dlist_destroy(d);
    return 0;
}
