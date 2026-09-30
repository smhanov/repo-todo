<div align="center">

<img src="assets/banner.png" alt="repo-todo — plan the work yourself, let an AI agent implement it" width="640">

# repo-todo

**A task board and planning format your AI agent can actually work from — in any repo, with any agent.**

You plan the work. The agent implements it. One markdown file keeps everyone — you, the agent, and your future self — on the same page.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![Format](https://img.shields.io/badge/format-just%20markdown-black)

</div>

---

## Why

Working with a coding agent has a failure mode you've probably hit: the agent loses the plot, you lose your place, and the "quick task" turns into an hour of re-explaining your own codebase.

repo-todo flips the workflow:

1. **You do the planning.** Writing tasks and plans into `.plans/` forces you to keep your mental model of the repo sharp — you're the architect, not a bystander.
2. **The agent does the implementing.** Point your agent at the board, tell it "do all the tasks", and step away. It claims one item at a time, implements, and records what it did.
3. **You stay in flow.** While the agent grinds through implementation, you can plan the next task, work another repo, or take an actual break. The board holds the state, so nothing lives only in your head — or only in the agent's context window.

The board is the handoff. Because it's just markdown in the repo, it survives context resets, works across sessions, and diffs cleanly in code review.

## What it is

Three small files you drop into your repo (or your agent's skill/instructions directory):

| File | Purpose |
|---|---|
| [`SKILL.md`](SKILL.md) | The agent-facing instructions: how to capture, claim, execute, block, and complete tasks |
| [`references/plan-template.md`](references/plan-template.md) | The plan template every task expands from (draft → ready) |
| `assets/` | Logo assets |

No runtime, no dependencies, no lock-in. It's a convention plus a precise instruction file any LLM agent can follow.

## The board

All state lives in `.plans/todo.md`. The structure is fixed so agents (and humans) can parse it at a glance:

```markdown
# Tasks

## Todo
| Priority | ID | Description / plan | Notes |
| --- | --- | --- | --- |
| P1 | T003 | Add retry with backoff to webhook sender — [plan](T003-webhook-retry.md) | draft |

## In Progress
| Priority | ID | Description / plan | Notes |
| --- | --- | --- | --- |
| P0 | T001 | Fix off-by-one in pagination — [plan](T001-pagination-fix.md) | owner=agent/codex; updated=2026-09-30T14:02Z |

## Blocked
| Priority | ID | Description / plan | Notes |
| --- | --- | --- | --- |
| P2 | T004 | Migrate config format — [plan](T004-config-migration.md) | blocked on T002; unblock: land config parser |

## Done
| Priority | ID | Description / plan | Notes |
| --- | --- | --- | --- |
| P1 | T002 | Upgrade to foo v2 — [plan](T002-foo-v2.md) | completed=2026-09-29 |
```

### Task states

| State | Meaning | Entry rules |
|---|---|---|
| **Todo** | Ready to be picked up, in priority order (`P0` urgent failure → `P2` normal) | Has a plan file, even if it's a draft |
| **In Progress** | Claimed by exactly one owner | Notes must contain `owner=<agent/session>; updated=<UTC timestamp>` |
| **Blocked** | Cannot proceed; the reason and unblock action are explicit | Notes name the blocker and the concrete unblock step |
| **Done** | Every acceptance criterion verified against evidence | Notes carry `completed=YYYY-MM-DD`; regressions reopen under the same ID |

Every task gets an **immutable ID** (`T001`, `T002`, …) that is never reused or renumbered — plan filenames carry the ID (`T001-pagination-fix.md`), so links survive reordering, and history stays traceable. One row per task, in exactly one section, always.

## Draft plans: capture now, think later

Good ideas shouldn't wait for full designs. When you know *what* but not yet *how*, record a **draft** plan:

```markdown
# T003: Add retry with backoff to webhook sender
Readiness: draft

MUST BE FLESHED OUT BEFORE IMPLEMENTATION.

## Request
Webhook deliveries fail silently on transient 5xx. We lose events.

## Missing before ready
- Which failures are retryable vs. permanent?
- Where does the backoff state live? Delivery table or in-memory?
- Acceptance criteria for "delivered exactly once, observably".
```

A **ready** plan is executable without guessing requirements: concrete acceptance criteria, an implementation overview a human reviewer can follow at a glance, and verified verification steps. Before implementing anything, the agent expands drafts to ready — never codes from a draft.

This draft → ready gate is the quality control: cheap to capture an idea mid-flow, impossible for an agent to run off with a half-thought.

## Claiming and locking

Multiple agents (or an agent plus you) can share one repo without stepping on each other:

- **Claiming** a task = moving its row to *In Progress* with `owner=...; updated=...` in Notes. The owner field is a convention, not a lock — but the rule is absolute: **never take another active owner's item without an explicit handoff.**
- **Serialized writes:** when several agents run concurrently, board edits go through one coordinator. Re-read the board immediately before editing; preserve other agents' rows.
- **Post-write invariants:** unique IDs, valid priorities, existing plan links, exactly one row per task — checked after every update.
- **Boards are checkout-local** (`.plans/` is gitignored by convention), so parallel worktrees each get a coordinator board and hand off plans explicitly.

## "Do all the tasks" mode

The workflow that makes the whole thing pay off. When you tell the agent to do all tasks, it processes the board one item at a time, in priority order:

1. **Delegate** — claim the item, launch exactly one implementation subagent, and block until it reports. Drafts get expanded to ready first.
2. **Verify** — review the diff and run the plan's acceptance checks *itself*. Problems found mid-task become new Todo rows with draft plans — follow-up work is captured, never dropped.
3. **Commit** — commit task + board + plan updates with a repo-style message, then move to the next item.

Because verification and committing are separated from implementation, you get clean per-task commits and an audit trail — and because it's one subagent at a time, you never get five half-finished features.

## Adding it to any repo

```bash
# in your repo root
mkdir -p .plans
curl -o .plans/AGENT_INSTRUCTIONS.md https://raw.githubusercontent.com/smhanov/repo-todo/main/SKILL.md
curl -o .plans/plan-template.md https://raw.githubusercontent.com/smhanov/repo-todo/main/references/plan-template.md

# keep plans local to the checkout (recommended)
grep -qxF '/.plans/' .gitignore || echo '/.plans/' >> .gitignore
```

Then point your agent at `.plans/AGENT_INSTRUCTIONS.md`, create a first draft plan, and say **"do all the tasks."**

Works with any agent that can read files and follow instructions: Claude Code, Codex, Cursor, OpenCode, Hermes, or a raw API loop.

### Or install it as an agent skill

If your agent supports skill directories (Hermes, OpenCode, and others), clone this repo into it:

```bash
git clone https://github.com/smhanov/repo-todo ~/.config/opencode/skills/repo-todo
```

## Tips

- **Keep the board honest.** The board is authoritative for status — if it's not on the board, it doesn't exist. Record newly discovered work as new rows immediately.
- **Plans are self-contained.** Link real files and symbols, verify commands exist, and never let a plan invent paths or test results. Future-you (and future agents) depend on it.
- **Right-size the ceremony.** A one-line fix gets a two-line plan. An architecture change gets acceptance criteria, risks, and a rollback. The template scales both ways.
- **Preserve done rows.** Completed tasks and their plans are the project's decision log — keep them.

## License

[MIT](LICENSE) — use it in any repo, with any agent.
