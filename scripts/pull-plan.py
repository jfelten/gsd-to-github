#!/usr/bin/env python3
"""Pull the next actionable task from a plan on the GitHub project board.

Usage:
    python3 pull-plan.py <plan-name>

Scans the project board for Todo items whose body contains "**Plan:** <plan-name>".
Picks the first task whose dependencies are all Done. Marks it In Progress and
writes its details to .plan-context.md for the executing agent.

Exit codes:
    0  Task claimed — details in .plan-context.md
    1  Error (missing args, API failure)
    2  No actionable tasks (all done, in progress, or blocked)

Configuration (environment variables or ~/git/.env):
    GITHUB_ACCESS_TOKEN     - GitHub PAT with repo + project scopes
    PROJECT_OWNER           - GitHub org or user (required)
    PROJECT_NUMBER          - Project board number (required)
    STATUS_FIELD_ID         - Node ID of the Status field (required)
    IN_PROGRESS_OPTION_ID   - Node ID of the "In Progress" option (required)
"""
import json
import re
import sys
from pathlib import Path

from lib import (
    get_config,
    get_project_id,
    gh,
    update_project_item_status,
)


CONTEXT_FILE = ".plan-context.md"


def get_project_items(config):
    output = gh(
        "project", "item-list", str(config["number"]),
        "--owner", config["owner"],
        "--format", "json",
        token=config["token"],
    )
    return json.loads(output).get("items", [])


def get_issue_body(repo, issue_number, token):
    output = gh(
        "issue", "view", str(issue_number),
        "--repo", repo,
        "--json", "body,title,url,labels",
        token=token,
    )
    return json.loads(output)


def extract_repo_from_body(body):
    match = re.search(r"\*\*Repository:\*\*\s*(\S+)", body)
    return match.group(1) if match else None


def extract_dependencies(body):
    deps = []
    for match in re.finditer(r"- \[[ x]\] #(\d+)", body):
        deps.append(int(match.group(1)))
    return deps


def are_dependencies_done(dep_numbers, done_numbers):
    return all(n in done_numbers for n in dep_numbers)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <plan-name>", file=sys.stderr)
        sys.exit(1)

    plan_name = sys.argv[1]
    config, get = get_config(["PROJECT_OWNER", "PROJECT_NUMBER", "STATUS_FIELD_ID", "IN_PROGRESS_OPTION_ID"])
    token = config["token"]

    owner = config["project_owner"]
    number_str = config["project_number"]
    if not owner or not number_str:
        print("ERROR: PROJECT_OWNER and PROJECT_NUMBER must be set.", file=sys.stderr)
        sys.exit(1)
    number = int(number_str)

    config["owner"] = owner
    config["number"] = number

    print(f"Scanning project for plan: {plan_name}")

    items = get_project_items(config)

    done_numbers = set()
    todo_candidates = []

    for item in items:
        content = item.get("content", {})
        issue_number = content.get("number")
        status = item.get("status", "")
        if issue_number is None:
            continue
        if status == "Done":
            done_numbers.add(issue_number)

    for item in items:
        content = item.get("content", {})
        issue_number = content.get("number")
        status = item.get("status", "")
        repo = content.get("repository", "")
        if issue_number is None or status != "Todo":
            continue

        if not repo:
            print(
                f"WARNING: Issue #{issue_number} has no repository field on the "
                f"project board — skipping",
                file=sys.stderr,
            )
            continue

        try:
            issue_data = get_issue_body(repo, issue_number, token)
        except SystemExit:
            print(
                f"WARNING: Could not fetch issue #{issue_number} from {repo} — skipping",
                file=sys.stderr,
            )
            continue

        body = issue_data.get("body", "")
        if f"**Plan:** {plan_name}" not in body:
            continue

        dep_numbers = extract_dependencies(body)
        target_repo = extract_repo_from_body(body) or repo

        todo_candidates.append({
            "item_id": item["id"],
            "issue_number": issue_number,
            "title": content.get("title", ""),
            "body": body,
            "url": issue_data.get("url", ""),
            "labels": issue_data.get("labels", []),
            "dep_numbers": dep_numbers,
            "repo": target_repo,
        })

    if not todo_candidates:
        print(f"No Todo tasks found for plan '{plan_name}'.")
        in_progress = sum(1 for item in items if item.get("status") == "In Progress")
        done = len(done_numbers)
        print(f"Board status: {done} done, {in_progress} in progress")
        sys.exit(2)

    actionable = None
    blocked = []
    for candidate in todo_candidates:
        if are_dependencies_done(candidate["dep_numbers"], done_numbers):
            actionable = candidate
            break
        else:
            missing = [n for n in candidate["dep_numbers"] if n not in done_numbers]
            blocked.append((candidate, missing))

    if actionable is None:
        print(f"All {len(todo_candidates)} remaining tasks are blocked on dependencies:")
        for candidate, missing in blocked:
            missing_str = ", ".join(f"#{n}" for n in missing)
            print(f"  #{candidate['issue_number']} {candidate['title']} — waiting on {missing_str}")
        sys.exit(2)

    project_id = get_project_id(owner, number, token)
    print(f"Claiming: #{actionable['issue_number']} {actionable['title']}")

    status_field_id = config.get("status_field_id")
    in_progress_option_id = config.get("in_progress_option_id")
    if status_field_id and in_progress_option_id:
        update_project_item_status(
            project_id, actionable["item_id"],
            status_field_id, in_progress_option_id, token,
        )
    else:
        print("WARNING: STATUS_FIELD_ID or IN_PROGRESS_OPTION_ID not set — skipping status update", file=sys.stderr)

    try:
        gh_user = gh("api", "user", "--jq", ".login", token=token)
        gh(
            "issue", "edit", str(actionable["issue_number"]),
            "--repo", actionable["repo"],
            "--add-assignee", gh_user,
            token=token,
        )
    except SystemExit:
        print("WARNING: Could not assign issue — continuing", file=sys.stderr)

    branch_slug = re.sub(r'[^a-z0-9]+', '-', actionable["title"].lower()).strip('-')[:60]
    branch_name = f"feat/{branch_slug}"

    context = f"""# Plan Task Context
# Plan: {plan_name}
# Issue: #{actionable['issue_number']} — {actionable['title']}
# URL: {actionable['url']}
# Repository: {actionable['repo']}
# Branch: {branch_name}
# DO NOT COMMIT this file — it is gitignored.

{actionable['body']}
"""
    Path(CONTEXT_FILE).write_text(context)

    print(f"Status: In Progress")
    print(f"Branch: {branch_name}")
    print(f"Context: {CONTEXT_FILE}")
    print()
    print(f"Task #{actionable['issue_number']}: {actionable['title']}")
    if actionable["dep_numbers"]:
        dep_str = ", ".join(f"#{n}" for n in actionable["dep_numbers"])
        print(f"Dependencies (all done): {dep_str}")


if __name__ == "__main__":
    main()
