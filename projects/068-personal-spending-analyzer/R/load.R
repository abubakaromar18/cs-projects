# load.R — source all modules. Used by the CLI and tests so the project runs
# without being installed as a package.

load_spending_analyzer <- function(root = ".") {
  files <- c("io.R", "categorize.R", "analyze.R", "plots.R", "report.R")
  for (f in files) sys.source(file.path(root, "R", f), envir = globalenv())
  invisible(TRUE)
}
