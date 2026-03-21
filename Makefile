.PHONY: start worker migrate infra-up infra-down

start:
	.venv/bin/python scripts/run_api.py

worker:
	.venv/bin/python scripts/run_worker.py

migrate:
	.venv/bin/alembic upgrade head

infra-up:
	docker compose -f compose.yaml up -d

infra-down:
	docker compose -f compose.yaml down
