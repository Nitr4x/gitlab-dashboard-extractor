"""Unit tests for extractor.py."""

import configparser
import json
import logging
import os
import re
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — lightweight stand-ins for python-gitlab objects
# ---------------------------------------------------------------------------


def _make_project(**kwargs) -> SimpleNamespace:
    """Return a minimal fake project object with sensible defaults."""
    defaults = {
        "id": 1,
        "name": "my-project",
        "name_with_namespace": "group / my-project",
        "description": "A test project",
        "web_url": "https://gitlab.example.com/group/my-project",
        "topics": [],
        "visibility": "private",
        "created_at": "2024-01-01T00:00:00.000Z",
        "last_activity_at": "2024-06-01T00:00:00.000Z",
        "default_branch": "main",
        "ssh_url_to_repo": "git@gitlab.example.com:group/my-project.git",
        "http_url_to_repo": "https://gitlab.example.com/group/my-project.git",
        "namespace": {"id": 10, "name": "group", "kind": "group"},
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _write_config(directory, url="https://gitlab.example.com", token="secret-token"):
    """Write a minimal config.properties file and return its path."""
    path = os.path.join(directory, "config.properties")
    content = f"[gitlab]\nurl = {url}\ntoken = {token}\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_returns_url_and_token(self, tmp_path):
        from extractor import load_config

        path = _write_config(str(tmp_path), url="https://gitlab.com", token="glpat-abc")
        config = load_config(path)
        assert config["url"] == "https://gitlab.com"
        assert config["token"] == "glpat-abc"

    def test_strips_whitespace_from_values(self, tmp_path):
        from extractor import load_config

        path = os.path.join(str(tmp_path), "config.properties")
        with open(path, "w") as fh:
            fh.write("[gitlab]\nurl =  https://gitlab.com  \ntoken =  tok  \n")
        config = load_config(path)
        assert config["url"] == "https://gitlab.com"
        assert config["token"] == "tok"

    def test_exits_if_file_not_found(self, tmp_path):
        from extractor import load_config

        with pytest.raises(SystemExit) as exc_info:
            load_config(os.path.join(str(tmp_path), "nonexistent.properties"))
        assert exc_info.value.code == 1

    def test_exits_if_gitlab_section_missing(self, tmp_path):
        from extractor import load_config

        path = os.path.join(str(tmp_path), "config.properties")
        with open(path, "w") as fh:
            fh.write("[other]\nurl = https://gitlab.com\ntoken = tok\n")
        with pytest.raises(SystemExit) as exc_info:
            load_config(path)
        assert exc_info.value.code == 1

    def test_exits_if_url_key_missing(self, tmp_path):
        from extractor import load_config

        path = os.path.join(str(tmp_path), "config.properties")
        with open(path, "w") as fh:
            fh.write("[gitlab]\ntoken = tok\n")
        with pytest.raises(SystemExit) as exc_info:
            load_config(path)
        assert exc_info.value.code == 1

    def test_exits_if_token_key_missing(self, tmp_path):
        from extractor import load_config

        path = os.path.join(str(tmp_path), "config.properties")
        with open(path, "w") as fh:
            fh.write("[gitlab]\nurl = https://gitlab.com\n")
        with pytest.raises(SystemExit) as exc_info:
            load_config(path)
        assert exc_info.value.code == 1

    def test_exits_if_both_keys_missing(self, tmp_path):
        from extractor import load_config

        path = os.path.join(str(tmp_path), "config.properties")
        with open(path, "w") as fh:
            fh.write("[gitlab]\n")
        with pytest.raises(SystemExit) as exc_info:
            load_config(path)
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# setup_logger
# ---------------------------------------------------------------------------


class TestSetupLogger:
    def test_returns_logger_with_correct_name(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from extractor import setup_logger

        logger = setup_logger("test-tool")
        assert logger.name == "test-tool"

    def test_creates_logs_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from extractor import setup_logger

        setup_logger("test-tool")
        assert (tmp_path / "logs").is_dir()

    def test_creates_log_file_with_correct_pattern(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from extractor import setup_logger
        from datetime import datetime

        setup_logger("my-tool")
        date_str = datetime.now().strftime("%Y-%m-%d")
        expected = tmp_path / "logs" / f"my-tool-{date_str}.log"
        assert expected.exists()

    def test_has_stdout_and_file_handlers(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Use a unique name to avoid reusing a cached logger from a previous test.
        from extractor import setup_logger

        logger = setup_logger("handler-check-tool")
        handler_types = {type(h) for h in logger.handlers}
        assert logging.StreamHandler in handler_types
        assert logging.FileHandler in handler_types

    def test_logger_level_is_debug(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from extractor import setup_logger

        logger = setup_logger("level-check-tool")
        assert logger.level == logging.DEBUG


# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


class TestParseArgs:
    def test_topic_long_flag_is_parsed(self):
        from extractor import parse_args

        args = parse_args(["--topic", "python"])
        assert args.topic == "python"

    def test_topic_short_flag_is_t(self):
        from extractor import parse_args

        args = parse_args(["-t", "data.*"])
        assert args.topic == "data.*"

    def test_config_defaults_to_config_properties(self):
        from extractor import parse_args, DEFAULT_CONFIG_PATH

        args = parse_args(["-t", "python"])
        assert args.config == DEFAULT_CONFIG_PATH

    def test_config_long_flag_overrides_default(self):
        from extractor import parse_args

        args = parse_args(["--config", "/tmp/my.properties", "-t", "python"])
        assert args.config == "/tmp/my.properties"

    def test_config_short_flag_overrides_default(self):
        from extractor import parse_args

        args = parse_args(["-c", "/tmp/my.properties", "-t", "python"])
        assert args.config == "/tmp/my.properties"

    def test_missing_topic_raises_system_exit(self):
        from extractor import parse_args

        with pytest.raises(SystemExit):
            parse_args([])

    def test_url_flag_no_longer_accepted(self):
        from extractor import parse_args

        with pytest.raises(SystemExit):
            parse_args(["--url", "https://gitlab.com", "-t", "python"])

    def test_token_flag_no_longer_accepted(self):
        from extractor import parse_args

        with pytest.raises(SystemExit):
            parse_args(["--token", "tok", "-t", "python"])


# ---------------------------------------------------------------------------
# fetch_projects
# ---------------------------------------------------------------------------


class TestFetchProjects:
    def _make_logger(self) -> logging.Logger:
        return logging.getLogger("test-fetch")

    def _make_gl(self, projects: list) -> MagicMock:
        gl = MagicMock()
        gl.projects.list.return_value = iter(projects)
        return gl

    # -- matching ---------------------------------------------------------

    def test_exact_topic_match(self):
        from extractor import fetch_projects

        project = _make_project(topics=["python", "backend"])
        gl = self._make_gl([project])
        results = fetch_projects(gl, "python", self._make_logger())
        assert len(results) == 1
        assert results[0]["name"] == "my-project"

    def test_regex_partial_match(self):
        from extractor import fetch_projects

        project = _make_project(topics=["python3"])
        gl = self._make_gl([project])
        results = fetch_projects(gl, r"python\d", self._make_logger())
        assert len(results) == 1

    def test_regex_matches_one_of_multiple_topics(self):
        from extractor import fetch_projects

        project = _make_project(topics=["java", "spring", "microservices"])
        gl = self._make_gl([project])
        results = fetch_projects(gl, "spring", self._make_logger())
        assert len(results) == 1

    # -- non-matching -----------------------------------------------------

    def test_no_match_returns_empty_list(self):
        from extractor import fetch_projects

        project = _make_project(topics=["javascript"])
        gl = self._make_gl([project])
        results = fetch_projects(gl, "python", self._make_logger())
        assert results == []

    def test_project_without_topics_is_excluded(self):
        from extractor import fetch_projects

        project = _make_project(topics=[])
        gl = self._make_gl([project])
        results = fetch_projects(gl, ".*", self._make_logger())
        assert results == []

    def test_project_with_none_topics_is_excluded(self):
        from extractor import fetch_projects

        project = _make_project(topics=None)
        gl = self._make_gl([project])
        results = fetch_projects(gl, ".*", self._make_logger())
        assert results == []

    # -- deduplication ----------------------------------------------------

    def test_project_included_only_once_when_multiple_topics_match(self):
        from extractor import fetch_projects

        project = _make_project(topics=["python", "python3"])
        gl = self._make_gl([project])
        results = fetch_projects(gl, r"python", self._make_logger())
        assert len(results) == 1

    # -- multiple projects ------------------------------------------------

    def test_multiple_projects_filtered_correctly(self):
        from extractor import fetch_projects

        p1 = _make_project(id=1, name="proj-a", topics=["python"])
        p2 = _make_project(id=2, name="proj-b", topics=["ruby"])
        p3 = _make_project(id=3, name="proj-c", topics=["python", "django"])
        gl = self._make_gl([p1, p2, p3])
        results = fetch_projects(gl, "python", self._make_logger())
        names = {r["name"] for r in results}
        assert names == {"proj-a", "proj-c"}

    # -- result shape -----------------------------------------------------

    def test_result_contains_expected_keys(self):
        from extractor import fetch_projects

        project = _make_project(topics=["devops"])
        gl = self._make_gl([project])
        results = fetch_projects(gl, "devops", self._make_logger())
        expected_keys = {
            "id",
            "name",
            "name_with_namespace",
            "description",
            "web_url",
            "topics",
            "visibility",
            "created_at",
            "last_activity_at",
            "default_branch",
            "ssh_url_to_repo",
            "http_url_to_repo",
            "namespace",
            "ingested_at",
        }
        assert expected_keys.issubset(results[0].keys())

    def test_ingested_at_is_iso8601_utc(self):
        from extractor import fetch_projects
        from datetime import datetime

        project = _make_project(topics=["devops"])
        gl = self._make_gl([project])
        results = fetch_projects(gl, "devops", self._make_logger())
        ingested_at = results[0]["ingested_at"]
        # Must parse without error and end with 'Z' (UTC marker)
        parsed = datetime.strptime(ingested_at, "%Y-%m-%dT%H:%M:%SZ")
        assert parsed is not None
        assert ingested_at.endswith("Z")

    def test_namespace_contains_expected_keys(self):
        from extractor import fetch_projects

        project = _make_project(topics=["ops"])
        gl = self._make_gl([project])
        results = fetch_projects(gl, "ops", self._make_logger())
        ns = results[0]["namespace"]
        assert set(ns.keys()) == {"id", "name", "kind"}


# ---------------------------------------------------------------------------
# save_output
# ---------------------------------------------------------------------------


class TestSaveOutput:
    def test_creates_output_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from extractor import save_output

        save_output([], logging.getLogger("test"))
        assert (tmp_path / "output").is_dir()

    def test_file_name_matches_pattern(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from extractor import save_output

        path = save_output([], logging.getLogger("test"))
        filename = os.path.basename(path)
        assert re.match(r"result_\d{8}_\d{6}\.json", filename), f"Unexpected filename: {filename}"

    def test_output_is_valid_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from extractor import save_output

        projects = [{"id": 1, "name": "proj"}]
        path = save_output(projects, logging.getLogger("test"))
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert data == projects

    def test_empty_list_produces_empty_array(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from extractor import save_output

        path = save_output([], logging.getLogger("test"))
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert data == []

    def test_returns_output_file_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from extractor import save_output

        path = save_output([], logging.getLogger("test"))
        assert os.path.isfile(path)


# ---------------------------------------------------------------------------
# main — integration-level smoke tests
# ---------------------------------------------------------------------------


class TestMain:
    def _mock_gl(self, projects=None):
        """Return a mock gitlab.Gitlab instance."""
        mock_gl = MagicMock()
        mock_gl.projects.list.return_value = iter(projects or [])
        return mock_gl

    def test_main_exits_on_invalid_regex(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config_path = _write_config(str(tmp_path))
        from extractor import main

        with pytest.raises(SystemExit) as exc_info:
            main(["-t", "[invalid", "-c", config_path])
        assert exc_info.value.code == 1

    def test_main_exits_on_missing_config_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from extractor import main

        with pytest.raises(SystemExit) as exc_info:
            main(["-t", "python", "-c", str(tmp_path / "nonexistent.properties")])
        assert exc_info.value.code == 1

    def test_main_exits_on_authentication_failure(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        import gitlab
        from extractor import main

        config_path = _write_config(str(tmp_path))
        mock_gl = MagicMock()
        mock_gl.auth.side_effect = gitlab.exceptions.GitlabAuthenticationError(
            "401 Unauthorized", 401
        )
        with patch("extractor.gitlab.Gitlab", return_value=mock_gl):
            with pytest.raises(SystemExit) as exc_info:
                main(["-t", "py", "-c", config_path])
            assert exc_info.value.code == 1

    def test_main_creates_output_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from extractor import main

        config_path = _write_config(str(tmp_path))
        project = _make_project(topics=["python"])
        mock_gl = self._mock_gl([project])
        with patch("extractor.gitlab.Gitlab", return_value=mock_gl):
            main(["-t", "python", "-c", config_path])

        output_files = list((tmp_path / "output").glob("result_*.json"))
        assert len(output_files) == 1
        with open(output_files[0], encoding="utf-8") as fh:
            data = json.load(fh)
        assert len(data) == 1
        assert data[0]["name"] == "my-project"

    def test_main_uses_credentials_from_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from extractor import main

        config_path = _write_config(
            str(tmp_path), url="https://my-gitlab.example.com", token="my-secret-token"
        )
        mock_gl = self._mock_gl()
        with patch("extractor.gitlab.Gitlab", return_value=mock_gl) as mock_ctor:
            main(["-t", "anything", "-c", config_path])

        mock_ctor.assert_called_once_with(
            "https://my-gitlab.example.com", private_token="my-secret-token"
        )

