# CLAUDE.md — Agent context for gitlab-dashboard-extractor

This file gives AI coding agents (Claude, Copilot, etc.) the context they need
to work effectively in this repository.

---

## Project overview

`gitlab-dashboard-extractor` is a single-file Python CLI tool that:

1. Reads GitLab connection credentials (URL + personal access token) from a
   local INI-format properties file (`config.properties`).
2. Iterates over every project accessible to the authenticated user via the
   GitLab API (pagination handled automatically).
3. Filters projects whose topic list contains at least one entry matching a
   user-supplied Python regular expression (`--topic`/`-t`).
4. Writes matching project metadata to a timestamped JSON file under `output/`.
5. Emits structured log messages to both stdout and a rolling daily log file
   under `logs/`.

---

## Repository layout

```
gitlab-dashboard-extractor/
├── extractor.py              # Single-file application — all logic lives here
├── config.properties.example # Credentials template committed to git
├── config.properties         # Real credentials — git-ignored, never commit
├── requirements.txt          # Runtime dependency: python-gitlab ≥ 4.0.0
├── requirements-dev.txt      # Dev/test dependencies: pytest, pytest-cov
├── tests/
│   └── test_extractor.py     # pytest unit tests (40 tests)
├── output/                   # Created at runtime — JSON result files
├── logs/                     # Created at runtime — daily log files
├── README.md                 # Human-facing documentation
└── CLAUDE.md                 # This file
```

---

## Architecture — `extractor.py`

The file exposes five public functions and one module-level constant:

| Symbol | Purpose |
|--------|---------|
| `DEFAULT_CONFIG_PATH` | Default path to the properties file (`"config.properties"`) |
| `load_config(path)` | Reads `[gitlab]` section from an INI file; returns `{"url": ..., "token": ...}`; calls `sys.exit(1)` on any error |
| `setup_logger(tool_name)` | Configures a logger writing to stdout and `logs/<tool>-YYYY-MM-DD.log` |
| `parse_args(argv)` | `argparse`-based CLI parser; accepts `--topic`/`-t` and `--config`/`-c` |
| `fetch_projects(gl, topic_regex, logger)` | Iterates all GitLab projects; returns list of matching project dicts |
| `save_output(projects, logger)` | Writes JSON to `output/result_<TIMESTAMP>.json` |
| `main(argv)` | Orchestrates the above; entry point for `__main__` |

---

## CLI interface

```
python extractor.py -t <REGEX> [-c <CONFIG_FILE>]
```

| Flag | Short | Required | Description |
|------|-------|----------|-------------|
| `--topic` | `-t` | ✅ | Python `re.search` pattern matched against project topics. |
| `--config` | `-c` | ❌ | Path to properties file (default: `config.properties`). |
| `--help` | `-h` | ❌ | Standard argparse help (auto-generated). |

---

## Properties file format

```ini
# config.properties
[gitlab]
url   = https://gitlab.com
token = glpat-xxxxxxxxxxxxxxxxxxxx
```

- Must contain a `[gitlab]` section.
- Both `url` and `token` keys are required.
- The real file is git-ignored. `config.properties.example` is the committed
  template.

---

## Output format

Each matching project is represented as:

```json
{
  "id": 12345,
  "name": "my-service",
  "name_with_namespace": "acme / my-service",
  "description": "...",
  "web_url": "https://gitlab.com/acme/my-service",
  "topics": ["python", "backend"],
  "visibility": "private",
  "created_at": "2023-03-15T10:22:00.000Z",
  "last_activity_at": "2024-05-30T08:45:00.000Z",
  "default_branch": "main",
  "ssh_url_to_repo": "git@gitlab.com:acme/my-service.git",
  "http_url_to_repo": "https://gitlab.com/acme/my-service.git",
  "namespace": { "id": 99, "name": "acme", "kind": "group" },
  "timestamp": "2026-05-20T09:38:17Z"
}
```

---

## Development commands

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install dev/test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=extractor --cov-report=term-missing
```

---

## Coding conventions

- **Python ≥ 3.10** — use modern type hints (`list[str]`, `X | None`).
- **No external dependencies** beyond `python-gitlab` for production code.
- Every public function has a Google-style docstring (Args / Returns / Raises).
- Tests live in `tests/test_extractor.py` and are grouped in classes named
  `Test<FunctionName>`.
- Helper functions in the test file are prefixed with `_` (e.g. `_make_project`,
  `_write_config`).
- Credentials must **never** appear on the command line or in committed files —
  always loaded via `load_config()`.
- `sys.exit(1)` is the standard exit code for all runtime errors.

---

## Key design decisions

- **Single file** — `extractor.py` contains everything; no internal packages.
- **Credentials in a properties file** — keeps secrets out of shell history,
  process lists, and CI logs.
- **`re.search` semantics** — the topic regex matches anywhere within a topic
  string; users anchor with `^`/`$` for exact matching.
- **Iterator-based pagination** — `gl.projects.list(iterator=True)` handles
  GitLab's pagination transparently.
- A project is included **at most once** even if multiple topics match.
