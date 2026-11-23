# testthat sources helper-*.R before tests: load the project modules.
root <- normalizePath(file.path(testthat::test_path(), "..", ".."))
source(file.path(root, "R", "load.R"))
load_spending_analyzer(root)

# Small hand-built fixture used across test files.
make_tx <- function() {
  data.frame(
    date = as.Date(c("2026-01-01", "2026-01-03", "2026-01-05", "2026-01-10",
                     "2026-02-01", "2026-02-03", "2026-02-10", "2026-02-15",
                     "2026-03-01", "2026-03-10")),
    description = c("ACME PAYROLL", "FRESHMART GROCERY #1", "STREAMFLIX.COM", "TRANSFER TO SAVINGS",
                    "ACME PAYROLL", "FRESHMART GROCERY #2", "STREAMFLIX.COM", "MYSTERY SHOP",
                    "ACME PAYROLL", "STREAMFLIX.COM"),
    amount = c(1000, -100, -15, -300, 1000, -50, -15, -20, 1000, -15),
    account = "Checking",
    stringsAsFactors = FALSE
  )
}

make_rules <- function() {
  data.frame(pattern = c("TRANSFER", "PAYROLL", "GROCERY", "STREAMFLIX"),
             category = c("Transfer", "Income", "Groceries", "Subscriptions"),
             priority = c(1, 5, 20, 10), stringsAsFactors = FALSE)
}
