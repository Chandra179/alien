.PHONY: start
start:
	@uv run app.py

.PHONY: test
test:
	@uv run pytest tests/ -v

.PHONY: lint
lint:
	@uv run ruff check

.PHONY: lint/fix
lint/fix:
	@uv run ruff format


.PHONY: ty
ty:
	@uv run ty check
