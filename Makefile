COMPOSE ?= docker compose

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) --profile runner build
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f --tail=100

migrate:
	$(COMPOSE) exec backend alembic upgrade head

seed:
	$(COMPOSE) exec backend python -m app.seed.seeder

test:
	cd backend && python -m pytest tests -q

.PHONY: up down build logs migrate seed test
