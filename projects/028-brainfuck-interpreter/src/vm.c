/*
 * vm.c - The virtual machine that executes compiled Brainfuck IR.
 *
 * A classic fetch-decode-execute loop over a flat array of ops. Cells are
 * unsigned bytes (wrapping arithmetic) and every pointer movement is bounds
 * checked, so a buggy program produces an error instead of corrupting memory.
 */
#include "bf.h"

#include <stdlib.h>

bf_config bf_default_config(void)
{
    return (bf_config){.tape_size = 30000, .eof = BF_EOF_ZERO, .max_steps = 0};
}

/* Is ptr + delta a valid cell index? Done in signed 64-bit to avoid wrap. */
static int in_bounds(size_t ptr, int64_t delta, size_t size)
{
    int64_t t = (int64_t)ptr + delta;
    return t >= 0 && (uint64_t)t < size;
}

bf_status bf_run(const bf_program *p, const bf_config *cfg, bf_io io,
                 bf_stats *stats, bf_error *err)
{
    bf_error dummy;
    if (!err)
        err = &dummy;
    bf_config defaults = bf_default_config();
    if (!cfg)
        cfg = &defaults;

    size_t size = cfg->tape_size ? cfg->tape_size : 1;
    unsigned char *tape = calloc(size, 1);
    if (!tape) {
        err->status = BF_ERR_NOMEM;
        return BF_ERR_NOMEM;
    }

    bf_status st = BF_OK;
    size_t ptr = 0, pc = 0;
    uint64_t steps = 0;
    const bf_op *ops = p->ops;

    for (; pc < p->len; pc++) {
        if (cfg->max_steps && steps >= cfg->max_steps) {
            st = BF_ERR_STEP_LIMIT;
            break;
        }
        steps++;

        const bf_op *op = &ops[pc];
        switch (op->kind) {
        case BF_OP_ADD:
            tape[ptr] = (unsigned char)(tape[ptr] + op->arg);
            break;

        case BF_OP_MOVE:
            if (!in_bounds(ptr, op->arg, size)) {
                st = BF_ERR_TAPE_BOUNDS;
                goto out;
            }
            ptr += (size_t)(int64_t)op->arg;
            break;

        case BF_OP_OUT:
            if (io.write(io.ctx, tape[ptr]) != 0) {
                st = BF_ERR_IO;
                goto out;
            }
            break;

        case BF_OP_IN: {
            int c = io.read(io.ctx);
            if (c != EOF)
                tape[ptr] = (unsigned char)c;
            else if (cfg->eof == BF_EOF_ZERO)
                tape[ptr] = 0;
            else if (cfg->eof == BF_EOF_MINUS_ONE)
                tape[ptr] = 0xFF;
            /* BF_EOF_UNCHANGED: leave the cell as is */
            break;
        }

        case BF_OP_JZ:
            if (tape[ptr] == 0)
                pc = (size_t)op->arg; /* lands on JNZ; loop's pc++ steps past */
            break;

        case BF_OP_JNZ:
            if (tape[ptr] != 0)
                pc = (size_t)op->arg; /* back to JZ; pc++ enters the body */
            break;

        case BF_OP_SET:
            tape[ptr] = (unsigned char)op->arg;
            break;

        case BF_OP_SCAN:
            while (tape[ptr] != 0) {
                if (!in_bounds(ptr, op->arg, size)) {
                    st = BF_ERR_TAPE_BOUNDS;
                    goto out;
                }
                ptr += (size_t)(int64_t)op->arg;
            }
            break;

        case BF_OP_MULADD:
            /* The original loop never ran when the cell was 0, so it must
             * not touch (or bounds-fault on) the target cell either. */
            if (tape[ptr] != 0) {
                if (!in_bounds(ptr, op->offset, size)) {
                    st = BF_ERR_TAPE_BOUNDS;
                    goto out;
                }
                size_t t = ptr + (size_t)(int64_t)op->offset;
                tape[t] = (unsigned char)(tape[t] + tape[ptr] * op->arg);
            }
            break;
        }
    }

out:
    if (stats) {
        stats->steps = steps;
        stats->ptr = ptr;
    }
    err->status = st;
    err->pc = pc;
    free(tape);
    return st;
}

/* ------------------------------------------------------------ io glue -- */

static int file_read(void *ctx)
{
    return fgetc(((bf_file_io *)ctx)->in);
}

static int file_write(void *ctx, int byte)
{
    return fputc(byte, ((bf_file_io *)ctx)->out) == EOF ? -1 : 0;
}

bf_io bf_io_files(bf_file_io *f)
{
    return (bf_io){file_read, file_write, f};
}

static int mem_read(void *ctx)
{
    bf_mem_io *m = ctx;
    return m->in_pos < m->in_len ? m->in[m->in_pos++] : EOF;
}

static int mem_write(void *ctx, int byte)
{
    bf_mem_io *m = ctx;
    if (m->out_len >= m->out_cap)
        return -1;
    m->out[m->out_len++] = (unsigned char)byte;
    return 0;
}

bf_io bf_io_memory(bf_mem_io *m)
{
    return (bf_io){mem_read, mem_write, m};
}
