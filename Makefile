.PHONY: test lint check

test:
	uv tool run pytest

lint:
	uv tool run ruff check .
	uv tool run pyright

check: lint test