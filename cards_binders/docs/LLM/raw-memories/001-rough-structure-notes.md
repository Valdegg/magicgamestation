# 001 — Raw Notes: Rough Structure Exploration

## Commands Run
* `ls -la`, `du -sh`, `wc -l *.py`, `ls` on all subfolders
* Read: `README.md`, `requirements.txt`, `config.env`, `start_website.sh`, `new_feature_requests.txt`

## Key Numbers
* Total project size: **1.8 GB** (1.5 GB is `data/raw/`, 222 MB is `venv/`)
* Actual code footprint (excluding data/venv): ~50 MB
* Python source: **21,695 lines** across 24 `.py` files
* HTML templates: 3 files totalling ~279 KB
* Biggest files: `collection_ui.py` (5,629 lines), `collection_ui_mitt.py` (5,105 lines), `wishlist_ui.py` (2,406 lines)

## Architecture Observations
* Monolithic FastAPI app — `main_app.py` mounts sub-apps (`web_ui.py`, `wishlist_ui.py`, `collection_ui.py`)
* Each sub-app is a self-contained Flask/FastAPI module with its own routes + HTML template
* `database.py` (1,145 lines) — SQLite via `collections.db`
* `simple_version/` has standalone market scanning scripts (`wishlist_deals.py` at 51 KB)
* `mtg_arbitrage/` — separate arbitrage module with config, data_loader, utils, wishlist
* `start_website.sh` also launches a game backend (port 9000) and game frontend (port 5173) from sibling dirs
* Parent project `/opt/magicgamestation/` has: `backend/`, `frontend/`, `cards_binders/`, `deploy/`, `docs/`, `logs/`

## Data Storage
* JSON files for collections, wishlists (with backup and archive variants)
* SQLite databases: `collections.db` (299 KB), `collections_mitt.db` (49 KB)
* Card images cached locally in `card_images/` and `card_images_sets/`
* `data/raw/` — 1.5 GB of raw market data

## Dependencies
* FastAPI + Uvicorn (web), Jinja2 (templates), requests + httpx (HTTP)
* BeautifulSoup4 + lxml (scraping), pandas + numpy (data)
* python-dotenv (config), itsdangerous (sessions)

## Auth
* `auth.py` (67 lines) — lightweight auth
* `tests/test_auth.py` exists

## Tests
* 12 test files in `tests/`
* Covers: API endpoints, auth, collection functions, database, dependencies, sorting, frontend auth (JS)

## Feature Requests (from new_feature_requests.txt)
* Done: ESC-closeable modals, rename binder.html, per-user wishlist in DB, market scan for all user collection cards
