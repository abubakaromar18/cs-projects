R ?= Rscript
DATA ?= inst/extdata/sample_transactions.csv

.PHONY: run plots sample deps test clean

run:            ## print the text report for the sample data
	$(R) bin/analyze.R --budgets inst/extdata/budgets.csv $(DATA)

plots:          ## report + PNG charts in ./output and a categorised CSV
	$(R) bin/analyze.R --budgets inst/extdata/budgets.csv --plots output \
		--out output/categorized.csv $(DATA)

sample:         ## regenerate the fictional sample transactions
	$(R) bin/make_sample_data.R

deps:           ## install the only dependency (tests)
	$(R) -e 'if (!requireNamespace("testthat", quietly = TRUE)) install.packages("testthat", repos = "https://cloud.r-project.org")'

test:
	$(R) tests/testthat.R

clean:
	rm -rf output Rplots.pdf
