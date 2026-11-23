# plots.R — base-graphics charts written to PNG files.
#
# Base graphics keep the project dependency-free (no ggplot2 needed), and
# every function returns the output path invisibly so callers can chain.

# A colour-blind-friendly qualitative palette (Okabe–Ito), recycled as needed.
PALETTE <- c("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9",
             "#D55E00", "#F0E442", "#999999", "#000000")

category_colours <- function(categories) {
  stats::setNames(rep_len(PALETTE, length(categories)), categories)
}

with_png <- function(path, width, height, expr) {
  grDevices::png(path, width = width, height = height, res = 110)
  on.exit(grDevices::dev.off())
  force(expr)
  invisible(path)
}

#' Horizontal bar chart of total spend by category.
plot_category_totals <- function(tx, path) {
  ct <- category_totals(tx)
  ct <- ct[rev(seq_len(nrow(ct))), ]  # largest at the top
  with_png(path, 900, 120 + 40 * nrow(ct), {
    op <- graphics::par(mar = c(4, 10, 3, 2)); on.exit(graphics::par(op), add = TRUE)
    bp <- graphics::barplot(ct$total, names.arg = ct$category, horiz = TRUE, las = 1,
                            col = category_colours(rev(ct$category)), border = NA,
                            main = "Spending by category", xlab = "Total spent")
    graphics::text(ct$total, bp, sprintf(" %.0f%%", 100 * ct$share), pos = 4, cex = 0.8,
                   xpd = TRUE)
  })
}

#' Stacked monthly bars, one segment per category.
plot_monthly_stacked <- function(tx, path) {
  m <- monthly_by_category(tx)
  m <- m[, order(-colSums(m)), drop = FALSE]
  cols <- category_colours(colnames(m))
  with_png(path, 1000, 600, {
    op <- graphics::par(mar = c(5, 5, 3, 10), xpd = TRUE); on.exit(graphics::par(op), add = TRUE)
    graphics::barplot(t(m), col = cols, border = NA, las = 2,
                      main = "Monthly spending by category", ylab = "Spent")
    graphics::legend("topright", inset = c(-0.22, 0), legend = colnames(m),
                     fill = cols, border = NA, bty = "n", cex = 0.8)
  })
}

#' Income vs spending lines with net cash flow bars.
plot_cashflow <- function(tx, path) {
  cf <- monthly_cashflow(tx)
  with_png(path, 1000, 550, {
    rng <- range(c(0, cf$income, cf$spending, cf$net))
    x <- seq_len(nrow(cf))
    graphics::plot(x, cf$income, type = "n", ylim = rng, xaxt = "n",
                   xlab = "", ylab = "Amount", main = "Monthly cash flow")
    graphics::rect(x - 0.3, 0, x + 0.3, cf$net,
                   col = ifelse(cf$net >= 0, "#009E7355", "#D55E0055"), border = NA)
    graphics::lines(x, cf$income, col = PALETTE[1], lwd = 2, type = "o", pch = 16)
    graphics::lines(x, cf$spending, col = PALETTE[6], lwd = 2, type = "o", pch = 16)
    graphics::abline(h = 0, col = "grey60")
    graphics::axis(1, at = x, labels = cf$month, las = 2, cex.axis = 0.8)
    graphics::legend("topleft", c("Income", "Spending", "Net"), bty = "n",
                     col = c(PALETTE[1], PALETTE[6], "#009E73"),
                     lwd = c(2, 2, 8), pch = c(16, 16, NA))
  })
}

#' Render all charts into `dir`; returns the paths written.
render_all_plots <- function(tx, dir) {
  dir.create(dir, showWarnings = FALSE, recursive = TRUE)
  c(plot_category_totals(tx, file.path(dir, "category_totals.png")),
    plot_monthly_stacked(tx, file.path(dir, "monthly_stacked.png")),
    plot_cashflow(tx, file.path(dir, "cashflow.png")))
}
