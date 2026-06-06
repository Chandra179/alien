# AGENTS.md

## Context of the Project

- Python: 3.13
- Package Manager: [uv](https://docs.astral.sh/uv/)

## Tooling & Environment
- This project uses `uv` for dependency and environment management.
- CRITICAL: Always use `uv run` to execute scripts, tests, or tools. Never use global `pytest` or `python`.

## Code Generation

For function signatures, include the type from `typing` package. Optional arguments should be put after mandatory arguments.

You have to add documentation for new functions and classes that you generate. For existing functions, update the documentation for functions and classes that you edit. The documentation should follow NumPy style. The documentation should contain what is the function for (basically the description), a brief summary of the steps, and input and output parameters. If your function has the ability to throw error, please state it in the documentation as well.

You have to add unit tests as well. Make sure to put unit tests in `tests` folder.

## Testing Standards

1. **Mandatory Coverage**: Every new feature or bug fix must include corresponding unit tests.
2. **Framework**: Use `pytest`. Prefer functional tests with fixtures over heavily mocked class-based tests.
3. **Async Code**: If testing async functions, use `@pytest.mark.anyio` or `@pytest.mark.asyncio` as appropriate for the project stack.
4. **Mocking**: Use `pytest-mock` (mocker fixture) instead of standard `unittest.mock` where possible for cleaner teardowns.

## Required Commands

- Lint code before committing: `make lint`
- Format code: `make lint/fix`
- Type-checking: `make ty`
- Run test suite: `make test`
