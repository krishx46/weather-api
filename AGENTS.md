# AI Agent Guidelines (`AGENTS.md`)

## Project Overview

This repository contains the **Async Weather & Flight Advisory CLI**, a Python tool that asynchronously fetches weather forecasts for target cities and calculates flight risk advisories.

This file defines the mandatory operating rules for AI coding agents (e.g. ChatGPT Codex) working in this repository. Task prompts say *what* to build; this file says *how* to work.

---

## 1. Operating Principles

* **Match existing patterns**: Inspect existing files in `src/weather_api/` and copy their style, naming, and module boundaries before writing new code.
* **No comment slop**: Do not write comments that narrate obvious code or excuse workarounds. Write self-explanatory code.
* **No escape hatches**: Never add `# type: ignore`, `# noqa`, or any inline suppression. Fix the root cause in code or type definitions.
* **Never edit guardrail configs**: Do not modify the `[tool.*]` sections of `pyproject.toml`, `.pre-commit-config.yaml`, or import-linter contracts to make a check pass. If a rule seems wrong, stop and tell the user.
* **Absolute imports only**: Use `from weather_api.models import ...`. Relative imports are banned.
* **No `print` in `src/`**: Output belongs in `scripts/` only.
* **No new top-level directories or modules** unless the task explicitly requires them.

---

## 2. Environment and Dependencies (uv)

This project uses **uv**. The environment lives in `.venv` and is pinned by `uv.lock`.

* **Run every command through `uv run`** (for example `uv run pytest`). Never call `ruff`, `mypy`, or `pytest` directly, never activate the environment manually, and never use `pip`.
* **Add dependencies only with `uv add <package>`** (or `uv add --dev <package>` for dev tools). Never hand-edit `uv.lock`, and never edit the dependency lists in `pyproject.toml` by hand.
* **Mention every dependency you add** in your final report, with the reason.
* Prefer the standard library and existing dependencies over adding new ones.

---

## 3. Project Architecture

```
src/weather_api/
├── __init__.py
├── models.py      # Pydantic schemas only. Imports nothing from client, adviser or service.
├── client.py      # Async httpx network calls only. No decision logic.
├── adviser.py     # Flight risk decision logic only. Never imports client.
└── service.py     # Orchestration and report formatting. Imports client, adviser, models. No printing.
tests/             # Automated tests
scripts/
└── advise.py      # CLI entry point (printing allowed here). Calls service only.
```

Boundaries are enforced by `lint-imports`. Put new logic in the module whose single responsibility it matches.

---

## 4. Mandatory Verification (run in order before declaring any task done)

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run lint-imports
uv run pytest
```

All five must pass. Do not report a task as complete until they do.

---

## 5. Testing Rules

* **No real network calls in tests.** Mock HTTP with `httpx.MockTransport`.
* Async tests run under `asyncio_mode = "auto"`; do not add manual event-loop code.
* Expected values in assertions must come from the task requirements, not from running the code and copying its output.
* For decision logic in `adviser.py`, add property-based tests with Hypothesis (for example: output is always a valid risk level and never raises).
* Every bug fix gets a regression test that fails without the fix.

---

## 6. Self-Correction Protocol

If any verification command fails:

1. Read the exact error output, line numbers, and error codes.
2. Fix the root cause in application code or type annotations.
3. Re-run the failing command, then re-run the full pipeline.
4. After three failed attempts at the same error, stop and report what you tried instead of working around it.

---

## 7. Definition of Done

When finishing, report:

* What changed and in which files.
* The result of each of the five verification commands.
* Any dependencies added, and why.
* Any assumptions you made or anything you were unsure about.
