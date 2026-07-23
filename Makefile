.PHONY: up down test test-back test-front lint demo

up:
	docker compose up -d

down:
	docker compose down

test: test-back test-front

test-back:
	cd backend && uv run pytest -m "not integration"

test-front:
	cd frontend && npm test

lint:
	cd backend && uv run ruff check .
	cd frontend && npm run lint

demo: up
