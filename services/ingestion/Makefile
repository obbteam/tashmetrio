include .env
export

DB_MODELS_PATH := src/adapters/common/models.py

install:
	uv sync --active
	uv lock

generate:
	sqlacodegen --generator declarative --outfile $(DB_MODELS_PATH) "$(SQLACODEGEN_URL)"
	ruff format $(DB_MODELS_PATH)

run:
	fastapi dev src/main.py --port=8090

simulate:
	python3 -m src.simulator_main