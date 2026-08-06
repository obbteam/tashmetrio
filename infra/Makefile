.PHONY: up down logs psql migrate-up migrate-down migrate-status
 
include .env
export
 
up:
	docker compose up -d
	@echo "Waiting for Postgres to be healthy..."
	@until docker compose exec -T db pg_isready -U $(POSTGRES_USER) -d $(POSTGRES_DB) > /dev/null 2>&1; do sleep 1; done
	@echo "Postgres is up on localhost:$(POSTGRES_PORT)"
	@echo "Redis is up on localhost:$(REDIS_PORT)"
	@echo "Kafka is up on localhost:$(KAFKA_PORT)"

 
down:
	docker compose down
 
logs:
	docker compose logs -f
 
psql:
	docker compose exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)
 
migrate-create:
	goose -s -dir migrations postgres "$(DATABASE_URL)" create migration sql

migrate-up:
	goose -dir migrations postgres "$(DATABASE_URL)" up
 
migrate-down:
	goose -dir migrations postgres "$(DATABASE_URL)" down
 
migrate-status:
	goose -dir migrations postgres "$(DATABASE_URL)" status
 
