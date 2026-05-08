"""Shared utilities for gsd-to-github plan scripts.

Provides GitHub CLI wrappers, configuration loading, and GraphQL helpers
used by push-plans.py, pull-plan.py, and complete-plan.py.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ENV_FILE = Path.home() / "git" / ".env"

_GRAPHQL_SAFE = re.compile(r'^[a-zA-Z0-9_\-/. ]+$')


def _sanitize_graphql_value(value, field_name):
    """Validate a value is safe for GraphQL string interpolation.

    Rejects values containing quotes, backslashes, or other characters
    that could break out of a GraphQL string literal.
    """
    s = str(value)
    if not _GRAPHQL_SAFE.match(s):
        print(
            f"ERROR: Unsafe characters in {field_name}: {s!r}. "
            f"Only alphanumeric, dash, underscore, slash, dot, and space are allowed.",
            file=sys.stderr,
        )
        sys.exit(1)
    return s


def load_env():
    """Load key=value pairs from ~/git/.env into a dict."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip()
    return env


def get_config(required_keys=None):
    """Resolve configuration from environment, falling back to ~/git/.env.

    Args:
        required_keys: List of keys that must be present (beyond the token).
                       Each key is checked in both os.environ and the .env file.
    """
    file_env = load_env()

    def get(key, default=None):
        return os.environ.get(key) or file_env.get(key) or default

    token = get("GITHUB_ACCESS_TOKEN") or get("GH_TOKEN") or get("GITHUB_TOKEN")
    if not token:
        print(
            "ERROR: No GitHub token found. Set GITHUB_ACCESS_TOKEN in ~/git/.env "
            "or GH_TOKEN in environment.",
            file=sys.stderr,
        )
        sys.exit(1)

    config = {"token": token}

    for key in (required_keys or []):
        val = get(key)
        config[key.lower()] = val

    return config, get


def gh(*args, token=None):
    """Run a gh CLI command and return stdout. Exits on failure."""
    env = os.environ.copy()
    if token:
        env["GH_TOKEN"] = token
    result = subprocess.run(
        ["gh"] + list(args),
        capture_output=True, text=True, env=env,
    )
    if result.returncode != 0:
        print(f"gh {' '.join(args[:3])}... failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def gh_graphql(query, token):
    """Run a GraphQL query via gh CLI and return parsed JSON."""
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True, env=env,
    )
    if result.returncode != 0:
        print(f"GraphQL failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def get_project_id(owner, number, token):
    """Look up the Projects V2 node ID by owner login and project number."""
    owner = _sanitize_graphql_value(owner, "owner")
    number = int(number)
    for entity_type in ["organization", "user"]:
        try:
            data = gh_graphql(f'''
                query {{
                    {entity_type}(login: "{owner}") {{
                        projectV2(number: {number}) {{ id }}
                    }}
                }}
            ''', token)
            return data["data"][entity_type]["projectV2"]["id"]
        except (KeyError, TypeError):
            continue
    print(f"ERROR: Could not find project {owner}/{number}", file=sys.stderr)
    sys.exit(1)


def update_project_item_status(project_id, item_id, field_id, option_id, token):
    """Set the status field on a project board item via GraphQL mutation."""
    project_id = _sanitize_graphql_value(project_id, "project_id")
    item_id = _sanitize_graphql_value(item_id, "item_id")
    field_id = _sanitize_graphql_value(field_id, "field_id")
    option_id = _sanitize_graphql_value(option_id, "option_id")

    mutation = f'''
        mutation {{
            updateProjectV2ItemFieldValue(input: {{
                projectId: "{project_id}"
                itemId: "{item_id}"
                fieldId: "{field_id}"
                value: {{ singleSelectOptionId: "{option_id}" }}
            }}) {{ projectV2Item {{ id }} }}
        }}
    '''
    gh_graphql(mutation, token)


def run_cmd(cmd, **kwargs):
    """Run a subprocess command, returning the CompletedProcess."""
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)
