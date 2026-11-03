/*
 * bf.h - Public API for the Brainfuck compiler-to-IR and virtual machine.
 *
 * Pipeline:   source text --bf_compile()--> bf_program (IR) --bf_run()--> output
 *
 * The compiler lowers the eight Brainfuck commands into a small intermediate
 * representation (IR). Depending on the optimization level it also folds runs
 * of commands and rewrites common loop idioms into single instructions.
 */
#ifndef BF_H
#define BF_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

/* ------------------------------------------------------------------ IR -- */

typedef enum {
    BF_OP_ADD,     /* cell += arg (mod 256)                                   */
    BF_OP_MOVE,    /* ptr  += arg                                             */
    BF_OP_OUT,     /* write cell                                              */
    BF_OP_IN,      /* read into cell (EOF handling is configurable)           */
    BF_OP_JZ,      /* '[' : if cell == 0 jump to op `arg` (the matching JNZ)  */
    BF_OP_JNZ,     /* ']' : if cell != 0 jump to op `arg` (the matching JZ)   */
    BF_OP_SET,     /* cell = arg            -- from [-] / [+]                 */
    BF_OP_SCAN,    /* while cell: ptr += arg -- from [>] / [<<] ...           */
    BF_OP_MULADD   /* if cell: tape[ptr+offset] += cell * arg -- from [->++<] */
} bf_opkind;

typedef struct {
    bf_opkind kind;
    int32_t arg;
    int32_t offset; /* used by BF_OP_MULADD only */
} bf_op;

typedef struct {
    bf_op *ops;
    size_t len;
    size_t cap;
} bf_program;

/* -------------------------------------------------------------- errors -- */

typedef enum {
    BF_OK = 0,
    BF_ERR_NOMEM,
    BF_ERR_UNMATCHED_OPEN,  /* '[' without ']'          (compile time) */
    BF_ERR_UNMATCHED_CLOSE, /* ']' without '['          (compile time) */
    BF_ERR_TAPE_BOUNDS,     /* pointer left the tape    (run time)     */
    BF_ERR_STEP_LIMIT,      /* max_steps exceeded       (run time)     */
    BF_ERR_IO               /* output callback failed   (run time)     */
} bf_status;

typedef struct {
    bf_status status;
    size_t line, col; /* 1-based source position, compile errors only */
    size_t pc;        /* instruction index, run-time errors only      */
} bf_error;

const char *bf_strerror(bf_status s);

/* ------------------------------------------------------------- compile -- */

/*
 * Optimization levels:
 *   0  one IR op per source command (a reference, "naive" interpreter)
 *   1  + run-length folding:  "+++--" -> ADD 1,  ">>><" -> MOVE 2
 *   2  + loop idioms: clear [-], scan [>], multiply/copy [->+>++<<]
 */
bf_status bf_compile(const char *src, size_t len, int opt_level,
                     bf_program *out, bf_error *err);

void bf_program_free(bf_program *p);

/* Print a human-readable listing of the IR. */
void bf_dump(const bf_program *p, FILE *fp);

/* ----------------------------------------------------------------- run -- */

typedef enum {
    BF_EOF_ZERO,      /* ',' at EOF stores 0               */
    BF_EOF_MINUS_ONE, /* ',' at EOF stores 255 (i.e. -1)   */
    BF_EOF_UNCHANGED  /* ',' at EOF leaves the cell alone  */
} bf_eof_mode;

/* I/O is abstracted so the VM can run against files or in-memory buffers. */
typedef struct {
    int (*read)(void *ctx);           /* returns 0..255, or EOF (-1)       */
    int (*write)(void *ctx, int byte);/* returns 0 on success              */
    void *ctx;
} bf_io;

typedef struct {
    size_t tape_size;    /* number of cells, default 30000            */
    bf_eof_mode eof;
    uint64_t max_steps;  /* 0 = unlimited                             */
} bf_config;

typedef struct {
    uint64_t steps; /* IR instructions executed */
    size_t ptr;     /* final data pointer       */
} bf_stats;

bf_config bf_default_config(void);

/* Execute `p`. `stats` may be NULL. On error, `err->pc` is the faulting op. */
bf_status bf_run(const bf_program *p, const bf_config *cfg, bf_io io,
                 bf_stats *stats, bf_error *err);

/* ------------------------------------------------------------ io glue -- */

/* Stream I/O: ctx is a bf_file_io*. */
typedef struct {
    FILE *in;
    FILE *out;
} bf_file_io;
bf_io bf_io_files(bf_file_io *f);

/* In-memory I/O, handy for tests and embedding. */
typedef struct {
    const unsigned char *in;
    size_t in_len, in_pos;
    unsigned char *out;
    size_t out_cap, out_len; /* writes past out_cap fail with BF_ERR_IO */
} bf_mem_io;
bf_io bf_io_memory(bf_mem_io *m);

#endif /* BF_H */
