# Convert GSD Milestone to Plan JSON

Read a GSD milestone roadmap and generate a `plan.json` suitable for `push-plans.py`.

<required_reading>
- `references/plan-schema.md` — output format
- `references/gsd-mapping.md` — how GSD concepts map to GitHub
</required_reading>

<process>

1. **Identify the milestone** — ask the user or detect from `.gsd/STATE.md`. Read:
   - `.gsd/milestones/M###/M###-ROADMAP.md` — slice list with risk and dependencies
   - `.gsd/milestones/M###/M###-CONTEXT.md` — milestone brief (if exists)

2. **Parse the roadmap** — extract slices from checkbox lines:
   ```
   - [ ] **S01: Title** `risk:high` `depends:[]`
   - [ ] **S02: Title** `risk:medium` `depends:[S01]`
   ```
   Capture: slice ID, title, risk level, dependency list.

3. **For each slice, read its plan** (if it exists):
   - `.gsd/milestones/M###/slices/S##/S##-PLAN.md` — task list with estimates
   - Parse tasks: `- [ ] **T01: Title** `est:2h``

4. **Decide granularity** with the user:
   - **Slice-level**: One GitHub issue per slice. Task lists become checklist items in the issue body.
   - **Task-level**: One GitHub issue per task. Slices become labels or grouping markers.
   - Default to **slice-level** unless the user asks for task-level.

5. **Build the plan JSON:**

   For **slice-level** mapping:
   ```json
   {
     "plan_name": "M001: Milestone Title",
     "project": "OWNER/PROJECT_NUMBER",
     "repository": "OWNER/REPO",
     "tasks": [
       {
         "title": "[S01] Slice Title",
         "description": "## Goal\n{slice context}\n\n## Tasks\n- [ ] T01: ...\n- [ ] T02: ...\n\n## Done criteria\n{from plan}",
         "labels": ["slice", "risk:high"],
         "depends_on": []
       }
     ]
   }
   ```

   For **task-level** mapping:
   ```json
   {
     "tasks": [
       {
         "title": "[S01-T01] Task Title",
         "description": "## Slice: S01 — Slice Title\n\n{task plan content}",
         "labels": ["task", "slice:S01", "risk:high"],
         "depends_on": [0]
       }
     ]
   }
   ```

6. **Map dependencies:**
   - GSD `depends:[S01]` means all tasks in S01 must complete before this slice starts
   - For slice-level: `depends_on` references the slice's 0-based index in the tasks array
   - For task-level: the first task of a dependent slice depends on the last task of the dependency slice

7. **Map risk levels to labels:**
   - `risk:high` → label `risk:high`
   - `risk:medium` → label `risk:medium`
   - `risk:low` → label `risk:low`
   - Ensure these labels exist on the repo (create if needed: `gh label create "risk:high" --color D73A4A --repo REPO`)

8. **Write the plan JSON** to `.gsd/milestones/M###/plan.json` (or user-specified path).

9. **Confirm with user** before proceeding to `push-plan` workflow.

</process>

<success_criteria>
- Plan JSON is valid against the schema
- All slice dependencies correctly mapped to `depends_on` indices
- Risk levels mapped to labels
- Task descriptions include enough context for an agent to execute
- Skipped/completed slices are excluded from the plan
</success_criteria>
