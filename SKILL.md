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
- Never refer to plans in source code. `.plans/` contents are temporary working notes, not part of the codebase. Do not add imports, comments, links, or task/plan IDs pointing at plans in source files.

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
- ID allocation: Do not invent an ID, and do not copy `T001` from the example below or from any other repo. Plan files and board rows diverge, so take the higher number from both, then use the next integer. Never reuse or renumber. Preserve existing unique IDs during migration.

  `ls .plans | tail` is the wrong command: `todo.md` sorts after `T*.md` and hides the last task. Glob the plan files, then take the numeric max so `T1000` does not sort before `T999`.

  ```bash
  # last plan file, if any — empty means no plan files yet
  ls -1 .plans/T*.md 2>/dev/null | tail -1

  # highest number already used by a filename OR a board row; empty means none
  { ls -1 .plans/T*.md 2>/dev/null; grep -oE 'T[0-9]+' .plans/todo.md 2>/dev/null; } | grep -oE '[0-9]+' | sort -n | tail -1
  ```

  Example: `ls -1 .plans/T*.md | tail -1` prints `.plans/T014-widget-export.md`, and the numeric command prints `14`. The next ID is `T015` (14 + 1, zero-padded to at least 3 digits). If both commands print nothing, the next ID is `T001`.

  Claim that ID before editing the board: create `.plans/T015-<slug>.md` first, then re-run the numeric command. It must print `15`, and `ls -1 .plans/T015*.md` must show exactly one file. If it prints a higher number, another writer took an ID — allocate again. Do not write a second file with an ID that already exists.
- Example row (format only — this ID is not free): `| P1 | T001 | Fix retry loop — [plan](T001-retry-loop.md) | draft |`.

## Workflow

1. **Capture:** Check for duplicates. Allocate the ID by running the commands under ID allocation in this checkout — do not choose one from memory. Create `.plans/<ID>-<slug>.md` first, confirm the re-check, then add the Todo row. Read [plan template](references/plan-template.md) when creating or expanding plans. Every plan must include an implementation overview describing the overall approach and architectural changes so human reviewers understand the plan without deducing it from granular steps. Default to a ready plan when enough context exists; otherwise save a draft with the required expansion warning. Recording work does not authorize implementation.
2. **Prepare:** Before implementation, inspect current source, expand drafts (including a clear implementation overview and verified steps), resolve blocking unknowns, and verify dependencies. Mark the plan `ready` only when executable without guessing requirements.
3. **Claim:** Move an eligible item to In Progress; Notes must contain `owner=<agent/session>; updated=<UTC timestamp>`. Follow requested scope; otherwise choose the highest-priority eligible item. Never take another active owner's item without a handoff.
4. **Execute:** Work in the plan's verified increments. Update its checkboxes, evidence, and next action after each increment and before stopping. Record newly discovered unrelated work separately.
5. **Block:** Move to Blocked; Notes must identify the blocker/dependency and concrete unblock action. Preserve owner and detailed handoff in the plan. When resolved, return to Todo or explicitly reclaim.
6. **Complete:** Check every acceptance criterion against evidence, run applicable checks, and review the diff for scope/regressions. Plan names (`T` plus 3 or more digits — IDs are zero-padded to at least 3) must not appear in the source or docs to be committed; run this at the checkout root and require no output:

   ```bash
   git grep -nE '(^|[^A-Za-z0-9_])T[0-9]{3,}([^0-9]|$)' -- . ':!.plans' | grep -v 'repo-todo:ignore'
   ```

   Write it in that POSIX form, not with `\b`: git grep uses the system regex engine, and the BSD regex on macOS never matches `\b`, so the check would silently pass there while missing every ID.

   A match is a candidate, not proof of a plan reference: source may legitimately hold a token of that shape (part number, model, fixture, error code). Resolve each one instead of guessing. Remove real plan references. For a legitimate token, confirm it is not a plan in this checkout (`ls -1 .plans/<ID>*.md` prints nothing), then clear it with judgment. When the token is obviously not a plan reference — its meaning is plain from the line itself (a fixture, a hex constant, an error code, a version string) — you may dismiss it without touching the source; record the `file:line`, the token, and the reason in the plan's evidence so a reviewer can audit the call. When the token could plausibly be mistaken for a plan ID, make the exemption visible: add a trailing `repo-todo:ignore` comment on that line beside the token, and record the `file:line` and reason in the plan's evidence. Never exempt or dismiss a line whose token does resolve to a plan in `.plans/`, and never mark a whole file or directory to silence the check. Missing or failing required checks prevent Done. Record results and residual limitations in the plan; move to Done with `completed=YYYY-MM-DD`. Reopen regressions under the same ID.

## Do All

Use when told to do all todo items, tasks, or plans. Process ready and draft items one at a time, in board order (priority, then ID), until none remain:

1. **Delegate:** Claim the item per Claim, then launch exactly one subagent and block until it reports completion before doing anything else. Never run subagents in parallel and never implement the item yourself. Give it the checkout root, plan path, and applicable agent instructions. If the plan is a draft, the subagent expands it to ready (per the plan template, including the implementation overview). Otherwise the subagent implements it per Execute, updating the plan's checkboxes, evidence, and next action as it goes. The subagent does not commit or move board rows.
2. **Verify:** Review the subagent's diff and run the plan's checks yourself; fix any problems directly. Then complete the item per Complete. Afterwards, capture follow-up work: any problems found, or work identified during the task but not done, must be recorded as a new Todo row with a draft plan (per Capture) before starting the next item.
3. **Commit:** Commit the task's changes (including board and plan updates) with a message matching repo style before starting the next item.

## Concurrency

Serialize board writes through one coordinator when agents run concurrently; an owner cell is not a lock. Re-read before edits and preserve others' changes. After each update, verify unique IDs across both `todo.md` and `.plans/`, valid priorities, existing plan links, and exactly one row per task. Keep completed records and plans.

## Standing facts (2026-10)

- Checkouts carrying repo-todo: Hermes `skills/`, e14 + steve-air + aorus `opencode` skills dirs, steve-air Claude `skills/`, staging at `~/workspace/repo-todo`.
- Multi-task pushes = Do-All: run subagents SERIALLY; the parent verifies + commits. Never let two agents edit the same files in parallel.
