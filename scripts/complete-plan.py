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
import sys
from pathlib import Path

from lib import (
    get_config,
    get_project_id,
    gh,
    run_cmd,
    update_project_item_status,
)


CONTEXT_FILE = ".plan-context.md"


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


def main():
    repo_override = None
    if "--repo" in sys.argv:
        idx = sys.argv.index("--repo")
        if idx + 1 < len(sys.argv):
            repo_override = sys.argv[idx + 1]

    context = parse_context()
    config, get = get_config(["PROJECT_OWNER", "PROJECT_NUMBER", "STATUS_FIELD_ID", "DONE_OPTION_ID"])
    token = config["token"]

    owner = config["project_owner"]
    number_str = config["project_number"]
    if not owner or not number_str:
        print("ERROR: PROJECT_OWNER and PROJECT_NUMBER must be set.", file=sys.stderr)
        sys.exit(1)
    number = int(number_str)

    config["owner"] = owner
    config["number"] = number

    issue_number = context.get("issue_number")
    branch = context.get("branch")
    repo = repo_override or context.get("repo")
    title = context.get("title", f"task-{issue_number}")

    if not repo:
        print(
            "ERROR: No repository found. Set --repo or ensure .plan-context.md "
            "contains a '# Repository:' line.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not issue_number:
        print("ERROR: Could not parse issue number from .plan-context.md", file=sys.stderr)
        sys.exit(1)

    if not branch:
        print("ERROR: Could not parse branch name from .plan-context.md", file=sys.stderr)
        sys.exit(1)

    print(f"Task: #{issue_number} — {title}")
    print(f"Branch: {branch}")
    print(f"Repository: {repo}")

    current_branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if current_branch.stdout.strip() != branch:
        check = run_cmd(["git", "show-ref", "--verify", f"refs/heads/{branch}"])
        if check.returncode == 0:
            print(f"Switching to existing branch: {branch}")
            result = run_cmd(["git", "checkout", branch])
            if result.returncode != 0:
                print(f"ERROR: git checkout failed:\n{result.stderr}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Creating branch: {branch}")
            result = run_cmd(["git", "checkout", "-b", branch])
            if result.returncode != 0:
                print(f"ERROR: git checkout -b failed:\n{result.stderr}", file=sys.stderr)
                sys.exit(1)

    print(f"Pushing {branch} to origin...")
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    result = run_cmd(["git", "push", "-u", "origin", branch], env=env)
    if result.returncode != 0:
        print(f"WARNING: git push failed:\n{result.stderr}", file=sys.stderr)
        print("Continuing to mark project item as Done...")
    else:
        print("Push successful.")

    project_id = get_project_id(owner, number, token)
    item_id = find_project_item_id(config, issue_number)

    if item_id:
        status_field_id = config.get("status_field_id")
        done_option_id = config.get("done_option_id")
        if status_field_id and done_option_id:
            update_project_item_status(project_id, item_id, status_field_id, done_option_id, token)
            print(f"Project board: #{issue_number} -> Done")
        else:
            print("WARNING: STATUS_FIELD_ID or DONE_OPTION_ID not set — skipping status update", file=sys.stderr)
    else:
        print(f"WARNING: Issue #{issue_number} not found on project board", file=sys.stderr)

    Path(CONTEXT_FILE).unlink(missing_ok=True)
    print(f"Cleaned up {CONTEXT_FILE}")
    print()
    print("Task complete.")


if __name__ == "__main__":
    main()
