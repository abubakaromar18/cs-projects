#!/usr/bin/env Rscript
# Generate a deterministic, entirely fictional 6-month transaction history
# at inst/extdata/sample_transactions.csv. Re-run to regenerate.

set.seed(68)
start <- as.Date("2026-01-01"); end <- as.Date("2026-06-30")
days <- seq(start, end, by = "day")
rows <- list()
add <- function(date, desc, amount, account = "Checking") {
  rows[[length(rows) + 1]] <<- data.frame(Date = format(date, "%m/%d/%Y"),
    Description = desc, Amount = sprintf("%.2f", amount), Account = account)
}

for (m in 1:6) {
  first <- as.Date(sprintf("2026-%02d-01", m))
  add(first, "ACME CORP PAYROLL", 2650)
  add(first + 14, "ACME CORP PAYROLL", 2650)
  add(first, "MAPLE STREET APTS RENT", -1450)
  add(first + 4, "CITY POWER & LIGHT", -round(runif(1, 70, 85), 2))
  add(first + 9, "STREAMFLIX.COM", -15.49, "Visa")
  add(first + 11, "TUNEBOX MUSIC SUB", -10.99, "Visa")
  add(first + 17, "IRONWORKS GYM MEMBERSHIP", -39.00, "Visa")
  add(first + 20, "CELLCO WIRELESS", -55.00)
  add(first + 25, "TRANSFER TO SAVINGS", -500)
}
for (d in as.list(days)) {
  wd <- as.POSIXlt(d)$wday
  if (runif(1) < 0.55) add(d, sample(c("JOE'S COFFEE #12", "BEAN THERE CAFE*A1B2"), 1),
                           -round(runif(1, 3.5, 7), 2), "Visa")
  if (wd == 6) add(d, sample(c("FRESHMART GROCERY #0042", "GREENLEAF MARKET"), 1),
                   -round(rnorm(1, 110, 18), 2), "Visa")
  if (runif(1) < 0.18) add(d, sample(c("TACO TOWN", "PIZZA PALACE", "NOODLE BAR*ORDER"), 1),
                           -round(runif(1, 12, 38), 2), "Visa")
  if (runif(1) < 0.12) add(d, sample(c("QUICKFUEL GAS #881", "METRO TRANSIT FARE"), 1),
                           -round(runif(1, 2.75, 48), 2), "Visa")
  if (runif(1) < 0.07) add(d, sample(c("MEGAMART ONLINE*XY12", "BOOKNOOK STORE"), 1),
                           -round(runif(1, 15, 90), 2), "Visa")
}
# A couple of one-offs the anomaly detector should notice.
add(as.Date("2026-03-21"), "FRESHMART GROCERY #0042", -412.80, "Visa")
add(as.Date("2026-05-02"), "PIZZA PALACE", -186.40, "Visa")
add(as.Date("2026-04-10"), "MEGAMART ONLINE*TV55", -649.99, "Visa")
add(as.Date("2026-02-14"), "TAX REFUND IRS TREAS", 812.00)
add(as.Date("2026-06-12"), "CITY DENTAL CARE", -180.00)

tx <- do.call(rbind, rows)
tx <- tx[order(as.Date(tx$Date, "%m/%d/%Y")), ]
out <- file.path("inst", "extdata", "sample_transactions.csv")
utils::write.csv(tx, out, row.names = FALSE)
cat("wrote", nrow(tx), "rows to", out, "\n")
