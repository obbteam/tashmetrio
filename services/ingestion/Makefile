include .env
export

DB_MODELS_PATH := src/adapters/common/models.py

install:
	uv sync --active
	uv lock

model-generate:
	sqlacodegen --generator declarative --outfile $(DB_MODELS_PATH) "$(SQLACODEGEN_URL)"
	ruff format $(DB_MODELS_PATH)

run:
	fastapi dev src/main.py --port=8091

simulate:
	python3 -m src.simulator_main

generate:
	python3 -m src.generator_main

seed-operation:
	python3 -m scripts.seed_operations

seed-topology:
	python3 -m scripts.seed_topology
	
kafka-topics:
	python3 -m scripts.create_kafka_topics