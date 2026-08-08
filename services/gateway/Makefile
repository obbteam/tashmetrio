include .env
export

DB_MODELS_PATH := src/adapters/common/models.py

install:
	uv sync --active
	uv lock

run:
	python3 -m src.main