# categorize.R — rule-based transaction categorisation.
#
# Rules are an ordered table of (pattern, category, priority). Each pattern is
# a case-insensitive regular expression matched against the description.
# The rule with the LOWEST priority number wins (ties broken by file order),
# so specific rules ("AMAZON PRIME" -> Subscriptions) can override general
# ones ("AMAZON" -> Shopping). Positive amounts with no matching rule are
# labelled Income; unmatched negatives become Uncategorized.

#' Load categorisation rules from CSV with columns pattern, category[, priority].
read_rules <- function(path) {
  rules <- utils::read.csv(path, stringsAsFactors = FALSE, strip.white = TRUE)
  validate_rules(rules)
}

#' Check rule table shape and that every pattern is a valid regex.
validate_rules <- function(rules) {
  missing <- setdiff(c("pattern", "category"), names(rules))
  if (length(missing)) stop("Rules missing column(s): ", paste(missing, collapse = ", "))
  if (!"priority" %in% names(rules)) rules$priority <- 100L
  rules$priority[is.na(rules$priority)] <- 100L
  for (p in rules$pattern) {
    ok <- tryCatch({ suppressWarnings(grepl(p, "", ignore.case = TRUE, perl = TRUE)); TRUE },
                   error = function(e) FALSE)
    if (!ok) stop("Invalid regex in rules: ", p)
  }
  # Stable sort by priority so earlier lines win ties.
  rules[order(rules$priority, seq_len(nrow(rules))), , drop = FALSE]
}

#' Assign a category to each transaction.
#'
#' Implementation: iterate over rules (usually tens) rather than transactions
#' (often thousands). Each rule is one vectorised grepl over all descriptions;
#' we only fill rows that are still unassigned, which gives first-match-wins
#' semantics in priority order.
categorize <- function(tx, rules) {
  rules <- validate_rules(rules)
  cat_out <- rep(NA_character_, nrow(tx))
  for (i in seq_len(nrow(rules))) {
    todo <- is.na(cat_out)
    if (!any(todo)) break
    hit <- grepl(rules$pattern[i], tx$description[todo], ignore.case = TRUE, perl = TRUE)
    cat_out[which(todo)[hit]] <- rules$category[i]
  }
  unmatched <- is.na(cat_out)
  cat_out[unmatched & tx$amount > 0]  <- "Income"
  cat_out[unmatched & tx$amount <= 0] <- "Uncategorized"
  tx$category <- cat_out
  tx
}

#' Categories considered transfers between own accounts; excluded from
#' spending and income totals so moving money doesn't look like spending.
TRANSFER_CATEGORIES <- c("Transfer")

#' Keep only real outflows (negative, non-transfer), as positive "spend".
spending_only <- function(tx) {
  out <- tx[tx$amount < 0 & !tx$category %in% TRANSFER_CATEGORIES, , drop = FALSE]
  out$spend <- -out$amount
  out
}
