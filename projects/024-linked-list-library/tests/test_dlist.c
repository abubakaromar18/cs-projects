#include <stdlib.h>

#include "dlist.h"
#include "test_util.h"

static void test_create_empty(void) {
    dlist *l = dlist_create();
    int v;
    CHECK(l != NULL);
    CHECK(dlist_is_empty(l));
    CHECK(dlist_check_invariants(l));
    CHECK_EQ(dlist_front(l, &v), LL_ERR_EMPTY);
    CHECK_EQ(dlist_pop_back(l, &v), LL_ERR_EMPTY);
    dlist_destroy(l);
}

static void test_push_pop(void) {
    dlist *l = dlist_create();
    int v;
    dlist_push_back(l, 2);
    dlist_push_front(l, 1);
    dlist_push_back(l, 3);
    CHECK_ARRAY(dlist_to_array, l, 1, 2, 3);
    CHECK(dlist_check_invariants(l));
    CHECK(dlist_pop_back(l, &v) == LL_OK && v == 3);
    CHECK(dlist_pop_front(l, &v) == LL_OK && v == 1);
    CHECK(dlist_check_invariants(l));
    CHECK(dlist_pop_back(l, &v) == LL_OK && v == 2);
    CHECK(dlist_is_empty(l));
    CHECK(dlist_check_invariants(l));
    dlist_destroy(l);
}

static void test_get_both_halves(void) {
    dlist *l = dlist_create();
    int v;
    for (int i = 0; i < 9; i++) dlist_push_back(l, i * i);
    for (size_t i = 0; i < 9; i++) {
        CHECK(dlist_get(l, i, &v) == LL_OK && v == (int)(i * i));
    }
    CHECK_EQ(dlist_get(l, 9, &v), LL_ERR_INDEX);
    CHECK_EQ(dlist_index_of(l, 49), 7);
    CHECK(!dlist_contains(l, 2));
    dlist_destroy(l);
}

static void test_insert(void) {
    dlist *l = dlist_create();
    CHECK_EQ(dlist_insert(l, 0, 10), LL_OK);
    CHECK_EQ(dlist_insert(l, 1, 40), LL_OK);
    CHECK_EQ(dlist_insert(l, 1, 20), LL_OK);
    CHECK_EQ(dlist_insert(l, 2, 30), LL_OK);
    CHECK_EQ(dlist_insert(l, 0, 0), LL_OK);
    CHECK_EQ(dlist_insert(l, 99, 1), LL_ERR_INDEX);
    CHECK_ARRAY(dlist_to_array, l, 0, 10, 20, 30, 40);
    CHECK(dlist_check_invariants(l));
    dlist_destroy(l);
}

static void test_remove(void) {
    dlist *l = dlist_create();
    int v;
    for (int i = 0; i < 6; i++) dlist_push_back(l, i);
    CHECK(dlist_remove_at(l, 4, &v) == LL_OK && v == 4);
    CHECK(dlist_remove_at(l, 0, &v) == LL_OK && v == 0);
    CHECK(dlist_remove_at(l, 3, &v) == LL_OK && v == 5);
    CHECK(dlist_check_invariants(l));
    CHECK(dlist_remove_value(l, 2));
    CHECK(!dlist_remove_value(l, 2));
    CHECK_ARRAY(dlist_to_array, l, 1, 3);
    CHECK(dlist_check_invariants(l));
    dlist_destroy(l);
}

static void test_reverse(void) {
    dlist *l = dlist_create();
    for (int i = 1; i <= 5; i++) dlist_push_back(l, i);
    dlist_reverse(l);
    CHECK_ARRAY(dlist_to_array, l, 5, 4, 3, 2, 1);
    CHECK(dlist_check_invariants(l));
    dlist_push_front(l, 6);
    dlist_push_back(l, 0);
    CHECK_ARRAY(dlist_to_array, l, 6, 5, 4, 3, 2, 1, 0);
    CHECK(dlist_check_invariants(l));
    dlist_destroy(l);
}

static void append_cb(int value, void *ctx) {
    int **cursor = ctx;
    *(*cursor)++ = value;
}

static void test_foreach_reverse(void) {
    dlist *l = dlist_create();
    for (int i = 1; i <= 4; i++) dlist_push_back(l, i);
    int buf[4], *cursor = buf;
    dlist_foreach_reverse(l, append_cb, &cursor);
    CHECK(buf[0] == 4 && buf[1] == 3 && buf[2] == 2 && buf[3] == 1);
    dlist_destroy(l);
}

/* Randomized differential test: mirror every operation in a plain array. */
static void test_random_ops_against_array(void) {
    dlist *l = dlist_create();
    int model[512];
    size_t n = 0;
    srand(7);
    for (int step = 0; step < 4000; step++) {
        int op = rand() % 4, val = rand() % 100;
        if ((op == 0 || n == 0) && n < 512) {
            size_t idx = (size_t)rand() % (n + 1);
            dlist_insert(l, idx, val);
            memmove(&model[idx + 1], &model[idx], (n - idx) * sizeof(int));
            model[idx] = val;
            n++;
        } else if (op == 1 && n > 0) {
            size_t idx = (size_t)rand() % n;
            int got;
            dlist_remove_at(l, idx, &got);
            CHECK_EQ(got, model[idx]);
            memmove(&model[idx], &model[idx + 1], (n - idx - 1) * sizeof(int));
            n--;
        } else if (op == 2 && n > 0) {
            size_t idx = (size_t)rand() % n;
            int got;
            dlist_get(l, idx, &got);
            CHECK_EQ(got, model[idx]);
        } else if (n < 512) {
            dlist_push_back(l, val);
            model[n++] = val;
        }
    }
    CHECK_EQ(dlist_size(l), n);
    CHECK(dlist_check_invariants(l));
    int *arr = malloc(n * sizeof(int) + 1);
    dlist_to_array(l, arr, n);
    CHECK(memcmp(arr, model, n * sizeof(int)) == 0);
    free(arr);
    dlist_destroy(l);
}

static void test_null_safety(void) {
    int v;
    CHECK_EQ(dlist_push_front(NULL, 1), LL_ERR_NULL);
    CHECK_EQ(dlist_back(NULL, &v), LL_ERR_NULL);
    CHECK(!dlist_remove_value(NULL, 1));
    CHECK(!dlist_check_invariants(NULL));
    dlist_destroy(NULL);
}

int main(void) {
    printf("dlist tests\n");
    RUN_TEST(test_create_empty);
    RUN_TEST(test_push_pop);
    RUN_TEST(test_get_both_halves);
    RUN_TEST(test_insert);
    RUN_TEST(test_remove);
    RUN_TEST(test_reverse);
    RUN_TEST(test_foreach_reverse);
    RUN_TEST(test_random_ops_against_array);
    RUN_TEST(test_null_safety);
    return TEST_SUMMARY("dlist");
}
