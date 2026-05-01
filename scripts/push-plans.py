#!/usr/bin/env python3
"""Push a plan file to GitHub as ordered issues on a project board.

Usage:
    python3 push-plans.py <plan.json>

Reads the plan JSON (see references/plan-schema.md for schema), creates one
GitHub issue per task in order, adds each to the target project board with
status "Todo", and annotates dependency links in the issue body.

Configuration (environment variables or ~/git/.env):
    GITHUB_ACCESS_TOKEN  - GitHub PAT with repo + project scopes
    PROJECT_OWNER        - GitHub org or user (default: from plan.project)
    PROJECT_NUMBER       - Project board number (default: from plan.project)
    STATUS_FIELD_ID      - Node ID of the Status field (required)
    TODO_OPTION_ID       - Node ID of the "Todo" option (required)
"""
import json
import os
import subprocess
import sys
from pathlib import Path


ENV_FILE = Path.home() / "git" / ".env"


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


def get_config(env_vars):
    """Resolve configuration from environment, falling back to ~/git/.env."""
    file_env = load_env()

    def get(key, default=None):
        return os.environ.get(key) or file_env.get(key) or default

    token = get("GITHUB_ACCESS_TOKEN") or get("GH_TOKEN") or get("GITHUB_TOKEN")
    if not token:
        print("ERROR: No GitHub token found. Set GITHUB_ACCESS_TOKEN in ~/git/.env or GH_TOKEN in environment.", file=sys.stderr)
        sys.exit(1)

    return {
        "token": token,
        "status_field_id": get("STATUS_FIELD_ID"),
        "todo_option_id": get("TODO_OPTION_ID"),
    }


def gh(*args, token=None):
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


def create_issue(repo, title, body, labels, token):
    cmd = [
        "issue", "create",
        "--repo", repo,
        "--title", title,
        "--body", body,
    ]
    for label in labels:
        cmd.extend(["--label", label])
    output = gh(*cmd, token=token)
    url = output.strip().splitlines()[-1]
    issue_number = int(url.rstrip("/").split("/")[-1])
    return issue_number, url


def add_to_project(owner, number, issue_url, token):
    output = gh(
        "project", "item-add", str(number),
        "--owner", owner,
        "--url", issue_url,
        "--format", "json",
        token=token,
    )
    data = json.loads(output)
    return data["id"]


def set_status_todo(project_id, item_id, config):
    if not config["status_field_id"] or not config["todo_option_id"]:
        print("WARNING: STATUS_FIELD_ID or TODO_OPTION_ID not set — skipping status update", file=sys.stderr)
        return
    mutation = f'''
        mutation {{
            updateProjectV2ItemFieldValue(input: {{
                projectId: "{project_id}"
                itemId: "{item_id}"
                fieldId: "{config['status_field_id']}"
                value: {{ singleSelectOptionId: "{config['todo_option_id']}" }}
            }}) {{ projectV2Item {{ id }} }}
        }}
    '''
    gh_graphql(mutation, config["token"])


def build_issue_body(task, plan_name, repo, created_issues):
    depends_on = task.get("depends_on", [])
    body_parts = [
        f"**Plan:** {plan_name}",
        f"**Repository:** {repo}",
        "",
        task["description"],
    ]
    if depends_on:
        body_parts.append("")
        body_parts.append("---")
        body_parts.append("### Dependencies")
        body_parts.append("This task depends on the following tasks completing first:")
        body_parts.append("")
        for idx in depends_on:
            if idx < len(created_issues):
                dep_number, dep_title = created_issues[idx]
                body_parts.append(f"- [ ] #{dep_number} — {dep_title}")
            else:
                body_parts.append(f"- [ ] Task index {idx} (not yet created)")
    return "\n".join(body_parts)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <plan.json>", file=sys.stderr)
        sys.exit(1)

    plan_path = Path(sys.argv[1])
    if not plan_path.exists():
        print(f"ERROR: {plan_path} not found", file=sys.stderr)
        sys.exit(1)

    plan = json.loads(plan_path.read_text())

    required = ["plan_name", "project", "repository", "tasks"]
    missing = [k for k in required if k not in plan]
    if missing:
        print(f"ERROR: Plan missing required fields: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    if not plan["tasks"]:
        print("ERROR: Plan has no tasks", file=sys.stderr)
        sys.exit(1)

    plan_name = plan["plan_name"]
    repo = plan["repository"]
    tasks = plan["tasks"]

    project_parts = plan["project"].split("/")
    owner = os.environ.get("PROJECT_OWNER") or project_parts[0]
    number = int(os.environ.get("PROJECT_NUMBER") or project_parts[1])

    print(f"Plan: {plan_name}")
    print(f"Repository: {repo}")
    print(f"Project: {owner}/{number}")
    print(f"Tasks: {len(tasks)}")
    print()

    config = get_config(None)
    token = config["token"]
    project_id = get_project_id(owner, number, token)

    created_issues = []

    for i, task in enumerate(tasks):
        title = task["title"]
        labels = task.get("labels", [])

        body = build_issue_body(task, plan_name, repo, created_issues)

        print(f"[{i+1}/{len(tasks)}] Creating: {title} ...", end=" ", flush=True)

        issue_number, issue_url = create_issue(repo, title, body, labels, token)
        print(f"#{issue_number}", end=" ", flush=True)

        item_id = add_to_project(owner, number, issue_url, token)
        set_status_todo(project_id, item_id, config)
        print("-> Todo")

        created_issues.append((issue_number, title))

    print()
    print(f"Done. Created {len(created_issues)} issues on {repo}, all set to Todo.")
    print("Issue numbers:", ", ".join(f"#{n}" for n, _ in created_issues))


if __name__ == "__main__":
    main()
