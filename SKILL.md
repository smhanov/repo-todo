---
name: repo-todo
description: Use to manage repo tasks and plans in .plans/todo.md. Also use when told to do all todo items or tasks.
---

# Repo Todo

Use this for a repository's bugs, features, implementation plans, and task status, captured in `.plans/todo.md`. Use it to capture, prioritize, plan, claim, resume, block, or complete repository work.

## Setup

- Use the target checkout root; read its applicable agent instructions, existing board, and existing files in `.plans/`. Create `.plans/` and `.plans/todo.md` if absent; preserve existing tasks and plans.
- Ensure root `.gitignore` ignores `.plans/`; append `/.plans/` only if no effective rule there covers it. Preserve other rules; verify with `git check-ignore --no-index`. Do not untrack already tracked files automatically.
- Treat `.plans/todo.md` as authoritative for status. Ignored plans are checkout-local: parallel worktrees need one coordinator board and explicit plan handoffs.

## Board

Use this exact structure; keep empty tables. One row per item, in exactly one section. Use single-line cells, relative plan links, and `—` for empty values.

```markdown
# Tasks

## Todo
| Priority | ID | Description / plan | Notes |
| --- | --- | --- | --- |

## In Progress
| Priority | ID | Description / plan | Notes |
| --- | --- | --- | --- |

## Blocked
| Priority | ID | Description / plan | Notes |
| --- | --- | --- | --- |

## Done
| Priority | ID | Description / plan | Notes |
| --- | --- | --- | --- |
```

- Priorities: P0 urgent failure; P1 important; P2 normal/default. Sort open sections by priority, then ID; Done newest first.
- ID allocation: Always check both `.plans/todo.md` and the entire `.plans/` folder (list all files in `.plans/`). Note that not all plans are listed in `todo.md`. Inspect all existing IDs across both the board and every filename in `.plans/` (e.g. `T001-*.md`). Choose a free ID strictly above the maximum existing ID found anywhere (`T001`, `T002`, …); never reuse an existing ID or renumber. Preserve existing unique IDs during migration.
- Example row: `| P1 | T001 | Fix retry loop — [plan](T001-retry-loop.md) | draft |`.

## Workflow

1. **Capture:** Check for duplicates. Inspect the `.plans/` directory (list all filenames) and `.plans/todo.md` to identify all used IDs, since some plan files might not be listed on the board. Choose a free ID strictly above the maximum found. Add a Todo row and `.plans/<ID>-<slug>.md`. Read [plan template](references/plan-template.md) when creating or expanding plans. Every plan must include an implementation overview describing the overall approach and architectural changes so human reviewers understand the plan without deducing it from granular steps. Default to a ready plan when enough context exists; otherwise save a draft with the required expansion warning. Recording work does not authorize implementation.
2. **Prepare:** Before implementation, inspect current source, expand drafts (including a clear implementation overview and verified steps), resolve blocking unknowns, and verify dependencies. Mark the plan `ready` only when executable without guessing requirements.
3. **Claim:** Move an eligible item to In Progress; Notes must contain `owner=<agent/session>; updated=<UTC timestamp>`. Follow requested scope; otherwise choose the highest-priority eligible item. Never take another active owner's item without a handoff.
4. **Execute:** Work in the plan's verified increments. Update its checkboxes, evidence, and next action after each increment and before stopping. Record newly discovered unrelated work separately.
5. **Block:** Move to Blocked; Notes must identify the blocker/dependency and concrete unblock action. Preserve owner and detailed handoff in the plan. When resolved, return to Todo or explicitly reclaim.
6. **Complete:** Check every acceptance criterion against evidence, run applicable checks, and review the diff for scope/regressions. Missing or failing required checks prevent Done. Record results and residual limitations in the plan; move to Done with `completed=YYYY-MM-DD`. Reopen regressions under the same ID.

## Do All

Use when told to do all todo items, tasks, or plans. Process ready and draft items one at a time, in board order (priority, then ID), until none remain:

1. **Delegate:** Claim the item per Claim, then launch exactly one subagent and block until it reports completion before doing anything else. Never run subagents in parallel and never implement the item yourself. Give it the checkout root, plan path, and applicable agent instructions. If the plan is a draft, the subagent expands it to ready (per the plan template, including the implementation overview). Otherwise the subagent implements it per Execute, updating the plan's checkboxes, evidence, and next action as it goes. The subagent does not commit or move board rows.
2. **Verify:** Review the subagent's diff and run the plan's checks yourself; fix any problems directly. Then complete the item per Complete. Afterwards, capture follow-up work: any problems found, or work identified during the task but not done, must be recorded as a new Todo row with a draft plan (per Capture) before starting the next item.
3. **Commit:** Commit the task's changes (including board and plan updates) with a message matching repo style before starting the next item.

## Concurrency

Serialize board writes through one coordinator when agents run concurrently; an owner cell is not a lock. Re-read before edits and preserve others' changes. After each update, verify unique IDs across both `todo.md` and `.plans/`, valid priorities, existing plan links, and exactly one row per task. Keep completed records and plans.
