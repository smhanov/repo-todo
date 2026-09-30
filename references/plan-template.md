# Plan template

Keep plans self-contained and proportional to the task. Replace instructions below with concrete facts; omit genuinely irrelevant sections. Link source paths/symbols, not just conversation history. Recheck source before execution; label hypotheses and never invent paths, commands, or test results. Always provide an implementation overview so human reviewers can grasp the overall technical approach at a glance without having to deduce it from granular steps.

## Draft

```markdown
# <ID>: <title>
Readiness: draft

MUST BE FLESHED OUT BEFORE IMPLEMENTATION.

## Request
<Problem or feature, desired outcome, known reproduction/context.>

## Missing before ready
- <Questions, source investigation, acceptance criteria, implementation overview, and implementation detail needed.>
```

## Ready

```markdown
# <ID>: <title>
Readiness: ready

## Outcome and scope
<Problem, observable desired behavior, explicit exclusions. For bugs: reproduction,
expected versus actual behavior.>

## Context and prerequisites
<Verified files/symbols, relevant contracts, existing patterns, setup and working
directory, dependencies by task ID, assumptions and resolved decisions.>

## Acceptance criteria
- [ ] AC1: <Given concrete input/state, when action occurs, observable result is X.>
- [ ] AC2: <Relevant error/boundary behavior; specify measurable thresholds if needed.>
<Map each criterion to a named test or reproducible manual check; avoid "works",
"robust", or implementation-only criteria. Preserve required existing behavior.>

## Implementation overview
<High-level summary of how the solution will be implemented. Explain the overall
strategy, architectural/structural changes, affected components/subsystems, data flow,
and key design decisions so a human reviewer can understand the entire approach at a
glance without having to deduce it from granular steps.>

## Implementation steps
1. <Exact files/symbols to inspect or change, intended behavior, constraints,
   and a verification checkpoint. Explain enough for a junior agent.>
2. <Next small, independently verifiable increment; name affected contracts,
   callers, error paths, and migration/compatibility concerns where relevant.>

## Verification
<For each AC: command/check, working directory, setup/fixtures, expected result.
Cover the critical user journey and relevant failure paths, not only mocked internals.
For bugs, add and observe a regression test failing for the intended reason before
fixing, where practical. For new behavior, test first where useful. For low-impact
edits, use direct checks; document why an automated test is unsuitable.
Include relevant regression/build/lint gates from the repo. Never weaken criteria
or tests merely to pass; record and justify legitimate scope changes.>

## Risks and recovery
<Material risks and mitigations; rollback for destructive/schema/deployment changes.>

## Progress and handoff
- Completed: <steps and changed files>
- Evidence: <AC IDs, actual commands/checks, outcomes, date; distinguish not run>
- Remaining/blocker: <unfinished work, failed attempts, required decision>
- Next action: <specific restart instruction; branch/worktree if relevant>
```
