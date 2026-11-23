# report.R — plain-text report assembled from the analysis functions.

fmt_money <- function(x) formatC(x, format = "f", digits = 2, big.mark = ",")
fmt_pct   <- function(x) ifelse(is.na(x), "  n/a", sprintf("%5.1f%%", 100 * x))

#' Render a data frame as an aligned text table (no external deps).
text_table <- function(df) {
  if (nrow(df) == 0) return("  (none)")
  cells <- rbind(names(df), as.matrix(format(df, trim = TRUE)))
  widths <- apply(nchar(cells), 2, max)
  lines <- apply(cells, 1, function(r) paste0("  ", paste(sprintf("%-*s", widths, r),
                                                          collapse = "  ")))
  c(lines[1], paste0("  ", paste(strrep("-", widths), collapse = "  ")), lines[-1])
}

section <- function(title) c("", title, strrep("=", nchar(title)))

#' Build the full report as a character vector of lines.
build_report <- function(tx, budgets = NULL, top_n = 8) {
  cf <- monthly_cashflow(tx)
  total_in  <- sum(cf$income); total_out <- sum(cf$spending)
  out <- c(
    "PERSONAL SPENDING REPORT",
    sprintf("Period: %s to %s  (%d transactions, %d months)",
            min(tx$date), max(tx$date), nrow(tx), nrow(cf)),
    sprintf("Income: %s   Spending: %s   Net: %s   Savings rate: %s",
            fmt_money(total_in), fmt_money(total_out), fmt_money(total_in - total_out),
            trimws(fmt_pct(if (total_in > 0) (total_in - total_out) / total_in else NA)))
  )

  ct <- category_totals(tx)
  ct_show <- data.frame(category = ct$category, total = fmt_money(ct$total),
                        share = fmt_pct(ct$share), txns = ct$n)
  out <- c(out, section("Spending by category"), text_table(ct_show))

  cf_show <- data.frame(month = cf$month, income = fmt_money(cf$income),
                        spending = fmt_money(cf$spending), net = fmt_money(cf$net),
                        saved = fmt_pct(cf$savings_rate))
  out <- c(out, section("Monthly cash flow"), text_table(cf_show))

  tm <- top_merchants(tx, top_n)
  tm$total <- fmt_money(tm$total)
  out <- c(out, section(sprintf("Top %d merchants", top_n)), text_table(tm))

  if (!is.null(budgets)) {
    br <- budget_report(tx, budgets)
    br_show <- data.frame(category = br$category, budget = fmt_money(br$budget),
                          avg_month = fmt_money(br$avg_actual), used = fmt_pct(br$used),
                          status = br$status)
    out <- c(out, section("Budget vs. average month"), text_table(br_show))
  }

  rec <- detect_recurring(tx)
  if (nrow(rec)) {
    rec <- data.frame(merchant = rec$merchant, cadence = rec$cadence,
                      amount = fmt_money(rec$typical_amount), count = rec$count,
                      per_year = fmt_money(rec$annual_cost))
  }
  out <- c(out, section("Recurring charges"), text_table(rec))

  an <- detect_anomalies(tx)
  if (nrow(an)) {
    an <- data.frame(date = format(an$date), description = an$description,
                     category = an$category, amount = fmt_money(an$spend),
                     z = sprintf("%.1f", an$robust_z))
  }
  out <- c(out, section("Unusually large transactions"), text_table(an))
  out
}
