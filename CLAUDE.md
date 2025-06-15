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

## Logging Standards
- Use loguru for all logging throughout the codebase
- Import logging utilities from `src.pr_agents.logging_config`
- Follow established logging patterns:
  - Use `log_processing_step()` for major operation milestones
  - Use `log_data_flow()` to track data transformations
  - Use `log_api_call()` for external API interactions
  - Use `log_error_with_context()` for error handling
- Sensitive data is automatically sanitized in logs
- Respect environment-aware logging (dev/staging/prod)

## Code Documentation Standards
All code must be consistently documented inline:

### Required for All Functions/Classes
- **Docstrings**: Follow existing project style with clear purpose, Args, Returns
- **Type hints**: Complete type annotations for all function parameters and returns
- **Consistent style**: Match existing docstring format in the codebase

### README Updates
Update README.md only when changes affect:
- Installation, setup, or environment configuration
- User-facing features or API usage
- New environment variables or configuration options
- Core functionality that users need to understand

### Documentation Consistency
- Follow existing patterns and style in the codebase
- Keep docstrings concise but complete
- Include practical examples only when they clarify complex usage