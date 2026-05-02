# GSD to GitHub Projects V2

Sync GSD (Get Shit Done) plans to GitHub Projects V2. This tool bridges GSD milestones, slices, and tasks with GitHub issues and project boards, enabling team collaboration on work defined in GSD.

## What It Does

- **Push plans to GitHub**: Convert GSD roadmaps or plan JSON files into GitHub issues with dependencies
- **Claim next task**: Pull the next actionable task from the project board, respecting dependency order
- **Complete tasks**: Mark tasks as Done, push branches, and update the project board
- **Dependency-aware**: Only allows claiming tasks whose dependencies are all complete

## Installation

One-line install (replace `<your-repo>` with your actual URL):

```bash
bash -c 'cd ~/.agents/skills && git clone <your-repo> && ./<repo-name>/install.sh'
```

Or manually copy this directory to your skills path:

```bash
cp -r gsd-to-github ~/.agents/skills/
```

## Prerequisites

- **gh CLI**: Install from [cli.github.com](https://cli.github.com)
- **Authentication**: Run `gh auth login` (browser OAuth recommended)
- **Required PAT scopes**: `repo`, `project`, `read:org`
- **Python 3.10+**: Required for Python scripts
- **Docker**: Optional, for running tests (see `claim-plan.sh`)

## Configuration

Set these environment variables or add to `~/.env` or project `.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_ACCESS_TOKEN` | GitHub PAT (falls back to `GH_TOKEN`/`GITHUB_TOKEN`) | `ghp_...` |
| `PROJECT_OWNER` | GitHub org or user | `ez-appsec` |
| `PROJECT_NUMBER` | Project board number | `2` |
| `REPOSITORY` | Target repo for issues | `ez-appsec/ez-appsec` |
| `STATUS_FIELD_ID` | Node ID of the Status field | `PVTSSF_lADOEEhvmM4BUnlNzhBuhsY` |
| `TODO_OPTION_ID` | Node ID of "Todo" option | `47fc9ee3` |
| `IN_PROGRESS_OPTION_ID` | Node ID of "In Progress" option | `47fc9ee4` |
| `DONE_OPTION_ID` | Node ID of "Done" option | `47fc9ee5` |

### Discovering Project Board IDs

Run the discovery workflow to find your project's field and option IDs:

```bash
# See references/discover-project-ids.md for detailed instructions
gh project view 2 --owner ez-appsec --json id,fields
```

## Usage

### 1. Push a Plan to GitHub

Convert a GSD milestone to plan JSON, then push to GitHub:

```bash
# Convert GSD roadmap to plan JSON
# Follow workflows/gsd-to-plan-json.md

# Push the plan
python3 scripts/push-plans.py plan.json
```

This creates one issue per task on the project board with:
- Task title and description
- Dependency checklist
- Status set to "Todo"
- Labels applied

### 2. Pull/Claim the Next Task

Claim the next unblocked task:

```bash
# Programmatic (generic)
python3 scripts/pull-plan.py "PLAN_NAME"

# Interactive (ez-appsec specific)
bash workflows/claim-plan.sh <issue-number>
```

The script:
1. Scans the project board for Todo tasks in the plan
2. Checks if all dependencies are Done
3. Claims the first unblocked task
4. Sets status to "In Progress"
5. Assigns the issue to you
6. Writes context to `.plan-context.md` (gitignored)
7. Creates a local git branch

### 3. Complete a Task

When work is done, mark the task complete:

```bash
python3 scripts/complete-plan.py
```

This:
1. Ensures you're on the correct branch
2. Pushes the branch to GitHub
3. Sets the project board item to "Done"
4. Cleans up `.plan-context.md`

## GSD to GitHub Mapping

| GSD Concept | GitHub Analog | How |
|-------------|---------------|-----|
| Milestone | Project board | One project per milestone or `milestone:M001` label |
| Slice | Issue with `slice` label | Issue body contains task checklist and risk level |
| Task | Task list item or sub-issue | Checklist items or standalone issues with `task` label |
| `risk:high/medium/low` | Label (`risk:high`, etc.) | Applied to slice issues |
| `depends:[S01]` | "Blocked by #N" in issue body | Dependency checklist in issue body |
| Roadmap checkbox | Project board column | Todo → In Progress → Done |

## Plan JSON Schema

```json
{
  "plan_name": "Widget Refactor",
  "project": "ez-appsec/2",
  "repository": "ez-appsec/ez-appsec",
  "tasks": [
    {
      "title": "Extract widget interface",
      "description": "## Goal\nDefine the widget interface.\n\n## Done criteria\n- [ ] Interface defined\n- [ ] Tests pass",
      "labels": ["enhancement"],
      "depends_on": []
    },
    {
      "title": "Implement widget",
      "description": "## Goal\nBuild implementation.\n\n## Done criteria\n- [ ] Code written\n- [ ] Unit tests added",
      "labels": ["enhancement"],
      "depends_on": [0]
    }
  ]
}
```

See `references/plan-schema.md` for full schema details.

## Workflows

- **`workflows/gsd-to-plan-json.md`**: Convert GSD milestone to plan JSON
- **`workflows/push-plan.md`**: Push plan to GitHub issues
- **`workflows/pull-plan.md`**: Pull next actionable task
- **`workflows/complete-plan.md`**: Complete current task
- **`workflows/claim-plan.sh`**: Interactive task claiming with validation

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/push-plans.py` | Push plan JSON to GitHub |
| `scripts/pull-plan.py` | Pull next unblocked task |
| `scripts/complete-plan.py` | Complete current task and push |

## Context File

`.plan-context.md` is the handoff artifact between pull and complete workflows. It contains:
- Issue number and URL
- Repository and branch name
- Full issue body with task description

This file is gitignored.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (missing args, API failure, config issue) |
| 2 | No actionable tasks (all done, in progress, or blocked) |

## Troubleshooting

### "No GitHub token found"
Set `GITHUB_ACCESS_TOKEN` in `~/git/.env` or authenticate with `gh auth login`.

### "Missing required scopes"
Your PAT needs `repo`, `project`, and `read:org`. Re-authenticate with browser OAuth.

### "Could not find project"
Verify `PROJECT_OWNER` and `PROJECT_NUMBER` are correct.

### "All tasks are blocked"
Dependencies haven't completed. Check the project board for pending tasks.

### "Status update skipped"
`STATUS_FIELD_ID` or option IDs are missing. Run the discovery workflow to find them.

## Development

Run the scripts directly with Python 3.10+:

```bash
python3 scripts/push-plans.py plan.json
python3 scripts/pull-plan.py "PLAN_NAME"
python3 scripts/complete-plan.py
```

For Bash workflows:

```bash
bash workflows/claim-plan.sh 21
```

## See Also

- `SKILL.md` - Main skill documentation
- `references/gh-projects-v2.md` - GraphQL patterns
- `references/discover-project-ids.md` - Project ID discovery guide
- `references/gsd-mapping.md` - Detailed GSD mapping
