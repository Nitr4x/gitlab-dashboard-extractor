# gitlab-dashboard-extractor

A command-line tool that queries the GitLab API to find all repositories whose
topics match a user-supplied regular expression. Matching projects are exported
to a timestamped JSON file, while structured logs are written to both stdout
and a dated log file.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Arguments](#arguments)
  - [Examples](#examples)
- [Output](#output)
  - [JSON result file](#json-result-file)
  - [Log files](#log-files)
- [Project structure](#project-structure)
- [Running tests](#running-tests)

---

## Features

- **Credentials from a properties file** — the GitLab URL and personal access
  token are loaded from `config.properties` so that secrets are never passed
  on the command line or stored in shell history.
- **Topic-based filtering** — provide any Python-compatible regular expression;
  every project whose topic list contains at least one match is collected.
- **Full project metadata** — id, name, namespace, description, URLs,
  visibility, branch, and timestamps are captured for each match.
- **Timestamped JSON output** — results are written to
  `output/result_YYYYMMDD_HHMMSS.json`.
- **Dual logging** — log messages are emitted to **stdout** *and* to a rolling
  daily file at `logs/<tool-name>-YYYY-MM-DD.log`.
- **Handles pagination automatically** — uses the `python-gitlab` iterator API
  so large GitLab instances with thousands of projects work out of the box.

---

## Requirements

| Dependency | Version |
|------------|---------|
| Python | ≥ 3.10 |
| [python-gitlab](https://python-gitlab.readthedocs.io/) | ≥ 4.0.0 |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Nitr4x/gitlab-dashboard-extractor.git
cd gitlab-dashboard-extractor

# 2. (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install runtime dependencies
pip install -r requirements.txt
```

---

## Configuration

GitLab connection settings are stored in a **properties file** (INI format) so
that credentials are never passed on the command line.

1. Copy the provided example:

   ```bash
   cp config.properties.example config.properties
   ```

2. Edit `config.properties` and fill in your values:

   ```ini
   [gitlab]
   url   = https://gitlab.com
   token = glpat-xxxxxxxxxxxxxxxxxxxx
   ```

   > **Security:** `config.properties` is listed in `.gitignore` and will
   > never be committed. Do **not** share or commit this file.

The script will exit with a clear error message if the file is missing or if
either key is absent.

---

## Usage

```
python extractor.py -t <REGEX> [-c <CONFIG_FILE>]
```

### Arguments

| Flag | Short | Required | Description |
|------|-------|----------|-------------|
| `--topic` | `-t` | ✅ | Python regular expression matched against each project topic. |
| `--config` | `-c` | ❌ | Path to the properties file (default: `config.properties`). |

> **Tip:** The pattern is tested with `re.search`, so it matches anywhere
> inside a topic string. Anchor with `^` / `$` for exact matching.

### Examples

**Find all projects tagged with any Python-related topic:**

```bash
python extractor.py -t "python"
```

**Use a non-default properties file:**

```bash
python extractor.py -t "python" -c /etc/secrets/gitlab.properties
```

**Match topics that start with `data`:**

```bash
python extractor.py -t "^data"
```

**Case-insensitive match for CI/CD-related topics:**

```bash
python extractor.py -t "(?i)ci.?cd"
```

---

## Output

### JSON result file

Results are saved to `output/result_<TIMESTAMP>.json`, where `<TIMESTAMP>`
follows the `YYYYMMDD_HHMMSS` format. Each element in the JSON array
represents one matching project:

```json
[
  {
    "id": 12345,
    "name": "my-service",
    "name_with_namespace": "acme / my-service",
    "description": "Core backend service",
    "web_url": "https://gitlab.com/acme/my-service",
    "topics": ["python", "backend", "microservices"],
    "visibility": "private",
    "created_at": "2023-03-15T10:22:00.000Z",
    "last_activity_at": "2024-05-30T08:45:00.000Z",
    "default_branch": "main",
    "ssh_url_to_repo": "git@gitlab.com:acme/my-service.git",
    "http_url_to_repo": "https://gitlab.com/acme/my-service.git",
    "namespace": {
      "id": 99,
      "name": "acme",
      "kind": "group"
    }
  }
]
```

The `output/` directory is created automatically if it does not exist.

### Log files

Log messages are printed to stdout **and** appended to
`logs/gitlab-dashboard-extractor-YYYY-MM-DD.log`. The `logs/` directory is
created automatically.

```
2024-06-01T12:00:00 - gitlab-dashboard-extractor - INFO - Starting gitlab-dashboard-extractor.
2024-06-01T12:00:00 - gitlab-dashboard-extractor - INFO - Topic regex: 'python'.
2024-06-01T12:00:01 - gitlab-dashboard-extractor - INFO - Successfully authenticated with GitLab.
2024-06-01T12:00:01 - gitlab-dashboard-extractor - INFO - Fetching projects from GitLab…
2024-06-01T12:00:05 - gitlab-dashboard-extractor - INFO - Project 'acme / my-service' matched topic 'python'.
2024-06-01T12:00:05 - gitlab-dashboard-extractor - INFO - Scanned 320 project(s); 1 matched the pattern.
2024-06-01T12:00:05 - gitlab-dashboard-extractor - INFO - Results saved to 'output/result_20240601_120005.json'.
2024-06-01T12:00:05 - gitlab-dashboard-extractor - INFO - Done. 1 project(s) written to 'output/result_20240601_120005.json'.
```

---

## Project structure

```
gitlab-dashboard-extractor/
├── extractor.py              # Main script
├── config.properties.example # Safe credentials template (commit this)
├── config.properties         # Your credentials (git-ignored, never commit)
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Development / test dependencies
├── tests/
│   └── test_extractor.py     # Unit tests
├── output/                   # Created at runtime — JSON result files
├── logs/                     # Created at runtime — daily log files
└── README.md
```

---

## Running tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=extractor --cov-report=term-missing
```