.PHONY: start
start:
	@uv run app.py

.PHONY: test
test:
	@uv run pytest tests/ -v

.PHONY: test/coverage
test/coverage:
	@uv run pytest --cov=alien_obfuscator --cov-report=term-missing tests/ -v

.PHONY: test/report
test/report:
	@uv run pytest --cov=alien_obfuscator --cov-report=html tests/ -v

.PHONY: lint
lint:
	@uv run ruff check

.PHONY: lint/fix
lint/fix:
	@uv run ruff format

.PHONY: ty
ty:
	@uv run ty check

.PHONY: req/generate
req/generate:
	@uv pip compile pyproject.toml -o requirements.txt
