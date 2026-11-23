# analyze.R — split-apply-combine summaries over categorised transactions.
#
# All functions take the canonical, categorised data frame and return plain
# data frames, so they are easy to test, print, or plot.

#' "2026-03-14" -> "2026-03"
month_key <- function(dates) format(dates, "%Y-%m")

#' Total spend per category, sorted descending, with percentage share.
category_totals <- function(tx) {
  s <- spending_only(tx)
  if (nrow(s) == 0) {
    return(data.frame(category = character(), total = numeric(), share = numeric(),
                      n = integer(), stringsAsFactors = FALSE))
  }
  agg <- stats::aggregate(spend ~ category, data = s, FUN = sum)
  cnt <- stats::aggregate(spend ~ category, data = s, FUN = length)
  names(agg)[2] <- "total"
  agg$n <- cnt$spend[match(agg$category, cnt$category)]
  agg$share <- agg$total / sum(agg$total)
  agg <- agg[order(-agg$total, agg$category), c("category", "total", "share", "n")]
  rownames(agg) <- NULL
  agg
}

#' Month x category matrix of spend (a pivot table). Missing cells are 0.
monthly_by_category <- function(tx) {
  s <- spending_only(tx)
  if (nrow(s) == 0) return(matrix(numeric(), 0, 0))
  # tapply over two factors produces exactly the cross-tab we want.
  m <- tapply(s$spend, list(month_key(s$date), s$category), sum)
  m[is.na(m)] <- 0
  m[order(rownames(m)), , drop = FALSE]
}

#' Per-month income, spending, net cash flow and savings rate.
monthly_cashflow <- function(tx) {
  tx <- tx[!tx$category %in% TRANSFER_CATEGORIES, , drop = FALSE]
  months <- sort(unique(month_key(tx$date)))
  mk <- month_key(tx$date)
  income   <- vapply(months, function(m) sum(tx$amount[mk == m & tx$amount > 0]), numeric(1))
  spending <- vapply(months, function(m) -sum(tx$amount[mk == m & tx$amount < 0]), numeric(1))
  data.frame(
    month = months,
    income = unname(income),
    spending = unname(spending),
    net = unname(income - spending),
    savings_rate = unname(ifelse(income > 0, (income - spending) / income, NA_real_)),
    stringsAsFactors = FALSE
  )
}

#' Top-N merchants by total spend, grouped by normalised merchant key.
top_merchants <- function(tx, n = 10) {
  s <- spending_only(tx)
  if (nrow(s) == 0) return(data.frame(merchant = character(), total = numeric(), visits = integer()))
  s$merchant <- merchant_key(s$description)
  tot <- tapply(s$spend, s$merchant, sum)
  cnt <- tapply(s$spend, s$merchant, length)
  out <- data.frame(merchant = names(tot), total = as.numeric(tot),
                    visits = as.integer(cnt[names(tot)]), stringsAsFactors = FALSE)
  out <- out[order(-out$total, out$merchant), , drop = FALSE]
  rownames(out) <- NULL
  utils::head(out, n)
}

#' Compare average monthly spend per category against a budget table
#' (columns: category, monthly_budget). Status flags over/near/under.
budget_report <- function(tx, budgets, near = 0.9) {
  m <- monthly_by_category(tx)
  n_months <- max(1L, nrow(m))
  avg <- if (length(m)) colSums(m) / n_months else numeric()
  actual <- unname(avg[budgets$category])
  actual[is.na(actual)] <- 0
  used <- ifelse(budgets$monthly_budget > 0, actual / budgets$monthly_budget, NA_real_)
  status <- ifelse(is.na(used), "n/a",
            ifelse(used > 1, "OVER", ifelse(used >= near, "near", "ok")))
  data.frame(category = budgets$category, budget = budgets$monthly_budget,
             avg_actual = actual, used = used, status = status,
             stringsAsFactors = FALSE)
}

#' Detect recurring charges (subscriptions, rent, utilities).
#'
#' A merchant is recurring if it has >= min_count charges whose gaps between
#' consecutive dates are consistently near a known period (weekly, monthly,
#' yearly) and whose amounts are stable (coefficient of variation <= max_cv).
#' Gap regularity is tested with the median gap, which is robust to one
#' missed or doubled charge.
detect_recurring <- function(tx, min_count = 3, max_cv = 0.15, tolerance = 0.2) {
  periods <- c(weekly = 7, biweekly = 14, monthly = 30.44, yearly = 365.25)
  s <- spending_only(tx)
  if (nrow(s) == 0) return(data.frame())
  s$merchant <- merchant_key(s$description)
  rows <- lapply(split(s, s$merchant), function(g) {
    if (nrow(g) < min_count) return(NULL)
    g <- g[order(g$date), ]
    gaps <- as.numeric(diff(g$date))
    med_gap <- stats::median(gaps)
    # Which named period is the median gap closest to (relatively)?
    rel_err <- abs(med_gap - periods) / periods
    best <- which.min(rel_err)
    if (rel_err[best] > tolerance) return(NULL)
    # Most gaps must also individually fit the period.
    fits <- abs(gaps - periods[best]) / periods[best] <= tolerance * 1.5
    if (mean(fits) < 0.75) return(NULL)
    cv <- if (mean(g$spend) > 0) stats::sd(g$spend) / mean(g$spend) else Inf
    if (is.na(cv)) cv <- 0
    if (cv > max_cv) return(NULL)
    data.frame(merchant = g$merchant[1], category = names(which.max(table(g$category))),
               cadence = names(periods)[best], typical_amount = stats::median(g$spend),
               count = nrow(g), last_seen = max(g$date),
               annual_cost = stats::median(g$spend) * 365.25 / periods[[best]],
               stringsAsFactors = FALSE)
  })
  out <- do.call(rbind, rows)
  if (is.null(out)) return(data.frame())
  out <- out[order(-out$annual_cost), , drop = FALSE]
  rownames(out) <- NULL
  out
}

#' Flag unusually large transactions within each category using a robust
#' z-score: (x - median) / (1.4826 * MAD). MAD-based scores are not dragged
#' around by the very outliers we're trying to find, unlike mean/sd.
detect_anomalies <- function(tx, threshold = 3.5, min_group = 5) {
  s <- spending_only(tx)
  if (nrow(s) == 0) return(s[0, ])
  s$robust_z <- NA_real_
  for (cat_name in unique(s$category)) {
    idx <- which(s$category == cat_name)
    if (length(idx) < min_group) next
    x <- s$spend[idx]
    mad <- stats::mad(x)                # already scaled by 1.4826
    if (mad == 0) mad <- stats::sd(x)   # fall back for very uniform groups
    if (is.na(mad) || mad == 0) next
    s$robust_z[idx] <- (x - stats::median(x)) / mad
  }
  out <- s[!is.na(s$robust_z) & s$robust_z > threshold, , drop = FALSE]
  out <- out[order(-out$robust_z), c("date", "description", "category", "spend", "robust_z")]
  rownames(out) <- NULL
  out
}
