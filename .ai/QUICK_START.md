# Quick Start Guide for New Tasks

Use this when starting a new task or resuming work.

---

## Starting a New Task

### 1. Update `context.md` (3 minutes)

Clear out old task, add new task:

```markdown
## Active Task

**[Task Name]** - Brief description

**Status**: [Just started / In progress / Blocked]

---

## Key Findings

(Add findings as you discover them)

---

## Implementation Plan

### Completed
- (Nothing yet)

### Next Steps
1. ⏳ First thing to do
2. ⏳ Second thing to do
3. ⏳ Third thing to do
```

### 2. Work on Task

As you work:
- ✅ Mark completed items
- Add findings to "Key Findings"
- Note file locations in "Critical Files"

### 3. Update `context.md` Before Ending (2 minutes)

- Mark what you completed today
- Add any blockers or questions
- Update "Last Updated" field

---

## Resuming Work After Time Away

### 1. Read `context.md` (5 minutes)
Get full picture of:
- What you're working on
- What's been discovered
- What's left to do
- Which files matter

### 2. Check Implementation Plan
See checklist: what's ✅ done, what's ⏳ next

### 3. Continue Where You Left Off
Pick up next item in plan

---

## Switching AI Tools

### Claude Code → Cursor

**Before leaving Claude Code:**
```markdown
1. Update context.md with current progress
2. Set "Active Tool: Cursor"
3. Add notes for Cursor if needed
```

**In Cursor:**
```
Tell Cursor: "Read .ai/context.md first, then implement [task]"
```

### Cursor → Claude Code

**Before leaving Cursor:**
```markdown
1. Update context.md with what you implemented
2. Set "Active Tool: Claude Code"
3. Note if you need tests/review
```

**In Claude Code:**
```
Tell Claude: "Read .ai/context.md, then review/test [what was implemented]"
```

### Using ChatGPT for Strategy

**Prepare:**
```markdown
1. Copy relevant sections from context.md
2. Copy any design docs from docs/design/
3. Ask ChatGPT for strategic advice
```

**After:**
```markdown
1. Update context.md with decision made
2. Continue with implementation
```

---

## When to Create Design Docs

### Always Create JIRA Ticket (`docs/design/JIRA_*.md`) for:
- ✅ Complex bugs needing root cause analysis
- ✅ Features touching 3+ files
- ✅ Architectural changes
- ✅ Anything requiring team discussion

### Skip JIRA Ticket for:
- ❌ Simple bug fixes (1-2 line changes)
- ❌ Cosmetic UI tweaks
- ❌ Documentation updates
- ❌ Adding simple tests

---

## Effective Prompts

### For Investigation
```
"Find all places in the codebase where [X] is handled,
and explain how it works"
```

### For Design
```
"Create a JIRA ticket for [feature/bug] with:
- Root cause analysis (for bugs)
- Implementation approach
- Test plan
- Acceptance criteria"
```

### For Implementation
```
"Read .ai/context.md and docs/design/JIRA_[X].md,
then implement the solution following .cursorrules"
```

### For Review
```
"Review the implementation of [X], checking for:
- Edge cases
- Security issues
- Test coverage
- Alignment with .cursorrules"
```

---

## Daily Workflow

### Start of Day (5 min)
1. Read `context.md`
2. Check Implementation Plan
3. Start on next ⏳ item

### During Work
- Mark ✅ when done
- Add findings as discovered
- Update file locations

### End of Day (3 min)
1. Update `context.md`:
   - Mark completed items
   - Add new findings
   - Note blockers
   - Update "Last Updated"
2. Commit changes

**Total overhead**: ~10 min/day
**Time saved**: Hours of context rebuilding

---

## Collaboration

### Handing Off Work

**Before handoff:**
1. Update `context.md` with full status
2. Mark items as 🔄 (in progress by other)
3. Add collaboration note
4. Commit and push

**Example:**
```markdown
## Active Task
**[Task]** - Handed off to [Developer]

**Status**: Being implemented by [Developer] on [branch]

**Note**: JIRA tickets created and shared with [Developer].
```

### Receiving Work

**When picking up someone's work:**
1. Read their `context.md`
2. Read linked JIRA tickets
3. Continue their Implementation Plan
4. Update "Active Tool" to your tool

---

## Tips

### Make Context Files Scannable
Use:
- ✅ Checkboxes for status
- 📍 Markers for important sections
- 🔄 Icons for in-progress items
- ⚠️ Warnings for blockers

### Keep It Current
Better to update often with small changes than let it get stale.

### Use Checklists
Implementation Plan checkboxes are your friend. Check them off!

### Learn From Prompts
When AI gives great response, add prompt to `prompts.md` immediately.

---

## Template: New Task Context

Copy this into `context.md` when starting fresh:

```markdown
# Current Session Context

**Last Updated**: YYYY-MM-DD
**Branch**: [branch-name]
**Worktree**: [worktree-name]
**Active Tool**: [Claude Code / Cursor / ChatGPT]

---

## Active Task

**[Task Name]** - Brief description

**Status**: [Just started / In progress / Blocked / Complete]

---

## Key Findings

(Add as you discover)

---

## Implementation Plan

### Completed
- (Nothing yet)

### Next Steps
1. ⏳ First step
2. ⏳ Second step
3. ⏳ Third step

---

## Critical Files

### Files to Modify
- `path/to/file.py:line-number` - What needs changing

### Design Documents
- `docs/design/JIRA_*.md` - Design spec

---

## Notes for Other AI Tools

### If Using Cursor
1. Read this context file first
2. Review linked design docs
3. Follow `.cursorrules`

### If Using ChatGPT
1. Copy relevant sections
2. Use for strategy, not implementation

---

## Questions / Blockers

(Add as they come up)
```

---

## Questions?

Check:
- `.ai/README.md` - Overview of AI workflow
- `.ai/prompts.md` - Examples of effective prompts
- `docs/design/README.md` - Guide for design docs
