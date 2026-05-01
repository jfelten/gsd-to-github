---
name: gsd-to-github
description: Sync GSD plans to GitHub Projects V2. Push milestones/slices/tasks as issues on a project board, pull the next actionable task, complete tasks with branch push and status update. Use when asked to "push plan to GitHub", "sync to project board", "pull next task", "complete task", "map GSD to GitHub", or when managing work on a GitHub Projects V2 board.
---

<essential_principles>

**GSD → GitHub Projects V2 Mapping**

| GSD Concept | GitHub Analog | How |
|---|---|---|
| Milestone | Project (or milestone label) | One project board per milestone, or a `milestone:M001` label |
| Slice | Issue with `slice` label | Issue body contains task checklist, risk level, dependencies |
| Task | Task list item or sub-issue | Checklist items within slice issue, or standalone issues with `task` label |
| `risk:high/medium/low` | Label (`risk:high`, etc.) | Applied to slice issues |
| `depends:[S01]` | "Blocked by #N" in issue body | Dependency checklist in issue body |
| Roadmap checkbox | Project board column | Todo → In Progress → Done |
| Plan name | `**Plan:** name` marker in body | Used to filter issues belonging to a plan |

**Authentication**: All workflows require `gh` CLI authenticated with `repo` + `project` scopes. Token is read from `~/git/.env` (`GITHUB_ACCESS_TOKEN=ghp_...`) or the ambient `GH_TOKEN`/`GITHUB_TOKEN` environment variable.

**Project Board Constants**: Each project has hardcoded IDs for the Status field and its option values (Todo, In Progress, Done). Discover these via GraphQL before first use — see `references/discover-project-ids.md`.

**Context File**: The `.plan-context.md` file is the handoff artifact between pull and complete workflows. It is gitignored and contains the claimed task's issue number, repo, branch name, and full body.

</essential_principles>

<routing>

Based on the user's request, route to the appropriate workflow:

**Creating/pushing plans:**
- Push a plan JSON to GitHub as issues → `workflows/push-plan.md`
- Convert a GSD milestone/roadmap to a plan JSON → `workflows/gsd-to-plan-json.md`
- Push a GSD milestone directly to GitHub → first `gsd-to-plan-json`, then `push-plan`

**Working on tasks:**
- Pull/claim the next actionable task → `workflows/pull-plan.md`
- Complete the current task → `workflows/complete-plan.md`

**Setup and discovery:**
- Discover project board IDs for a new project → `references/discover-project-ids.md`
- Understand the plan JSON schema → `references/plan-schema.md`
- Understand the GraphQL patterns used → `references/gh-projects-v2.md`

**If the user says "sync GSD to GitHub" or "map milestone to GitHub":**
1. Read the GSD roadmap (`M###-ROADMAP.md`)
2. Follow `workflows/gsd-to-plan-json.md` to generate `plan.json`
3. Follow `workflows/push-plan.md` to create issues and board items

</routing>

<configuration>

These constants must be set per-project. Discover them using `references/discover-project-ids.md`:

```
PROJECT_OWNER       - GitHub org or user (e.g. "ez-appsec")
PROJECT_NUMBER      - Project board number (e.g. 2)
REPOSITORY          - Target repo for issues (e.g. "ez-appsec/ez-appsec")
STATUS_FIELD_ID     - Node ID of the Status single-select field
TODO_OPTION_ID      - Node ID of the "Todo" option
IN_PROGRESS_OPTION_ID - Node ID of the "In Progress" option
DONE_OPTION_ID      - Node ID of the "Done" option
```

</configuration>

<success_criteria>
- Plans pushed to GitHub create one issue per task with correct labels, dependencies, and project board status
- Pulling a task respects dependency order — only claims tasks whose dependencies are all Done
- Completing a task pushes the branch, sets board status to Done, and cleans up the context file
- GSD milestone roadmaps can be converted to plan JSON and pushed in one workflow
</success_criteria>
