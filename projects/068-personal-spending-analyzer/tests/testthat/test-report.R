test_that("text_table aligns columns and handles empty frames", {
  lines <- text_table(data.frame(a = c("x", "long"), b = c(1, 22)))
  expect_length(lines, 4)
  expect_equal(length(unique(nchar(lines))), 1)  # every row the same width
  expect_equal(text_table(data.frame()), "  (none)")
})

test_that("build_report contains every section", {
  tx <- categorize(make_tx(), make_rules())
  budgets <- data.frame(category = "Groceries", monthly_budget = 40)
  rep <- build_report(tx, budgets)
  for (h in c("PERSONAL SPENDING REPORT", "Spending by category", "Monthly cash flow",
              "Top 8 merchants", "Budget vs. average month", "Recurring charges",
              "Unusually large transactions")) {
    expect_true(any(grepl(h, rep, fixed = TRUE)), info = h)
  }
  expect_true(any(grepl("STREAMFLIX COM", rep)))
})

test_that("render_all_plots writes non-empty PNGs", {
  skip_if_not(capabilities("png"), "PNG device unavailable")
  tx <- categorize(make_tx(), make_rules())
  dir <- file.path(tempdir(), "plots-test")
  paths <- render_all_plots(tx, dir)
  expect_length(paths, 3)
  expect_true(all(file.exists(paths)))
  expect_true(all(file.size(paths) > 1000))
})

test_that("CLI runs end to end on the sample data", {
  out <- tempfile(fileext = ".csv")
  res <- system2(file.path(R.home("bin"), "Rscript"),
                 c(file.path(root, "bin", "analyze.R"), "--out", out, "--top", "3",
                   file.path(root, "inst", "extdata", "sample_transactions.csv")),
                 stdout = TRUE, stderr = TRUE)
  expect_true(any(grepl("Top 3 merchants", res)))
  expect_true(file.exists(out))
  expect_true("category" %in% names(utils::read.csv(out)))
})
