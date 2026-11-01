#include <stdlib.h>

#include "slist.h"
#include "test_util.h"

static void test_create_empty(void) {
    slist *l = slist_create();
    int v;
    CHECK(l != NULL);
    CHECK(slist_is_empty(l));
    CHECK_EQ(slist_front(l, &v), LL_ERR_EMPTY);
    CHECK_EQ(slist_back(l, &v), LL_ERR_EMPTY);
    CHECK_EQ(slist_pop_front(l, &v), LL_ERR_EMPTY);
    CHECK_EQ(slist_pop_back(l, &v), LL_ERR_EMPTY);
    CHECK_EQ(slist_middle(l, &v), LL_ERR_EMPTY);
    slist_destroy(l);
}

static void test_push_and_peek(void) {
    slist *l = slist_create();
    int v;
    slist_push_back(l, 2);
    slist_push_back(l, 3);
    slist_push_front(l, 1);
    CHECK_EQ(slist_size(l), 3u);
    CHECK_ARRAY(slist_to_array, l, 1, 2, 3);
    CHECK(slist_front(l, &v) == LL_OK && v == 1);
    CHECK(slist_back(l, &v) == LL_OK && v == 3);
    slist_destroy(l);
}

static void test_pop_both_ends(void) {
    slist *l = slist_create();
    int v;
    for (int i = 1; i <= 4; i++) slist_push_back(l, i);
    CHECK(slist_pop_front(l, &v) == LL_OK && v == 1);
    CHECK(slist_pop_back(l, &v) == LL_OK && v == 4);
    CHECK_ARRAY(slist_to_array, l, 2, 3);
    CHECK(slist_pop_back(l, NULL) == LL_OK);
    CHECK(slist_pop_back(l, &v) == LL_OK && v == 2);
    CHECK(slist_is_empty(l));
    CHECK(l->head == NULL && l->tail == NULL);
    /* the list remains usable after emptying */
    slist_push_back(l, 9);
    CHECK(slist_front(l, &v) == LL_OK && v == 9);
    slist_destroy(l);
}

static void test_get_and_index(void) {
    slist *l = slist_create();
    int v;
    for (int i = 0; i < 5; i++) slist_push_back(l, i * 10);
    CHECK(slist_get(l, 3, &v) == LL_OK && v == 30);
    CHECK_EQ(slist_get(l, 5, &v), LL_ERR_INDEX);
    CHECK_EQ(slist_index_of(l, 40), 4);
    CHECK_EQ(slist_index_of(l, 7), -1);
    CHECK(slist_contains(l, 0));
    CHECK(!slist_contains(l, 99));
    slist_destroy(l);
}

static void test_insert(void) {
    slist *l = slist_create();
    CHECK_EQ(slist_insert(l, 1, 5), LL_ERR_INDEX);
    CHECK_EQ(slist_insert(l, 0, 2), LL_OK);   /* into empty */
    CHECK_EQ(slist_insert(l, 0, 0), LL_OK);   /* front */
    CHECK_EQ(slist_insert(l, 2, 3), LL_OK);   /* back */
    CHECK_EQ(slist_insert(l, 1, 1), LL_OK);   /* middle */
    CHECK_ARRAY(slist_to_array, l, 0, 1, 2, 3);
    slist_push_back(l, 4);                    /* tail must still be right */
    CHECK_ARRAY(slist_to_array, l, 0, 1, 2, 3, 4);
    slist_destroy(l);
}

static void test_remove_at(void) {
    slist *l = slist_create();
    int v;
    for (int i = 0; i < 5; i++) slist_push_back(l, i);
    CHECK(slist_remove_at(l, 2, &v) == LL_OK && v == 2);
    CHECK(slist_remove_at(l, 3, &v) == LL_OK && v == 4);   /* removes tail */
    CHECK(slist_remove_at(l, 0, &v) == LL_OK && v == 0);
    CHECK_EQ(slist_remove_at(l, 2, &v), LL_ERR_INDEX);
    CHECK_ARRAY(slist_to_array, l, 1, 3);
    slist_push_back(l, 8);
    CHECK_ARRAY(slist_to_array, l, 1, 3, 8);
    slist_destroy(l);
}

static void test_remove_value(void) {
    slist *l = slist_create();
    int vals[] = {5, 1, 5, 2, 7};
    for (int i = 0; i < 5; i++) slist_push_back(l, vals[i]);
    CHECK(slist_remove_value(l, 5));          /* first occurrence only */
    CHECK_ARRAY(slist_to_array, l, 1, 5, 2, 7);
    CHECK(slist_remove_value(l, 7));          /* tail */
    CHECK(!slist_remove_value(l, 42));
    slist_push_back(l, 3);
    CHECK_ARRAY(slist_to_array, l, 1, 5, 2, 3);
    slist_destroy(l);
}

static void test_reverse(void) {
    slist *l = slist_create();
    slist_reverse(l);                         /* empty is fine */
    for (int i = 1; i <= 4; i++) slist_push_back(l, i);
    slist_reverse(l);
    CHECK_ARRAY(slist_to_array, l, 4, 3, 2, 1);
    slist_push_back(l, 0);                    /* tail updated */
    CHECK_ARRAY(slist_to_array, l, 4, 3, 2, 1, 0);
    slist_destroy(l);
}

static void test_sort(void) {
    slist *l = slist_create();
    int vals[] = {5, -3, 9, 0, 5, 2, 8, -1};
    for (int i = 0; i < 8; i++) slist_push_back(l, vals[i]);
    slist_sort(l);
    CHECK_ARRAY(slist_to_array, l, -3, -1, 0, 2, 5, 5, 8, 9);
    CHECK_EQ(slist_size(l), 8u);
    slist_push_back(l, 100);
    int v;
    CHECK(slist_back(l, &v) == LL_OK && v == 100);
    slist_destroy(l);
}

static void test_sort_large_random(void) {
    slist *l = slist_create();
    srand(42);
    for (int i = 0; i < 5000; i++) slist_push_back(l, rand() % 1000);
    slist_sort(l);
    int prev = -1, ok = 1;
    for (slist_node *n = l->head; n; n = n->next) {
        if (n->value < prev) ok = 0;
        prev = n->value;
    }
    CHECK(ok);
    CHECK_EQ(slist_size(l), 5000u);
    slist_destroy(l);
}

static void test_middle(void) {
    slist *l = slist_create();
    int v;
    for (int i = 1; i <= 5; i++) slist_push_back(l, i);
    CHECK(slist_middle(l, &v) == LL_OK && v == 3);
    slist_push_back(l, 6);
    CHECK(slist_middle(l, &v) == LL_OK && v == 4);   /* second middle */
    slist_destroy(l);
}

static void sum_cb(int value, void *ctx) { *(int *)ctx += value; }

static void test_foreach_and_clear(void) {
    slist *l = slist_create();
    for (int i = 1; i <= 10; i++) slist_push_back(l, i);
    int sum = 0;
    slist_foreach(l, sum_cb, &sum);
    CHECK_EQ(sum, 55);
    slist_clear(l);
    CHECK(slist_is_empty(l));
    slist_destroy(l);
}

static void test_null_safety(void) {
    int v;
    CHECK_EQ(slist_push_back(NULL, 1), LL_ERR_NULL);
    CHECK_EQ(slist_front(NULL, &v), LL_ERR_NULL);
    CHECK_EQ(slist_size(NULL), 0u);
    CHECK_EQ(slist_index_of(NULL, 1), -1);
    slist_destroy(NULL);
    CHECK(ll_strerror(LL_ERR_INDEX) != NULL);
}

int main(void) {
    printf("slist tests\n");
    RUN_TEST(test_create_empty);
    RUN_TEST(test_push_and_peek);
    RUN_TEST(test_pop_both_ends);
    RUN_TEST(test_get_and_index);
    RUN_TEST(test_insert);
    RUN_TEST(test_remove_at);
    RUN_TEST(test_remove_value);
    RUN_TEST(test_reverse);
    RUN_TEST(test_sort);
    RUN_TEST(test_sort_large_random);
    RUN_TEST(test_middle);
    RUN_TEST(test_foreach_and_clear);
    RUN_TEST(test_null_safety);
    return TEST_SUMMARY("slist");
}
