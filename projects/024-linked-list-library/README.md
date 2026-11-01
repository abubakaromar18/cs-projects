# Linked List Library (C)

A small, well-tested C11 library providing **singly** and **doubly** linked lists of `int`, plus a few classic linked-list algorithms. It builds into a static library (`liblinkedlist.a`) with a zero-dependency test suite and a demo program.

## Features

| Operation | `slist` (singly) | `dlist` (doubly) |
|---|---|---|
| `push_front` / `push_back` | O(1) / O(1) | O(1) / O(1) |
| `pop_front` / `pop_back` | O(1) / **O(n)** | O(1) / **O(1)** |
| `get(i)`, `insert(i)`, `remove_at(i)` | O(i) | O(min(i, n−i)), walks from the nearer end |
| `index_of`, `contains`, `remove_value` | O(n) | O(n) |
| `reverse` | O(n) pointer reversal | O(n) prev/next swap |
| `sort` | O(n log n) stable merge sort | — |
| `middle` | O(n) tortoise & hare | — |
| `foreach` | forward | forward and reverse |

Every fallible call returns an `ll_status` (`LL_OK`, `LL_ERR_NULL`, `LL_ERR_EMPTY`, `LL_ERR_INDEX`, `LL_ERR_NOMEM`), and results come back through out-parameters. `ll_strerror()` turns a status into text. All functions handle `NULL` lists safely.

## CS concepts demonstrated

- **Pointer-based data structures**: nodes on the heap, with head and tail pointers and a cached size.
- **Trade-offs between singly and doubly linked lists**: the extra `prev` pointer costs memory but makes `pop_back` and removal of a known node O(1).
- **Pointer-to-pointer removal** (`slist_remove_value`): deletes a node without special-casing the head.
- **Merge sort on linked lists**: splits with slow/fast pointers and merges in place with no extra arrays. It is stable because ties take from the left side.
- **Floyd's tortoise and hare**: finds the middle node in a single pass.
- **Invariant checking** (`dlist_check_invariants`): checks prev/next symmetry, head/tail consistency, size, and that there are no cycles.
- **Manual memory management**: ownership is explicit, and leaks are checked with valgrind and AddressSanitizer.
- **Differential testing**: a randomized test runs thousands of operations on a `dlist` and on a plain array, then checks that the two agree.

## Layout

```
include/   ll_common.h  slist.h  dlist.h      public API
src/       ll_common.c  slist.c  dlist.c      implementation
tests/     test_util.h  test_slist.c  test_dlist.c
examples/  demo.c
Makefile
```

## Build, run, test

Requires a C11 compiler (gcc or clang) and `make`.

```sh
make            # build build/liblinkedlist.a and run the demo
make test       # build and run both test suites
make valgrind   # run the tests under valgrind (leak + memory error check)
make sanitize   # rebuild with -fsanitize=address,undefined and run the tests
make clean
```

To use it in your own program:

```sh
cc -Iinclude myprog.c build/liblinkedlist.a -o myprog
```

```c
#include "slist.h"

slist *l = slist_create();
slist_push_back(l, 3);
slist_push_back(l, 1);
slist_sort(l);
int first;
if (slist_front(l, &first) == LL_OK) printf("%d\n", first);  /* 1 */
slist_destroy(l);
```

## Example output

```
$ make test
slist tests
  [ OK ] test_create_empty
  ...
slist: 13/13 passed
dlist tests
  ...
  [ OK ] test_random_ops_against_array
dlist: 9/9 passed

$ make demo
== Singly linked list ==
built:                 [42 -> 7 -> 19 -> 3 -> 88 -> 7 -> 25]  (size 7)
middle (tortoise/hare): 3
merge-sorted:          [3 -> 7 -> 7 -> 19 -> 25 -> 42 -> 88]  (size 7)
reversed:              [88 -> 42 -> 25 -> 19 -> 7 -> 7 -> 3]  (size 7)
remove first 7:        [88 -> 42 -> 25 -> 19 -> 7 -> 3]  (size 6)
index_of(19):          3

== Doubly linked list ==
built:                 [10 -> 20 -> 30 -> 40 -> 50]  (size 5)
walked backwards:      [50 -> 40 -> 30 -> 20 -> 10]  (size 5)
insert 25 @2:          [10 -> 20 -> 25 -> 30 -> 40 -> 50]  (size 6)
pop_back (O(1)):       50
reversed:              [40 -> 30 -> 25 -> 20 -> 10]  (size 5)
invariants hold:       yes
get(99):               index out of range
```

## Possible extensions

- Make the lists generic: store `void *` plus element size, or add a destructor callback, or generate typed lists with macros.
- Add an iterator API (`slist_iter_next`) so callers can walk the list without callbacks.
- Add Floyd cycle detection, `merge` of two sorted lists, `splice`, and `dedupe`.
- Build an intrusive list like the Linux kernel's `list_head`, where the links are embedded in the user's own struct.
- Add a circular doubly linked list with a sentinel node, which removes most of the NULL checks.
- Benchmark the lists against a dynamic array to show cache effects.
