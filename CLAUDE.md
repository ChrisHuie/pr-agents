# PR Agents Project

## Code Quality Standards
- Use Python 3.13
- Follow PEP 8 style guidelines
- Line length: 88 characters
- Use double quotes for strings
- Use type hints for all functions

## Development Workflow
- Always run code quality checks before completing tasks
- Format code with black: `uv run black .`
- Lint code with ruff: `uv run ruff check .`
- Run tests with pytest: `uv run pytest`

## Required Commands After Code Changes
When making code changes, ALWAYS run these commands in order:
1. `uv run black .` - Format code
2. `uv run ruff check .` - Check for linting issues
3. `uv run pytest` - Run all tests

If any of these commands fail, fix the issues before considering the task complete.

## Dependencies
- Use `uv` for dependency management
- Add new dependencies to pyproject.toml
- Keep dev dependencies separate in [dependency-groups.dev]

## Git Workflow
- Never commit without running the quality checks above
- Write clear, descriptive commit messages
- Only commit when explicitly asked by the user