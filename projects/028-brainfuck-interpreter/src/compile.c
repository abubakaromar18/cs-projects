/*
 * compile.c - Brainfuck source -> IR, with an optional optimizing pass.
 *
 * The compiler works in three phases:
 *   1. Lexing:   keep only the 8 command characters, remembering line/col
 *                of each so errors can point at the source.
 *   2. Matching: pair every '[' with its ']' using a stack. This is where
 *                syntax errors are found.
 *   3. Emitting: walk the commands and append IR ops. Level 1 folds runs of
 *                +/- and </>; level 2 additionally recognises whole loops
 *                that can be replaced with a constant-time instruction.
 * Finally the JZ/JNZ ops are linked to each other by a second stack pass.
 */
#include "bf.h"

#include <stdlib.h>
#include <string.h>

/* One lexed command plus its source position. */
typedef struct {
    char c;
    size_t line, col;
} token;

static int is_command(char c)
{
    return c == '+' || c == '-' || c == '<' || c == '>' ||
           c == '.' || c == ',' || c == '[' || c == ']';
}

static bf_status emit(bf_program *p, bf_opkind kind, int32_t arg, int32_t offset)
{
    if (p->len == p->cap) {
        size_t ncap = p->cap ? p->cap * 2 : 64;
        bf_op *n = realloc(p->ops, ncap * sizeof *n);
        if (!n)
            return BF_ERR_NOMEM;
        p->ops = n;
        p->cap = ncap;
    }
    p->ops[p->len++] = (bf_op){kind, arg, offset};
    return BF_OK;
}

/* ------------------------------------------------------- loop idioms -- */

/* Offsets a multiply loop may touch, relative to the loop's cell. */
#define MUL_RANGE 64
#define MUL_SPAN (2 * MUL_RANGE + 1)

/*
 * Try to replace the loop body toks[lo..hi) (exclusive of the brackets)
 * with a constant-time sequence. Returns 1 if ops were emitted, 0 if the
 * loop must be compiled normally, or -1 on allocation failure.
 */
static int try_loop_idiom(const token *toks, size_t lo, size_t hi, bf_program *p)
{
    int delta[MUL_SPAN] = {0};
    int pos = 0, moved = 0, changed = 0;

    for (size_t i = lo; i < hi; i++) {
        switch (toks[i].c) {
        case '+': delta[pos + MUL_RANGE]++; changed = 1; break;
        case '-': delta[pos + MUL_RANGE]--; changed = 1; break;
        case '>': pos++; moved = 1; break;
        case '<': pos--; moved = 1; break;
        default:  return 0; /* I/O or nested loop: not a simple idiom */
        }
        if (pos < -MUL_RANGE || pos > MUL_RANGE)
            return 0;
    }

    /* Scan loop: [>], [<<], ... -- body only moves, never changes cells. */
    if (moved && !changed && pos != 0)
        return emit(p, BF_OP_SCAN, pos, 0) == BF_OK ? 1 : -1;

    /* Everything below needs the pointer to end where it started and the
     * loop cell to step by exactly one each iteration. */
    if (pos != 0)
        return 0;
    int d0 = delta[MUL_RANGE] & 0xFF; /* step of the loop cell mod 256 */
    if (d0 != 0xFF && d0 != 0x01)
        return 0;

    /*
     * Multiply / copy loop: [->+>+++<<] runs `cell` times (when the cell
     * decrements) and adds delta[k] * cell to each other cell k. With an
     * incrementing cell it runs (256 - cell) times, i.e. -cell mod 256, so
     * the factor's sign flips. A plain clear loop has no other deltas.
     */
    int sign = (d0 == 0xFF) ? 1 : -1;
    for (int k = 0; k < MUL_SPAN; k++) {
        if (k == MUL_RANGE || (delta[k] & 0xFF) == 0)
            continue;
        if (emit(p, BF_OP_MULADD, (delta[k] * sign) & 0xFF, k - MUL_RANGE) != BF_OK)
            return -1;
    }
    return emit(p, BF_OP_SET, 0, 0) == BF_OK ? 1 : -1;
}

/* ------------------------------------------------------------ compile -- */

bf_status bf_compile(const char *src, size_t len, int opt_level,
                     bf_program *out, bf_error *err)
{
    bf_error dummy;
    if (!err)
        err = &dummy;
    memset(err, 0, sizeof *err);
    memset(out, 0, sizeof *out);

    bf_status st = BF_ERR_NOMEM;
    token *toks = malloc((len ? len : 1) * sizeof *toks);
    size_t *match = malloc((len ? len : 1) * sizeof *match);
    size_t *stack = malloc((len ? len : 1) * sizeof *stack);
    if (!toks || !match || !stack)
        goto done;

    /* Phase 1: lex. */
    size_t n = 0, line = 1, col = 1;
    for (size_t i = 0; i < len; i++) {
        if (is_command(src[i]))
            toks[n++] = (token){src[i], line, col};
        if (src[i] == '\n') {
            line++;
            col = 1;
        } else {
            col++;
        }
    }

    /* Phase 2: bracket matching. */
    size_t sp = 0;
    for (size_t i = 0; i < n; i++) {
        if (toks[i].c == '[') {
            stack[sp++] = i;
        } else if (toks[i].c == ']') {
            if (sp == 0) {
                st = BF_ERR_UNMATCHED_CLOSE;
                err->line = toks[i].line;
                err->col = toks[i].col;
                goto done;
            }
            size_t open = stack[--sp];
            match[open] = i;
            match[i] = open;
        }
    }
    if (sp != 0) {
        size_t open = stack[sp - 1]; /* innermost unclosed '[' */
        st = BF_ERR_UNMATCHED_OPEN;
        err->line = toks[open].line;
        err->col = toks[open].col;
        goto done;
    }

    /* Phase 3: emit IR. */
    for (size_t i = 0; i < n;) {
        char c = toks[i].c;

        if (opt_level >= 1 && (c == '+' || c == '-')) {
            int sum = 0;
            for (; i < n && (toks[i].c == '+' || toks[i].c == '-'); i++)
                sum += toks[i].c == '+' ? 1 : -1;
            sum &= 0xFF;
            if (sum && emit(out, BF_OP_ADD, sum, 0) != BF_OK)
                goto done;
            continue;
        }
        if (opt_level >= 1 && (c == '<' || c == '>')) {
            int sum = 0;
            for (; i < n && (toks[i].c == '<' || toks[i].c == '>'); i++)
                sum += toks[i].c == '>' ? 1 : -1;
            if (sum && emit(out, BF_OP_MOVE, sum, 0) != BF_OK)
                goto done;
            continue;
        }
        if (opt_level >= 2 && c == '[') {
            int r = try_loop_idiom(toks, i + 1, match[i], out);
            if (r < 0)
                goto done;
            if (r > 0) {
                i = match[i] + 1; /* skip the whole loop */
                continue;
            }
        }

        bf_status e = BF_OK;
        switch (c) {
        case '+': e = emit(out, BF_OP_ADD, 1, 0); break;
        case '-': e = emit(out, BF_OP_ADD, 0xFF, 0); break;
        case '>': e = emit(out, BF_OP_MOVE, 1, 0); break;
        case '<': e = emit(out, BF_OP_MOVE, -1, 0); break;
        case '.': e = emit(out, BF_OP_OUT, 0, 0); break;
        case ',': e = emit(out, BF_OP_IN, 0, 0); break;
        case '[': e = emit(out, BF_OP_JZ, 0, 0); break;
        case ']': e = emit(out, BF_OP_JNZ, 0, 0); break;
        }
        if (e != BF_OK)
            goto done;
        i++;
    }

    /* Link jumps: each JZ points at its JNZ and vice versa. The emitted IR
     * has fewer ops than tokens, so the token-level `match` table cannot be
     * reused; a fresh stack pass over the IR is simplest. */
    sp = 0;
    for (size_t pc = 0; pc < out->len; pc++) {
        if (out->ops[pc].kind == BF_OP_JZ) {
            stack[sp++] = pc;
        } else if (out->ops[pc].kind == BF_OP_JNZ) {
            size_t open = stack[--sp];
            out->ops[open].arg = (int32_t)pc;
            out->ops[pc].arg = (int32_t)open;
        }
    }
    st = BF_OK;

done:
    free(toks);
    free(match);
    free(stack);
    if (st != BF_OK)
        bf_program_free(out);
    err->status = st;
    return st;
}

void bf_program_free(bf_program *p)
{
    if (!p)
        return;
    free(p->ops);
    p->ops = NULL;
    p->len = p->cap = 0;
}

void bf_dump(const bf_program *p, FILE *fp)
{
    static const char *names[] = {"ADD", "MOVE", "OUT", "IN", "JZ",
                                  "JNZ", "SET", "SCAN", "MULADD"};
    int depth = 0;
    for (size_t pc = 0; pc < p->len; pc++) {
        const bf_op *op = &p->ops[pc];
        if (op->kind == BF_OP_JNZ)
            depth--;
        fprintf(fp, "%5zu  %*s%-6s", pc, depth * 2, "", names[op->kind]);
        switch (op->kind) {
        case BF_OP_ADD:    fprintf(fp, " %+d", (int8_t)op->arg); break;
        case BF_OP_MULADD: fprintf(fp, " [%+d] += cell * %d", op->offset, op->arg); break;
        case BF_OP_OUT:
        case BF_OP_IN:     break;
        case BF_OP_JZ:
        case BF_OP_JNZ:    fprintf(fp, " -> %d", op->arg); break;
        default:           fprintf(fp, " %d", op->arg); break;
        }
        fputc('\n', fp);
        if (op->kind == BF_OP_JZ)
            depth++;
    }
}

const char *bf_strerror(bf_status s)
{
    switch (s) {
    case BF_OK:                  return "ok";
    case BF_ERR_NOMEM:           return "out of memory";
    case BF_ERR_UNMATCHED_OPEN:  return "unmatched '['";
    case BF_ERR_UNMATCHED_CLOSE: return "unmatched ']'";
    case BF_ERR_TAPE_BOUNDS:     return "data pointer moved off the tape";
    case BF_ERR_STEP_LIMIT:      return "step limit exceeded";
    case BF_ERR_IO:              return "output error";
    }
    return "unknown error";
}
