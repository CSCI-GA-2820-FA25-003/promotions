## Continuous Integration

The CI pipeline, defined in `.github/workflows/workflow.yml`, automates quality checks on `push` and `pull_request` to `master` and `milestone/**` branches.

### Workflow

1.  **Setup**: The job runs in a `python:3.11-slim` container with a `postgres:15-alpine` service.
2.  **Install Dependencies**: Installs Python packages using `pipenv`.
3.  **Linting**: Enforces code style with `flake8` and `pylint`.
4.  **Testing**: Runs `pytest` and checks for test coverage (≥ 95%).
5.  **Codecov**: Uploads coverage reports to Codecov.
