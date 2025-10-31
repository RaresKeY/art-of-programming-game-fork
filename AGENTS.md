# Repository Guidelines

This repository collects course modules, classroom drafts, and the Delivery Fleet simulation used in the Art of Programming curriculum. Keep contributions scoped and well-documented so instructors and students can reuse them effortlessly.

## Project Structure & Module Organization
Top-level folders prefixed with numbers (for example `05_functions`, `10_advanced_algorithms`) hold curriculum content. Each module usually contains `live_session/` walkthrough code, `drafts/` reference snippets, and assets such as slides or images. Core gameplay code lives in `10_advanced_algorithms/delivery_fleet_game/src/`, with supporting JSON data in `data/` and specs in `ARCHITECTURE.md`. Experimentation sandboxes are under `10_advanced_algorithms/codex_stress_testing`, and student submissions reside in `Students Tasks/`—do not overwrite another learner’s work without coordination.

## Build, Test, and Development Commands
Use Python 3.10+. For the fleet game, install optional tooling with `pip install -r 10_advanced_algorithms/delivery_fleet_game/requirements.txt`. Run the console simulation via `python 10_advanced_algorithms/delivery_fleet_game/main.py`. Execute automated checks with `python -m pytest 10_advanced_algorithms/delivery_fleet_game/tests`. When editing documentation only, no build step is required; otherwise keep command outputs in your PR description.

## Coding Style & Naming Conventions
Write Python that passes PEP 8: 4-space indentation, `snake_case` for functions and modules, `CamelCase` for classes, and expressive docstrings mirroring the existing modules. Prefer dataclasses for immutable models, and keep type hints consistent with the codebase. When modifying JSON scenarios, preserve keys’ snake_case naming and keep values human-auditable. If formatting drifts, run `black` and `isort` locally even though they are optional dependencies.

## Testing Guidelines
Unit tests live in `10_advanced_algorithms/delivery_fleet_game/tests`, organized per feature (for example `test_game_state.py`). Add new tests alongside the code they verify and use existing fixtures from `tests/conftest.py` to avoid duplication. Name files `test_<feature>.py`, and keep assertions precise with `pytest.approx` for floating-point checks. Document any new datasets or scenarios in a docstring within the test module, and mention coverage deltas in your PR if you touch logic-heavy areas.

## Commit & Pull Request Guidelines
Follow Conventional Commit prefixes (`feat:`, `refactor:`, `fix:`, `docs:`, etc.) as seen in recent history. Keep commits scoped to a single concern and include brief context in the body when touching shared curricula. Pull requests should link to the relevant module or issue, describe testing performed (`pytest`, manual run, or docs-only), and attach screenshots or terminal transcripts when altering interactive flows. Request review from the module maintainer and wait for CI (when available) before merge.
