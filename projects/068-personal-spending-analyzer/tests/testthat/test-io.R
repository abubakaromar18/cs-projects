test_that("parse_amount handles currency symbols, commas and parentheses", {
  expect_equal(parse_amount(c("$1,234.50", "(12.00)", "-3.2", "7", "")),
               c(1234.5, -12, -3.2, 7, NA))
  expect_equal(parse_amount(c(1, -2)), c(1, -2))
})

test_that("parse_dates detects the format", {
  expect_equal(parse_dates(c("03/14/2026", "12/01/2025")),
               as.Date(c("2026-03-14", "2025-12-01")))
  expect_equal(parse_dates("2026-03-14"), as.Date("2026-03-14"))
  expect_equal(parse_dates("14.03.2026"), as.Date("2026-03-14"))
  expect_error(parse_dates("not a date"), "Could not parse")
})

test_that("normalise_transactions maps aliased columns and sorts by date", {
  raw <- data.frame(`Posted Date` = c("2026-02-01", "2026-01-01"),
                    Payee = c(" B ", "A"), Amount = c("-5.00", "$10"),
                    check.names = FALSE, stringsAsFactors = FALSE)
  tx <- normalise_transactions(raw)
  expect_equal(names(tx), c("date", "description", "amount", "account"))
  expect_equal(tx$description, c("A", "B"))
  expect_equal(tx$amount, c(10, -5))
  expect_equal(tx$account, c("default", "default"))
})

test_that("debit/credit columns become a signed amount", {
  raw <- data.frame(Date = c("2026-01-01", "2026-01-02"), Memo = c("x", "y"),
                    Debit = c("25.00", ""), Credit = c("", "100.00"),
                    stringsAsFactors = FALSE)
  expect_equal(normalise_transactions(raw)$amount, c(-25, 100))
})

test_that("missing required columns raise clear errors", {
  expect_error(normalise_transactions(data.frame(Memo = "x", Amount = 1)), "date")
  expect_error(normalise_transactions(data.frame(Date = "2026-01-01", Amount = 1)), "description")
  expect_error(normalise_transactions(data.frame(Date = "2026-01-01", Memo = "x")), "amount")
})

test_that("read_transactions round-trips through a CSV file", {
  f <- tempfile(fileext = ".csv")
  writeLines(c("Date,Description,Amount", "01/05/2026,COFFEE,-4.50"), f)
  tx <- read_transactions(f)
  expect_equal(tx$date, as.Date("2026-01-05"))
  expect_equal(tx$amount, -4.5)
})

test_that("merchant_key collapses reference codes and store numbers", {
  expect_equal(merchant_key(c("AMAZON MKTPL*1A2B3", "Amazon Mktpl*9Z8Y")),
               c("AMAZON MKTPL", "AMAZON MKTPL"))
  expect_equal(merchant_key("FRESHMART GROCERY #0042 SPRINGFIELD"), "FRESHMART GROCERY")
  expect_equal(merchant_key("STREAMFLIX.COM"), "STREAMFLIX COM")
})
