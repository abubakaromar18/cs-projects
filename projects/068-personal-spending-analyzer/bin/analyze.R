#!/usr/bin/env Rscript
# Command-line entry point.
#
#   Rscript bin/analyze.R [options] transactions.csv
#
# Options:
#   --rules PATH        categorisation rules CSV (default inst/extdata/rules.csv)
#   --budgets PATH      monthly budgets CSV (optional)
#   --plots DIR         write PNG charts into DIR
#   --out PATH          write categorised transactions to CSV
#   --top N             number of top merchants to show (default 8)

script_dir <- function() {
  arg <- grep("^--file=", commandArgs(FALSE), value = TRUE)
  if (length(arg)) dirname(normalizePath(sub("^--file=", "", arg))) else "bin"
}
root <- normalizePath(file.path(script_dir(), ".."))
source(file.path(root, "R", "load.R"))
load_spending_analyzer(root)

usage <- function(status = 1) {
  cat("usage: Rscript bin/analyze.R [--rules F] [--budgets F] [--plots DIR]",
      "[--out F] [--top N] transactions.csv\n")
  quit(status = status)
}

parse_args <- function(args) {
  opts <- list(rules = file.path(root, "inst", "extdata", "rules.csv"),
               budgets = NULL, plots = NULL, out = NULL, top = 8, input = NULL)
  i <- 1
  while (i <= length(args)) {
    a <- args[i]
    if (a %in% c("-h", "--help")) usage(0)
    if (a %in% c("--rules", "--budgets", "--plots", "--out", "--top")) {
      if (i == length(args)) usage()
      opts[[sub("^--", "", a)]] <- args[i + 1]
      i <- i + 2
    } else if (startsWith(a, "--")) {
      cat("unknown option:", a, "\n"); usage()
    } else {
      opts$input <- a; i <- i + 1
    }
  }
  if (is.null(opts$input)) usage()
  opts$top <- as.integer(opts$top)
  opts
}

main <- function() {
  opts <- parse_args(commandArgs(trailingOnly = TRUE))
  tx <- read_transactions(opts$input)
  tx <- categorize(tx, read_rules(opts$rules))
  budgets <- if (!is.null(opts$budgets))
    utils::read.csv(opts$budgets, stringsAsFactors = FALSE, strip.white = TRUE)

  writeLines(build_report(tx, budgets, top_n = opts$top))

  if (!is.null(opts$out)) {
    dir.create(dirname(opts$out), showWarnings = FALSE, recursive = TRUE)
    utils::write.csv(tx, opts$out, row.names = FALSE)
    cat("\nWrote categorised transactions to", opts$out, "\n")
  }
  if (!is.null(opts$plots)) {
    paths <- render_all_plots(tx, opts$plots)
    cat("Wrote charts:", paste(paths, collapse = ", "), "\n")
  }
}

main()
