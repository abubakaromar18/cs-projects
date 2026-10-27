.PHONY: help test up down logs ps smoke clean-volumes local config

help:            ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

test:            ## Run unit + integration tests (no Docker needed)
	cd tests && python3 -m unittest -v

config:          ## Validate and print the resolved compose file
	docker compose config

up:              ## Build images and start the stack in the background
	docker compose up --build -d --wait

down:            ## Stop and remove containers (volumes are kept)
	docker compose down

clean-volumes:   ## Stop everything AND delete the data volumes
	docker compose down -v

logs:            ## Follow logs from all three services
	docker compose logs -f

ps:              ## Show container status and health
	docker compose ps

smoke: up        ## Start the stack and run the end-to-end smoke test
	./scripts/smoke_test.sh

local:           ## Run the three services as local processes, no Docker
	python3 scripts/run_local.py
