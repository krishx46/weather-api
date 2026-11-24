# Async Weather & Flight Advisory CLI

[![CI](https://github.com/krishx46/weather-api/actions/workflows/ci.yml/badge.svg)](https://github.com/krishx46/weather-api/actions/workflows/ci.yml)

This learning project is an asynchronous command-line tool that uses Open-Meteo's current-weather endpoints (with no API key) to fetch conditions for one or more cities and give each a `LOW`, `MEDIUM`, or `HIGH` flight-risk advisory. It is not an aviation safety tool and must not be used for operational flight decisions.

## Install and run

```bash
uv sync
uv run python scripts/advise.py Dubai London
```

The report always uses this column format; the live risk and details depend on current conditions.

```text
CITY                 RISK     DETAILS
Dubai                LOW      -
London               HIGH     Wind gusts: 60 km/h; Precipitation: 5 mm
```

## Risk rules

- `HIGH`: wind gusts of at least 60 km/h, precipitation of at least 5 mm, or weather code 95, 96, or 99.
- `MEDIUM`: otherwise, wind gusts of at least 40 km/h or precipitation of at least 1 mm.
- `LOW`: all other conditions.

## Exit codes

- `0`: every requested city produced an advisory.
- `1`: at least one city produced an error.

## Project layout

- `src/weather_api/models.py`: Pydantic data models.
- `src/weather_api/client.py`: asynchronous Open-Meteo requests.
- `src/weather_api/adviser.py`: flight-risk decisions.
- `src/weather_api/service.py`: orchestration and report formatting.
- `scripts/advise.py`: command-line entry point.

Import-linter enforces the layering: `service` may depend on `client`, `adviser`, and `models`; `client` and `adviser` may depend on `models`; models are a leaf layer. The adviser cannot depend on the client.

## Development

Install the pre-commit hooks:

```bash
uv run pre-commit install
```

Run the required checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run lint-imports
uv run pytest
```

GitHub Actions runs on pushes to `main` and pull requests. Its `checks` job syncs the locked dependencies, rejects `type: ignore` and `noqa` comments in `src`, `tests`, and `scripts`, then runs the same lint, format, type, import-boundary, and test checks.
