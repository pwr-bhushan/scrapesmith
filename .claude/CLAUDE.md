## Development Workflow

### Step-by-Step Process

```
Step 1:  PLAN       → skill: everything-claude-code:plan          via Agent(model="opus")
Step 2:  TESTS      → skill: everything-claude-code:tdd            via Agent(model="sonnet")
Step 3:  IMPLEMENT  → skill: everything-claude-code:build-fix      via Agent(model="sonnet")
Step 4:  VERIFY     → skill: everything-claude-code:verify         via Agent(model="sonnet")
Step 5:  REVIEW     → skill: everything-claude-code:python-review  via Agent(model="opus")
Step 6:  FIX PLAN   → skill: everything-claude-code:plan           via Agent(model="opus")   (for review issues)
Step 7:  FIX        → skill: everything-claude-code:build-fix      via Agent(model="sonnet")  (after user approval)
Step 8:  RE-VERIFY  → skill: everything-claude-code:verify         via Agent(model="sonnet")
Step 9:  COMPLETE   → skill: everything-claude-code:update-docs    via Agent(model="haiku")  (update todo.md + lessons.md)
Step 10: SAVE       → skill: everything-claude-code:save-session   via Agent(model="haiku")
```

**Model rationale:**
- `opus` — deep reasoning tasks: planning, architecture, code review
- `sonnet` — balanced tasks: test writing, verification
- `haiku` — fast execution tasks: implementation edits, docs, session save

**CRITICAL — model enforcement:**
- The `Skill` tool always executes inline in the current session model and does NOT switch models.
- To actually run a skill under a different model, wrap it in a `general-purpose` Agent with the `model` parameter set:
  ```
  Agent(subagent_type="general-purpose", model="opus",   description="...", prompt="Use the Skill tool: skill='everything-claude-code:plan', args='...'")
  Agent(subagent_type="general-purpose", model="haiku",  description="...", prompt="Use the Skill tool: skill='everything-claude-code:build-fix', args='...'")
  Agent(subagent_type="general-purpose", model="sonnet", description="...", prompt="Use the Skill tool: skill='everything-claude-code:verify', args='...'")
  ```
- `general-purpose` agents have all tools (including `Skill`), so skills invoked this way work correctly.
- Never call `Skill` directly from the main session when a non-Sonnet model is required.

**At each step:**
1. At the start of a new session or step, spawn `Agent(model="haiku")` to invoke `everything-claude-code:resume-session`
2. Complete the step **by spawning an Agent with the correct model that invokes the designated skill — do not call Skill directly from the main session**
3. Present results to user
4. Spawn `Agent(model="haiku")` to invoke `everything-claude-code:save-session`
5. **Ask: "Ready to proceed to [next step]?"**
6. Wait for user confirmation before moving on

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
