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
import sys
from pathlib import Path

from lib import (
    get_config,
    get_project_id,
    gh,
    update_project_item_status,
)


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


def validate_plan(plan):
    required = ["plan_name", "project", "repository", "tasks"]
    missing = [k for k in required if k not in plan]
    if missing:
        print(f"ERROR: Plan missing required fields: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    if not plan["tasks"]:
        print("ERROR: Plan has no tasks", file=sys.stderr)
        sys.exit(1)

    for i, task in enumerate(plan["tasks"]):
        if "title" not in task or not task["title"].strip():
            print(f"ERROR: Task at index {i} missing required 'title' field", file=sys.stderr)
            sys.exit(1)
        if "description" not in task or not task["description"].strip():
            print(f"ERROR: Task at index {i} missing required 'description' field", file=sys.stderr)
            sys.exit(1)
        for dep_idx in task.get("depends_on", []):
            if not isinstance(dep_idx, int) or dep_idx < 0 or dep_idx >= len(plan["tasks"]):
                print(
                    f"ERROR: Task at index {i} has invalid dependency index {dep_idx} "
                    f"(must be 0..{len(plan['tasks']) - 1})",
                    file=sys.stderr,
                )
                sys.exit(1)
            if dep_idx >= i:
                print(
                    f"ERROR: Task at index {i} depends on task {dep_idx} which comes after it "
                    f"(forward dependency)",
                    file=sys.stderr,
                )
                sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <plan.json>", file=sys.stderr)
        sys.exit(1)

    plan_path = Path(sys.argv[1])
    if not plan_path.exists():
        print(f"ERROR: {plan_path} not found", file=sys.stderr)
        sys.exit(1)

    plan = json.loads(plan_path.read_text())
    validate_plan(plan)

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

    config, _ = get_config(["STATUS_FIELD_ID", "TODO_OPTION_ID"])
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

        status_field_id = config.get("status_field_id")
        todo_option_id = config.get("todo_option_id")
        if status_field_id and todo_option_id:
            update_project_item_status(project_id, item_id, status_field_id, todo_option_id, token)
        else:
            print("(skipped status — STATUS_FIELD_ID or TODO_OPTION_ID not set)", end=" ", file=sys.stderr)

        print("-> Todo")

        created_issues.append((issue_number, title))

    print()
    print(f"Done. Created {len(created_issues)} issues on {repo}, all set to Todo.")
    print("Issue numbers:", ", ".join(f"#{n}" for n, _ in created_issues))


if __name__ == "__main__":
    main()
