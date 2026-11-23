# io.R — loading and normalising transaction data.
#
# Banks export CSVs in wildly different shapes. Rather than special-casing
# each one, we accept a small set of column-name aliases, coerce types, and
# produce one canonical data frame:
#
#   date (Date) | description (chr) | amount (num, negative = money out) | account (chr)
#
# Everything downstream relies only on this canonical shape.

# Column-name aliases (lower-cased, punctuation stripped) -> canonical name.
COLUMN_ALIASES <- list(
  date        = c("date", "transactiondate", "posteddate", "postingdate", "txndate"),
  description = c("description", "memo", "payee", "merchant", "details", "name"),
  amount      = c("amount", "value", "transactionamount"),
  debit       = c("debit", "withdrawal", "moneyout"),
  credit      = c("credit", "deposit", "moneyin"),
  account     = c("account", "accountname", "card")
)

#' Normalise a raw column name for alias matching ("Posted Date" -> "posteddate").
normalise_name <- function(x) gsub("[^a-z0-9]", "", tolower(x))

#' Find which raw column (if any) maps onto a canonical field.
find_column <- function(raw_names, field) {
  hits <- which(normalise_name(raw_names) %in% COLUMN_ALIASES[[field]])
  if (length(hits) == 0) NA_character_ else raw_names[hits[1]]
}

#' Parse money strings like "$1,234.50", "(12.00)" or "-3.2" into numerics.
#' Accounting-style parentheses denote negatives.
parse_amount <- function(x) {
  if (is.numeric(x)) return(as.numeric(x))
  x <- trimws(as.character(x))
  neg <- grepl("^\\(.*\\)$", x)
  cleaned <- gsub("[$,()\\s]", "", x, perl = TRUE)
  cleaned[cleaned == ""] <- NA
  out <- suppressWarnings(as.numeric(cleaned))
  out[neg & !is.na(out)] <- -abs(out[neg & !is.na(out)])
  out
}

#' Parse dates in the common formats banks use. Tries each format in turn and
#' keeps the first one that parses every non-empty value.
parse_dates <- function(x, formats = c("%Y-%m-%d", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d")) {
  if (inherits(x, "Date")) return(x)
  x <- trimws(as.character(x))
  for (fmt in formats) {
    d <- as.Date(x, format = fmt)
    if (all(!is.na(d) | x == "" | is.na(x))) return(d)
  }
  stop("Could not parse dates; tried formats: ", paste(formats, collapse = ", "))
}

#' Convert an arbitrary bank-export data frame into the canonical shape.
#'
#' Supports either a single signed `amount` column or separate
#' `debit`/`credit` columns (debit becomes negative).
normalise_transactions <- function(raw, default_account = "default") {
  nm <- names(raw)
  col <- vapply(names(COLUMN_ALIASES), function(f) find_column(nm, f), character(1))

  if (is.na(col["date"]))        stop("No date column found")
  if (is.na(col["description"])) stop("No description column found")

  if (!is.na(col["amount"])) {
    amount <- parse_amount(raw[[col["amount"]]])
  } else if (!is.na(col["debit"]) || !is.na(col["credit"])) {
    debit  <- if (is.na(col["debit"]))  0 else parse_amount(raw[[col["debit"]]])
    credit <- if (is.na(col["credit"])) 0 else parse_amount(raw[[col["credit"]]])
    debit[is.na(debit)] <- 0
    credit[is.na(credit)] <- 0
    amount <- abs(credit) - abs(debit)
  } else {
    stop("No amount (or debit/credit) column found")
  }

  account <- if (is.na(col["account"])) rep(default_account, nrow(raw))
             else as.character(raw[[col["account"]]])

  tx <- data.frame(
    date        = parse_dates(raw[[col["date"]]]),
    description = trimws(as.character(raw[[col["description"]]])),
    amount      = amount,
    account     = account,
    stringsAsFactors = FALSE
  )
  tx <- tx[!is.na(tx$date) & !is.na(tx$amount), , drop = FALSE]
  tx <- tx[order(tx$date), , drop = FALSE]
  rownames(tx) <- NULL
  tx
}

#' Read a CSV export from disk and normalise it.
read_transactions <- function(path, ...) {
  raw <- utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE,
                         strip.white = TRUE)
  normalise_transactions(raw, ...)
}

#' Collapse merchant descriptions into a stable key so "AMAZON MKTPL*1A2B3"
#' and "Amazon Mktpl*9Z8Y" group together. Strips digits, reference codes and
#' punctuation, then keeps the first two words.
merchant_key <- function(description) {
  x <- toupper(description)
  x <- gsub("\\*.*$", "", x)            # drop "*REFCODE" suffixes
  x <- gsub("#\\s*\\w+", "", x)          # drop "#1234" store numbers
  x <- gsub("[0-9]+", "", x)
  x <- gsub("[^A-Z ]", " ", x)
  x <- gsub("\\s+", " ", trimws(x))
  words <- strsplit(x, " ", fixed = TRUE)
  vapply(words, function(w) paste(utils::head(w[nzchar(w)], 2), collapse = " "),
         character(1))
}
