#!/usr/bin/env python3
"""Mark the current plan task as Done and push its branch.

Usage:
    python3 complete-plan.py
    python3 complete-plan.py --repo owner/repo

Reads .plan-context.md (written by pull-plan.py) to identify the current task.
Creates a branch named after the task, pushes it to the target repository,
and sets the project board item to Done.

Configuration (environment variables or ~/git/.env):
    GITHUB_ACCESS_TOKEN   - GitHub PAT with repo + project scopes
    PROJECT_OWNER         - GitHub org or user (required)
    PROJECT_NUMBER        - Project board number (required)
    STATUS_FIELD_ID       - Node ID of the Status field (required)
    DONE_OPTION_ID        - Node ID of the "Done" option (required)
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ENV_FILE = Path.home() / "git" / ".env"
CONTEXT_FILE = ".plan-context.md"


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip()
    return env


def get_config():
    file_env = load_env()

    def get(key, default=None):
        return os.environ.get(key) or file_env.get(key) or default

    token = get("GITHUB_ACCESS_TOKEN") or get("GH_TOKEN") or get("GITHUB_TOKEN")
    if not token:
        print("ERROR: No GitHub token found.", file=sys.stderr)
        sys.exit(1)

    owner = get("PROJECT_OWNER")
    number = get("PROJECT_NUMBER")
    if not owner or not number:
        print("ERROR: PROJECT_OWNER and PROJECT_NUMBER must be set.", file=sys.stderr)
        sys.exit(1)

    return {
        "token": token,
        "owner": owner,
        "number": int(number),
        "status_field_id": get("STATUS_FIELD_ID"),
        "done_option_id": get("DONE_OPTION_ID"),
    }


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


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


def parse_context():
    path = Path(CONTEXT_FILE)
    if not path.exists():
        print(f"ERROR: {CONTEXT_FILE} not found. Run pull-plan.py first.", file=sys.stderr)
        sys.exit(1)

    text = path.read_text()
    context = {}

    match = re.search(r"# Issue: #(\d+)", text)
    if match:
        context["issue_number"] = int(match.group(1))

    match = re.search(r"# Repository: (\S+)", text)
    if match:
        context["repo"] = match.group(1)

    match = re.search(r"# Branch: (\S+)", text)
    if match:
        context["branch"] = match.group(1)

    match = re.search(r"# Plan: (.+)", text)
    if match:
        context["plan_name"] = match.group(1).strip()

    match = re.search(r"# Issue: #\d+ — (.+)", text)
    if match:
        context["title"] = match.group(1).strip()

    return context


def find_project_item_id(config, issue_number):
    output = gh(
        "project", "item-list", str(config["number"]),
        "--owner", config["owner"],
        "--format", "json",
        token=config["token"],
    )
    items = json.loads(output).get("items", [])
    for item in items:
        content = item.get("content", {})
        if content.get("number") == issue_number:
            return item["id"]
    return None


def set_status_done(project_id, item_id, config):
    if not config["status_field_id"] or not config["done_option_id"]:
        print("WARNING: STATUS_FIELD_ID or DONE_OPTION_ID not set — skipping status update", file=sys.stderr)
        return
    mutation = f'''
        mutation {{
            updateProjectV2ItemFieldValue(input: {{
                projectId: "{project_id}"
                itemId: "{item_id}"
                fieldId: "{config['status_field_id']}"
                value: {{ singleSelectOptionId: "{config['done_option_id']}" }}
            }}) {{ projectV2Item {{ id }} }}
        }}
    '''
    gh_graphql(mutation, config["token"])


def main():
    repo_override = None
    if "--repo" in sys.argv:
        idx = sys.argv.index("--repo")
        if idx + 1 < len(sys.argv):
            repo_override = sys.argv[idx + 1]

    context = parse_context()
    config = get_config()
    token = config["token"]

    issue_number = context.get("issue_number")
    branch = context.get("branch")
    repo = repo_override or context.get("repo", f"{config['owner']}/ez-appsec")
    title = context.get("title", f"task-{issue_number}")

    if not issue_number:
        print("ERROR: Could not parse issue number from .plan-context.md", file=sys.stderr)
        sys.exit(1)

    if not branch:
        print("ERROR: Could not parse branch name from .plan-context.md", file=sys.stderr)
        sys.exit(1)

    print(f"Task: #{issue_number} — {title}")
    print(f"Branch: {branch}")
    print(f"Repository: {repo}")

    current_branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if current_branch.stdout.strip() != branch:
        check = run(["git", "show-ref", "--verify", f"refs/heads/{branch}"])
        if check.returncode == 0:
            print(f"Switching to existing branch: {branch}")
            result = run(["git", "checkout", branch])
            if result.returncode != 0:
                print(f"ERROR: git checkout failed:\n{result.stderr}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Creating branch: {branch}")
            result = run(["git", "checkout", "-b", branch])
            if result.returncode != 0:
                print(f"ERROR: git checkout -b failed:\n{result.stderr}", file=sys.stderr)
                sys.exit(1)

    print(f"Pushing {branch} to origin...")
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    result = run(["git", "push", "-u", "origin", branch], env=env)
    if result.returncode != 0:
        print(f"WARNING: git push failed:\n{result.stderr}", file=sys.stderr)
        print("Continuing to mark project item as Done...")
    else:
        print("Push successful.")

    project_id = get_project_id(config["owner"], config["number"], token)
    item_id = find_project_item_id(config, issue_number)

    if item_id:
        set_status_done(project_id, item_id, config)
        print(f"Project board: #{issue_number} -> Done")
    else:
        print(f"WARNING: Issue #{issue_number} not found on project board", file=sys.stderr)

    Path(CONTEXT_FILE).unlink(missing_ok=True)
    print(f"Cleaned up {CONTEXT_FILE}")
    print()
    print("Task complete.")


if __name__ == "__main__":
    main()
