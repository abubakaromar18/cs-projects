# Run with: Rscript tests/testthat.R   (or `make test`)
library(testthat)
test_dir(file.path("tests", "testthat"), reporter = "summary", stop_on_failure = TRUE)
