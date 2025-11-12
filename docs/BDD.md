## Behavior-Driven Development

The BDD pipeline, defined in `.github/workflows/bdd.yml`, runs end-to-end tests on `push` and `pull_request` to the `master` branch.

### Workflow

1.  **Setup**: The job runs in a `quay.io/rofrano/pipeline-selenium:sp25` container with a `postgres:15-alpine` service.
2.  **Install Dependencies**: Installs Python packages using `pipenv`.
3.  **Run Service**: Starts the application locally with `gunicorn`.
4.  **Run BDD Tests**: Executes `behave` tests using the Chrome driver.