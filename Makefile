.PHONY: validate test lint check

validate:
	uv run --locked python -m ztwf .

test:
	uv run --locked pytest -q

lint:
	uv run --locked ruff check src tests

check: validate test lint
