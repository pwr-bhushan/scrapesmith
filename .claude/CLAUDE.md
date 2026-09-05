## Development Workflow

### Step-by-Step Process

```
Step 1:  PLAN
Step 2:  TESTS
Step 3:  IMPLEMENT
Step 4:  VERIFY
Step 5:  REVIEW     → skill: ponytail:ponytail-review  via Agent(model="opus")
Step 6:  FIX PLAN
Step 7:  FIX
Step 8:  RE-VERIFY
Step 9:  COMPLETE (update todo.md + lessons.md)
Step 10: SAVE
```

**At each step:**
1. At the start of a new session invoke `everything-claude-code:resume-session`
2. Complete the step
3. Present results to user
4. Invoke `everything-claude-code:save-session` at end of session

**Session file retention:** Keep at most 3 session files in `.claude/sessions/`. After saving a new session, delete the oldest files if count exceeds 3.

---

## Workflow Orchestration

1. **Plan Mode Default** — enter plan mode for any non-trivial task (3+ steps or architectural decisions). If something goes sideways, STOP and re-plan.
2. **Subagent Strategy** — use subagents liberally to keep main context clean.
3. **Self-Improvement Loop** — after ANY correction from the user: update `.claude/tasks/lessons.md`.
4. **Code Review → Plan → Fix** — never skip planning between review findings and the fix.
5. **Plan Changes Must Be Written to the Plan File** — any change to a plan is written to `.claude/plans/*.md` before code changes.
6. **Verification Before Done** — never mark a task complete without proving it works.
7. **Demand Elegance (balanced)** — for non-trivial changes, pause and ask "is there a more elegant way?"
8. **Autonomous Bug Fixing** — when given a bug report, just fix it. Don't ask for hand-holding.

## Task Management
1. **Plan First** — write complete plan to `.claude/plans/*.md` and update `.claude/tasks/todo.md` with checkable items.
2. **Verify Plan** — check in before starting implementation.
3. **Track Progress** — mark items complete in `.claude/tasks/todo.md` immediately, not later.
4. **Explain Changes** — high-level summary at each step.
5. **Document Results** — add review section to `.claude/tasks/todo.md`.
6. **Capture Lessons** — update `.claude/tasks/lessons.md` after corrections.

## Knowledge Base
**Before planning, building, or fixing anything, read `.claude/tasks/lessons.md`.** It contains domain knowledge and coding lessons. Update it whenever the user answers a domain question or a correction is made.

## Core Principles
- **Simplicity First** — make every change as simple as possible.
- **No Laziness** — find root causes, no temporary fixes, senior developer standards.
- **Minimal Impact** — changes should only touch what's necessary.

## Diagrams
- **Always use Mermaid.js** for workflow diagrams (and any flowcharts, sequence diagrams, state machines, or architecture diagrams) in plans, docs, and Markdown files. Author them in fenced ```mermaid code blocks — never ASCII art, bullet-step lists, or external image files for these.
- Pick the Mermaid diagram type that fits: `flowchart` for workflows/pipelines, `sequenceDiagram` for request/response flows, `stateDiagram-v2` for state machines, `erDiagram` for data models.
- **Data models / schemas:** always render a Mermaid `erDiagram` *alongside* the SQL DDL (keep both — SQL stays the source of truth, the erDiagram is the visual). A visual ER diagram beats reading raw DDL.

## Cross-Project Lessons

Pinned into `.claude/tasks/lessons.md` on day one.

**Environment**
- Use the project toolchain path explicitly (e.g. `.venv/bin/pytest`, `./node_modules/.bin/...`).
- Paste the full toolchain path into every subagent prompt.

**Workflow**
- Work on a feature/dev branch, never `main`.
- Implementation wins as ground truth on doc/code drift.
- Treat existing tests as locked public contracts. Extend, do not rewrite.

## Permissions
- You have permission to run any test runner bash commands needed by this project.
