#!/usr/bin/env python3
"""
gitlab-dashboard-extractor

A script that interfaces with the GitLab API to gather all repositories
that have a specific topic attached to them. The topic is provided as a
CLI argument and is interpreted as a regular expression.
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime

import gitlab

TOOL_NAME = "gitlab-dashboard-extractor"


def setup_logger(tool_name: str) -> logging.Logger:
    """Configure and return a logger that writes to stdout and a dated log file.

    The log file is created inside a ``logs/`` directory and follows the
    naming pattern ``<tool_name>-YYYY-MM-DD.log``.

    Args:
        tool_name: The name of the tool, used as the logger name and as part
            of the log file name.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(tool_name)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # File handler — logs/<tool_name>-YYYY-MM-DD.log
    os.makedirs("logs", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join("logs", f"{tool_name}-{date_str}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse and return command-line arguments.

    Args:
        argv: Optional list of argument strings (defaults to ``sys.argv[1:]``).

    Returns:
        A :class:`argparse.Namespace` with the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description=(
            "Extract GitLab repositories whose topics match a given "
            "regular expression and export the results as a JSON file."
        ),
    )
    parser.add_argument(
        "--url",
        "-u",
        required=True,
        help="Base URL of the GitLab instance (e.g. https://gitlab.com).",
    )
    parser.add_argument(
        "--token",
        "-t",
        required=True,
        help="GitLab personal access token (requires at least 'read_api' scope).",
    )
    parser.add_argument(
        "--topic",
        "-T",
        required=True,
        help="Regular expression pattern matched against each project topic.",
    )
    return parser.parse_args(argv)


def fetch_projects(
    gl: gitlab.Gitlab,
    topic_regex: str,
    logger: logging.Logger,
) -> list[dict]:
    """Fetch all projects from GitLab and return those with a matching topic.

    The function retrieves every accessible project (handling pagination
    automatically) and tests each of its topics against *topic_regex*.  A
    project is included at most once even if several of its topics match.

    Args:
        gl: An authenticated :class:`gitlab.Gitlab` client.
        topic_regex: A compiled-ready regular-expression string.
        logger: Logger used for progress and error messages.

    Returns:
        A list of dictionaries, each representing a matching project.

    Raises:
        gitlab.exceptions.GitlabError: On API communication errors.
    """
    matching_projects: list[dict] = []
    pattern = re.compile(topic_regex)

    logger.info("Fetching projects from GitLab…")
    projects = gl.projects.list(iterator=True)

    total = 0
    for project in projects:
        total += 1
        topics: list[str] = project.topics or []
        matched_topic = next(
            (t for t in topics if pattern.search(t)), None
        )
        if matched_topic is not None:
            logger.info(
                "Project '%s' matched topic '%s'.",
                project.name_with_namespace,
                matched_topic,
            )
            matching_projects.append(
                {
                    "id": project.id,
                    "name": project.name,
                    "name_with_namespace": project.name_with_namespace,
                    "description": project.description,
                    "web_url": project.web_url,
                    "topics": topics,
                    "visibility": project.visibility,
                    "created_at": project.created_at,
                    "last_activity_at": project.last_activity_at,
                    "default_branch": project.default_branch,
                    "ssh_url_to_repo": project.ssh_url_to_repo,
                    "http_url_to_repo": project.http_url_to_repo,
                    "namespace": {
                        "id": project.namespace["id"],
                        "name": project.namespace["name"],
                        "kind": project.namespace["kind"],
                    },
                }
            )

    logger.info(
        "Scanned %d project(s); %d matched the pattern.",
        total,
        len(matching_projects),
    )
    return matching_projects


def save_output(projects: list[dict], logger: logging.Logger) -> str:
    """Serialise *projects* to ``output/result_<TIMESTAMP>.json``.

    The ``output/`` directory is created if it does not already exist.

    Args:
        projects: List of project dictionaries to persist.
        logger: Logger used to report the output path.

    Returns:
        The path of the written file.
    """
    os.makedirs("output", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join("output", f"result_{timestamp}.json")

    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(projects, fh, indent=2, ensure_ascii=False)

    logger.info("Results saved to '%s'.", output_file)
    return output_file


def main(argv: list[str] | None = None) -> None:
    """Entry point of the script.

    Args:
        argv: Optional argument list forwarded to :func:`parse_args`.
    """
    args = parse_args(argv)
    logger = setup_logger(TOOL_NAME)

    logger.info("Starting %s.", TOOL_NAME)
    logger.info("Topic regex: '%s'.", args.topic)

    # Validate the regex early to give a clear error message.
    try:
        re.compile(args.topic)
    except re.error as exc:
        logger.error("Invalid regex pattern: %s", exc)
        sys.exit(1)

    # Initialise the GitLab client and authenticate.
    gl = gitlab.Gitlab(args.url, private_token=args.token)
    try:
        gl.auth()
        logger.info("Successfully authenticated with GitLab.")
    except gitlab.exceptions.GitlabAuthenticationError as exc:
        logger.error("Authentication failed: %s", exc)
        sys.exit(1)
    except gitlab.exceptions.GitlabError as exc:
        logger.error("GitLab API error during authentication: %s", exc)
        sys.exit(1)

    projects = fetch_projects(gl, args.topic, logger)
    output_file = save_output(projects, logger)
    logger.info("Done. %d project(s) written to '%s'.", len(projects), output_file)


if __name__ == "__main__":
    main()
