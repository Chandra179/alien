-include .env
export

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

.PHONY: modal/run
modal/run:
	@uv run modal run src/alien_obfuscator/modal_serve.py

.PHONY: modal/deploy
modal/deploy:
	@uv run modal deploy src/alien_obfuscator/modal_serve.py

.PHONY: deploy/hf
deploy/hf:
	hf upload build-small-hackathon/alien-riddle ./ --type space \
		--exclude ".git/*" --exclude ".gitignore" \
		--exclude ".venv/*" --exclude ".env" --exclude ".env.example" \
		--exclude "__pycache__/*" --exclude "*.pyc" \
		--exclude ".pytest_cache/*" --exclude ".ruff_cache/*" \
		--exclude ".mypy_cache/*" --exclude ".coverage*" \
		--exclude "htmlcov/*" \
		--commit-message="deploy from GitHub"
