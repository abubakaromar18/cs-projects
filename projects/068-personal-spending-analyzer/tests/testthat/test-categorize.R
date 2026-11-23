test_that("rules assign categories and unmatched rows fall back by sign", {
  tx <- categorize(make_tx(), make_rules())
  expect_equal(tx$category[tx$description == "MYSTERY SHOP"], "Uncategorized")
  expect_true(all(tx$category[grepl("PAYROLL", tx$description)] == "Income"))
  expect_equal(unique(tx$category[grepl("STREAMFLIX", tx$description)]), "Subscriptions")

  pos <- data.frame(date = Sys.Date(), description = "RANDOM REFUND", amount = 5,
                    account = "a", stringsAsFactors = FALSE)
  expect_equal(categorize(pos, make_rules())$category, "Income")
})

test_that("lower priority number wins regardless of file order", {
  rules <- data.frame(pattern = c("AMAZON", "AMAZON PRIME"),
                      category = c("Shopping", "Subscriptions"),
                      priority = c(50, 10), stringsAsFactors = FALSE)
  tx <- data.frame(date = Sys.Date() + 0:1, description = c("AMAZON PRIME", "AMAZON MKTPL"),
                   amount = c(-15, -30), account = "a", stringsAsFactors = FALSE)
  expect_equal(categorize(tx, rules)$category, c("Subscriptions", "Shopping"))
})

test_that("ties in priority are broken by rule order and matching is case-insensitive", {
  rules <- data.frame(pattern = c("cafe", "CAFE"), category = c("First", "Second"),
                      stringsAsFactors = FALSE)
  tx <- data.frame(date = Sys.Date(), description = "Corner Cafe", amount = -3,
                   account = "a", stringsAsFactors = FALSE)
  expect_equal(categorize(tx, rules)$category, "First")
})

test_that("invalid rules are rejected", {
  expect_error(validate_rules(data.frame(pattern = "x")), "category")
  expect_error(validate_rules(data.frame(pattern = "([", category = "x")), "Invalid regex")
})

test_that("spending_only drops income and transfers and flips sign", {
  s <- spending_only(categorize(make_tx(), make_rules()))
  expect_false(any(s$category %in% c("Transfer", "Income")))
  expect_true(all(s$spend > 0))
  expect_equal(sum(s$spend), 100 + 15 + 50 + 15 + 20 + 15)
})

test_that("bundled rules file loads and categorises the sample data fully", {
  rules <- read_rules(file.path(root, "inst", "extdata", "rules.csv"))
  tx <- categorize(read_transactions(file.path(root, "inst", "extdata",
                                               "sample_transactions.csv")), rules)
  expect_equal(sum(tx$category == "Uncategorized"), 0)
})
