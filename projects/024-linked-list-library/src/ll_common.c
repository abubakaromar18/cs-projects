#include "ll_common.h"

const char *ll_strerror(ll_status status) {
    switch (status) {
    case LL_OK:        return "ok";
    case LL_ERR_NULL:  return "null argument";
    case LL_ERR_EMPTY: return "list is empty";
    case LL_ERR_INDEX: return "index out of range";
    case LL_ERR_NOMEM: return "out of memory";
    }
    return "unknown error";
}
