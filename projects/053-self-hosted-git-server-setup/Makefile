# Convenience targets for the Gitea stack. Run `make help` for a list.
COMPOSE ?= docker compose
BACKUP  ?= latest

.PHONY: help env up down restart ps logs pull admin backup restore list-backups health test lint
help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

env: ## Create .env from the template with a random DB password
	@test ! -f .env || { echo ".env already exists"; exit 1; }
	@sed "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$$(openssl rand -hex 24)|" .env.example > .env
	@chmod 600 .env && echo "wrote .env"

up: ## Start Gitea + Postgres in the background
	$(COMPOSE) up -d
down: ## Stop and remove containers (volumes are kept)
	$(COMPOSE) down
restart: ## Restart the stack
	$(COMPOSE) restart
ps: ## Show service status and health
	$(COMPOSE) ps
logs: ## Follow logs
	$(COMPOSE) logs -f --tail=100
pull: ## Pull newer images for the pinned versions
	$(COMPOSE) pull

admin: ## Create an admin: make admin ADMIN_USER=omar ADMIN_EMAIL=omar@example.com
	scripts/create-admin.sh "$(ADMIN_USER)" "$(ADMIN_EMAIL)"

backup: ## Take a backup now (keeps newest BACKUP_KEEP)
	scripts/backup.sh
restore: ## Restore: make restore BACKUP=<file|latest>
	scripts/restore.sh "$(BACKUP)"
list-backups: ## List backup archives, oldest first
	@bash -c 'source scripts/lib/common.sh; list_backups "$${BACKUP_DIR:-./backups}"'
health: ## Check Gitea is up and the newest backup is fresh
	scripts/healthcheck.sh

test: ## Run the script/compose test suite (no running containers needed)
	bash tests/run.sh
lint: ## shellcheck all scripts
	shellcheck -x -S warning scripts/*.sh scripts/lib/common.sh tests/run.sh tests/stubs/fake-compose
