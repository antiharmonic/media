# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Personal media tracking app (books, movies, TV, anime, music, etc.) — a single-user Flask app backed by PostgreSQL. There are no tests, linter, or build step.

## Running

- **Production / normal use:** `docker-compose up -d --build`. This brings up two containers, both on host networking:
  - `web`: the Flask app on port 5001 (`python media_app/__init__.py`, Python 3.8, deps from `Pipfile` installed with `pipenv install --system`)
  - `cinema`: `cinema_service/`, a FastAPI + uvicorn IMDb lookup service on port 5005 (Python 3.10, deps installed inline in its Dockerfile)
- **Local dev:** `pipenv install`, then `pipenv run python media_app/__init__.py` from the repo root. Cover images are written to the relative path `./media_app/static/images/covers/`, so the app must run from the repo root.
- `start.sh` runs gunicorn (`media_app:app`), but it's an old testing script that Docker doesn't use.

**Committing to master auto-deploys.** `.git/hooks/post-commit` is symlinked to `.githooks/post-commit`. When a commit on master/main touches `media_app/`, the hook runs `docker-deploy.sh`, which does `docker-compose down && build && up -d`. Keep this in mind before committing.

## Configuration

- Config is an INI file chosen by `APP_CONFIG_FILE`: `config.ini` by default, and `config.docker.ini` in Docker. It has a `[database]` section (`db_user`, `db_pass`, `db_host`, `db_port`, `db_name`) and a `[youtube]` section (`youtube_api_key`). `config*.ini` is gitignored.
- `CINEMA_URL` sets where the app reaches the cinema service (default `http://localhost:5005/`).
- `.dockerignore` is a deny-all allowlist that only lets in `Pipfile*`, `media_app/` and `config.docker.ini`. Any new top-level file the web container needs must be added there.

## Architecture

Almost all backend logic is in the single file `media_app/__init__.py`. The `models/` and `util/` directories are empty stubs and unused.

- **DB access** goes through the `records` library, with raw SQL and `:named` params. Its pins are deliberate: `records==0.5.3` and `sqlalchemy==1.3.23`, because newer SQLAlchemy breaks `records` (see TODO.md). A per-request connection is stored on `g.db`. Some functions (`list_media`, `action_update_integration_data`, `get_video_title`) use the module-global `db` instead.
- **The schema is not in the repo.** `sql/0001-setup.sql` only grants permissions. Tables referenced in code:
  - `media`
  - `media_type`
  - `media_length` (length units)
  - `media_integration_data` (keyed on `media_id` + `media_integration_id`; holds `cover_image`, `synopsis`, `meta_rating`)
  - `youtube_metadata` (a cache of video id → title/channel)

  Check the live DB, not guesses, for column details.
- **Dual-purpose functions:** several `@api` blueprint functions (`/api/...`) are also called directly from view routes. They check `'api' in request.url_rule.rule` and return a JSON `Response` for API calls or plain Python data for internal calls (examples: `action_years`, `action_stats`, `action_stats_list`). Route functions also switch behavior on which URL rule matched, such as `create` vs `update`, or `view` vs `edit`.
- **Media type IDs are hardcoded in several places**, and all of them must stay in sync when types change:
  - `type_unit` (type id → length unit)
  - `integrations[...]['media_types']` in `__init__.py`
  - `imdb_types` / `ol_types` in `media_app/static/js/imdb.js`
  - the shelf query (`media_type in (1, 4)`)
- **External integrations** are defined in the `integrations` dict:
  - `imdb` (integration id 1) calls the `cinema` service over HTTP. That service wraps `imdbinfo` and returns cinemagoer-style keys (`'cover url'`, `'plot'` as a list, `'runtimes'` as a list) that `imdb_info()` parses. The service was split out because the IMDb library's dependencies conflicted with the main app's.
  - `ol` (integration id 2) calls the OpenLibrary API directly.

  When an entry is saved with an integration ID, the app fetches its cover image (saved to `static/images/covers/<media_id>.<ext>`, which is bind-mounted in compose) and its synopsis.
- **YouTube "music theme"**: an optional URL on each entry. On save, `get_video_title` looks up the title through the YouTube Data API, using the `youtube_metadata` table as a cache, so the title survives if the video later disappears.
- **Frontend**: Jinja templates extending `base.html`, with Bootstrap 5 beta (vendored under `static/lib`) and jQuery. Integration search and autofill on the create/edit page live in `static/js/imdb.js`, which calls the `/api/integration/...` endpoints.

## Intentional design choices

- Rewatches and rereads are separate entries, told apart through the free-form `subsection` field (for example "2026 reread"). The stubbed `/api/rewatch` endpoint is intentionally unused.
- No export feature: the user queries Postgres directly.
- `subsection` is intentionally generic across all media types.
