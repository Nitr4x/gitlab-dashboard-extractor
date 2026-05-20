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

## Usage

```
python extractor.py --url <GITLAB_URL> --token <ACCESS_TOKEN> --topic <REGEX>
```

### Arguments

| Flag | Short | Required | Description |
|------|-------|----------|-------------|
| `--url` | `-u` | ✅ | Base URL of the GitLab instance (e.g. `https://gitlab.com`). |
| `--token` | `-t` | ✅ | GitLab personal access token. Requires at least the `read_api` scope. |
| `--topic` | `-T` | ✅ | Python regular expression matched against each project topic. |

> **Tip:** The pattern is tested with `re.search`, so it matches anywhere
> inside a topic string. Anchor with `^` / `$` for exact matching.

### Examples

**Find all projects tagged with any Python-related topic:**

```bash
python extractor.py \
  --url https://gitlab.com \
  --token glpat-xxxxxxxxxxxxxxxxxxxx \
  --topic "python"
```

**Match topics that start with `data`:**

```bash
python extractor.py -u https://gitlab.com -t glpat-xxx -T "^data"
```

**Case-insensitive match for CI/CD-related topics:**

```bash
python extractor.py -u https://gitlab.com -t glpat-xxx -T "(?i)ci.?cd"
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
├── extractor.py          # Main script
├── requirements.txt      # Runtime dependencies
├── requirements-dev.txt  # Development / test dependencies
├── tests/
│   └── test_extractor.py # Unit tests
├── output/               # Created at runtime — JSON result files
├── logs/                 # Created at runtime — daily log files
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