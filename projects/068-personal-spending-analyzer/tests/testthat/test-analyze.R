tx_c <- function() categorize(make_tx(), make_rules())

test_that("category_totals sums spend and shares add to 1", {
  ct <- category_totals(tx_c())
  expect_equal(ct$category[1], "Groceries")
  expect_equal(ct$total[ct$category == "Groceries"], 150)
  expect_equal(ct$total[ct$category == "Subscriptions"], 45)
  expect_equal(ct$n[ct$category == "Subscriptions"], 3L)
  expect_equal(sum(ct$share), 1)
  expect_equal(nrow(category_totals(tx_c()[0, ])), 0)
})

test_that("monthly_by_category is a zero-filled month x category pivot", {
  m <- monthly_by_category(tx_c())
  expect_equal(rownames(m), c("2026-01", "2026-02", "2026-03"))
  expect_equal(unname(m["2026-03", "Groceries"]), 0)
  expect_equal(unname(m["2026-01", "Groceries"]), 100)
  expect_equal(sum(m), 215)
})

test_that("monthly_cashflow excludes transfers and computes savings rate", {
  cf <- monthly_cashflow(tx_c())
  jan <- cf[cf$month == "2026-01", ]
  expect_equal(jan$income, 1000)
  expect_equal(jan$spending, 115)   # the 300 transfer is excluded
  expect_equal(jan$net, 885)
  expect_equal(jan$savings_rate, 0.885)
})

test_that("top_merchants groups by merchant key and limits rows", {
  tm <- top_merchants(tx_c(), n = 2)
  expect_equal(nrow(tm), 2)
  expect_equal(tm$merchant[1], "FRESHMART GROCERY")
  expect_equal(tm$visits[1], 2L)
})

test_that("budget_report flags over / near / ok", {
  budgets <- data.frame(category = c("Groceries", "Subscriptions", "Dining"),
                        monthly_budget = c(40, 15, 100))
  br <- budget_report(tx_c(), budgets)
  # Groceries averages 150/3 = 50 > 40; Subscriptions 15/15 = 100% -> near; Dining 0.
  expect_equal(br$status, c("OVER", "near", "ok"))
  expect_equal(br$avg_actual, c(50, 15, 0))
})

monthly_series <- function(desc, amounts, start = as.Date("2026-01-05"), by = "month") {
  data.frame(date = seq(start, by = by, length.out = length(amounts)),
             description = desc, amount = -amounts, account = "a",
             category = "Subscriptions", stringsAsFactors = FALSE)
}

test_that("detect_recurring finds stable monthly and weekly charges", {
  tx <- rbind(monthly_series("STREAMFLIX.COM", rep(15.49, 6)),
              monthly_series("LAUNDRY CO", rep(8, 8), by = "week"))
  rec <- detect_recurring(tx)
  expect_setequal(rec$merchant, c("STREAMFLIX COM", "LAUNDRY CO"))
  expect_equal(rec$cadence[rec$merchant == "STREAMFLIX COM"], "monthly")
  expect_equal(rec$cadence[rec$merchant == "LAUNDRY CO"], "weekly")
  expect_equal(rec$annual_cost[rec$merchant == "STREAMFLIX COM"], 15.49 * 12, tolerance = 0.01)
})

test_that("detect_recurring ignores irregular timing and volatile amounts", {
  irregular <- data.frame(date = as.Date(c("2026-01-01", "2026-01-04", "2026-02-20", "2026-02-22")),
                          description = "TACO TOWN", amount = -10, account = "a",
                          category = "Dining", stringsAsFactors = FALSE)
  volatile <- monthly_series("CITY POWER", c(40, 120, 60, 150, 30))
  expect_equal(nrow(detect_recurring(rbind(irregular, volatile))), 0)
})

test_that("detect_anomalies uses robust z-scores within a category", {
  normal <- data.frame(date = as.Date("2026-01-01") + 0:9, description = "GROCER",
                       amount = -c(100, 104, 98, 110, 95, 102, 99, 105, 101, 97),
                       account = "a", category = "Groceries", stringsAsFactors = FALSE)
  spike <- normal[1, ]; spike$amount <- -400; spike$date <- as.Date("2026-01-20")
  an <- detect_anomalies(rbind(normal, spike))
  expect_equal(nrow(an), 1)
  expect_equal(an$spend, 400)
  expect_gt(an$robust_z, 3.5)
  # Groups smaller than min_group are never flagged.
  expect_equal(nrow(detect_anomalies(rbind(normal[1:3, ], spike))), 0)
})

test_that("sample data: known one-off spikes are flagged", {
  tx <- categorize(read_transactions(file.path(root, "inst", "extdata", "sample_transactions.csv")),
                   read_rules(file.path(root, "inst", "extdata", "rules.csv")))
  an <- detect_anomalies(tx)
  expect_true(all(c(412.80, 649.99, 186.40) %in% an$spend))
  rec <- detect_recurring(tx)
  expect_true(all(c("STREAMFLIX COM", "TUNEBOX MUSIC", "IRONWORKS GYM") %in% rec$merchant))
})
