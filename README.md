# Promotions Service

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Language-Python-blue.svg)](https://python.org/)
[![Build Status](https://github.com/CSCI-GA-2820-FA25-003/promotions/actions/workflows/workflow.yml/badge.svg)](https://github.com/CSCI-GA-2820-FA25-003/promotions/actions)
[![codecov](https://codecov.io/gh/CSCI-GA-2820-FA25-003/promotions/graph/badge.svg?token=FS7IXVUIWI)](https://codecov.io/gh/CSCI-GA-2820-FA25-003/promotions)

A production-style REST API for managing promotions, built with Python and Flask.

This service provides a robust and consistent API for CRUD operations and querying of promotion records. It emphasizes clear and explicit API design, moving away from ambiguous legacy concepts.

## Key Features

*   **Predictable API**: Easy to integrate with consistent behavior and clear filtering.
*   **Data Integrity**: Ensures valid data entry and reliable, atomic transactions.
*   **Flexible Management**: Safely deactivate promotions while preserving history.
*   **High Availability**: Designed for robust operation in cloud environments.

## Technology Stack

*   **Backend**: Python, Flask, Flask-SQLAlchemy
*   **Database**: PostgreSQL
*   **Containerization**: Docker
*   **CI/CD**: GitHub Actions
*   **Testing**: PyTest, Behave, Codecov

## Quick Start

1.  **Open in VS Code DevContainer**:
    *   Open the Command Palette (Ctrl+Shift+P or Cmd+Shift+P) and select "Dev Containers: Reopen in Container".
    *   This will build the development container and open the project inside it, with all necessary dependencies pre-installed.

2.  **Initialize the database**:
    ```bash
    # Create database tables
    flask db-create

    # Load sample data for testing(optional)
    flask load-data
    ```
    
3.  **Run the server**:
    ```bash
    flask run
    ```
    The service will be available at `http://127.0.0.1:8080` by default.

4.  **Check syntax**:
    ```bash
    make lint
    ```

5.  **Run tests**:
    ```bash
    make test
    ```
6.  **Run BDD tests**:
    ```bash
    behave
    ```

---

## Documentation

* [Architecture](docs/ARCHITECTURE.md)
* [API Reference](docs/API.md)
* [Deployment Guide](docs/DEPLOYMENT.md)
* [Minikube Guide](docs/MINIKUBE.md)
* [Testing Guide](docs/TESTING.md)
* [CI Commands](docs/CI.md)

---

## Project Structure

```
service/
  __init__.py
  routes.py          # REST endpoints and filter priority
  models.py          # Promotion model + unified query contract
  common/
    status.py        # HTTP status codes
    error_handlers.py
    log_handlers.py
    cli_commands.py
tests/
  test_models.py     # Model behavior, queries, validation, exceptions
  test_routes.py     # Routes, filters, errors, 500 simulation
  test_cli_commands.py
wsgi.py              # App entry (Flask)
Makefile
requirements.txt
README.md            # This file
```

## License

Copyright (c) 2016, 2025 [John Rofrano](https://www.linkedin.com/in/JohnRofrano/). All rights reserved.


Licensed under the Apache License. See [LICENSE](LICENSE)

This repository is part of the New York University (NYU) masters class: **CSCI-GA.2820-001 DevOps and Agile Methodologies** created and taught by [John Rofrano](https://cs.nyu.edu/~rofrano/), Adjunct Instructor, NYU Courant Institute, Graduate Division, Computer Science, and NYU Stern School of Business.