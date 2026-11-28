.PHONY: setup lint test verify schemas build-ui run-hub

setup:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest -v

schemas:
	uv run python -m aarogya_contracts.export_schemas

verify:
	uv run python -m aarogya_contracts.export_schemas --check
	uv run ruff check .
	uv run pytest -v

build-ui:
	@[ -f apps/field-pwa/dist/app.js ] || (cd apps/field-pwa && npm ci && npm run build)
	@[ -f apps/watch-companion/dist/watch.js ] || (cd apps/watch-companion && npm ci && npm run build)
	@[ -f apps/presentation/dist/index.html ] || (cd apps/presentation && npm ci && npm run build)

run-hub: build-ui
	uv run uvicorn aarogya_phc_hub.app:app --host 0.0.0.0 --port 8000 --reload
