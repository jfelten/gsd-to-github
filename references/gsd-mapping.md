# GSD → GitHub Projects V2 Mapping

## Concept Mapping

| GSD | GitHub | Notes |
|---|---|---|
| Milestone (M001) | Plan name / project board | `**Plan:** M001: Title` in issue body |
| Slice (S01) | Issue with `slice` label | Contains task checklist, risk, dependencies |
| Task (T01) | Checklist item or sub-issue | Within slice issue body, or standalone with `task` label |
| `risk:high` | Label `risk:high` | Color: `D73A4A` (red) |
| `risk:medium` | Label `risk:medium` | Color: `FFA500` (orange) |
| `risk:low` | Label `risk:low` | Color: `0E8A16` (green) |
| `depends:[S01]` | `- [ ] #N` checklist | Parsed by pull-plan for scheduling |
| Slice completion | Board column "Done" | Set via GraphQL mutation |
| Roadmap reassessment | Manual issue update | No native GitHub analog |

## Granularity Options

### Slice-Level (Default)

One issue per slice. Best when:
- Slices are the unit of work assignment
- Task-level tracking happens within the issue body or in GSD locally
- You want a clean board with fewer items

Issue title: `[S01] Slice Title`
Issue body structure:
```markdown
**Plan:** M001: Milestone Title
**Repository:** owner/repo
**Risk:** high

## Goal
{from slice context or plan}

## Tasks
- [ ] T01: Task one title
- [ ] T02: Task two title

## Done Criteria
{from slice plan}
```

### Task-Level

One issue per task. Best when:
- Multiple people work on tasks within a single slice
- You need per-task board tracking
- Tasks are substantial enough to warrant their own issues

Issue title: `[S01-T01] Task Title`
Labels: `task`, `slice:S01`, `risk:{level}`

## Dependency Translation

GSD dependencies are between slices: `depends:[S01, S02]`.

**Slice-level mapping**: Direct — slice S03 depends on slice S01 and S02 issues.

**Task-level mapping**: The first task of S03 depends on the last task of S01 and the last task of S02. This approximates "slice S03 can't start until S01 and S02 are done."

## What Doesn't Map

- **Reassessment between slices** — GSD reassesses the roadmap after each slice. GitHub has no built-in analog. After completing a slice, manually update remaining issues if the plan changes.
- **Task estimates** (`est:2h`) — No native field. Could use a custom "Estimate" field on the project board.
- **Verification evidence** — GSD tasks have structured verification. GitHub issues have free-form comments.
- **GSD summaries** — These stay local in `.gsd/`. They don't need to sync to GitHub.

## Recommended Labels

Create these on the repository before pushing plans:

```bash
gh label create "slice" --color "1D76DB" --description "GSD slice" --repo OWNER/REPO
gh label create "task" --color "5319E7" --description "GSD task" --repo OWNER/REPO
gh label create "risk:high" --color "D73A4A" --description "High risk slice" --repo OWNER/REPO
gh label create "risk:medium" --color "FFA500" --description "Medium risk slice" --repo OWNER/REPO
gh label create "risk:low" --color "0E8A16" --description "Low risk slice" --repo OWNER/REPO
gh label create "plan" --color "FBCA04" --description "Part of a GSD plan" --repo OWNER/REPO
```
