# Managing Completed Tasks in context.md

Quick guide for keeping context.md clean and useful.

---

## When You Finish a Task

You have **three options** depending on the situation:

### Option 1: Clear for New Task (Most Common) ✅

**When**: Starting a completely new, unrelated task

**What to do**: Replace the "Active Task" section with new task info

```markdown
## Active Task

**[New Task Name]** - Brief description

**Status**: Just started

---

## Implementation Plan

### Completed
- (Nothing yet)

### Next Steps
1. ⏳ First step
2. ⏳ Second step
```

**What to keep**:
- "Key Learnings / Architecture Notes" section (useful knowledge)
- "Recent Work History" (move old task here)

**What to remove**:
- Detailed implementation plans
- File-specific line numbers
- Step-by-step checklists

---

### Option 2: Archive for Future Reference (Optional) 📁

**When**: Task was complex and you might need to reference it later

**What to do**: Move detailed context to archive file

```bash
# Create archive with date
mv .ai/context.md .ai/archive/2026-01-25-dnt-corruption-bug.md

# Start fresh context from template (see QUICK_START.md)
```

**Benefit**: Keeps context.md clean while preserving detailed history

---

### Option 3: Move to "Recent Work History" (Good for Collaboration) 👥

**When**: Other developers might need to know what you worked on

**What to do**: Keep a brief summary in "Recent Work History"

```markdown
## Recent Work History

### DNT Corruption Bug (2026-01-25) - Completed/Handed Off
- ✅ Root cause analysis completed
- ✅ Defense-in-depth solution designed
- ✅ JIRA tickets created and shared with other developer
- 🔄 Implementation in progress by other developer

### Feature X (2026-01-20) - Completed
- ✅ Implemented in PR #123
- ✅ Tests passing
- ✅ Merged to main
```

**Benefit**: Team visibility into recent work without cluttering active task section

---

## Recommended Workflow

### For Your Next Task (After DNT Bug)

**Step 1**: Clean up context.md (5 minutes)

```markdown
## Active Task

**[Your New Task]** - What you're working on

**Status**: Just started

---

## Implementation Plan

### Completed
- (Nothing yet)

### Next Steps
1. ⏳ First thing to do
2. ⏳ Second thing to do

---

## Recent Work History

### DNT Corruption Bug (2026-01-25) - Handed Off
- ✅ Root cause analysis completed
- ✅ JIRA tickets created
- 🔄 Being implemented by other developer

---

## Key Learnings / Architecture Notes

### QSettings Behavior
- Type Preservation: QSettings serializes faithfully
- No Schema Validation: Always validate on load
- Platform Differences: Windows Registry vs plist vs INI

(Keep useful knowledge, remove task-specific details)
```

**Step 2**: Remove detailed sections that are no longer relevant:
- Detailed implementation plans with line numbers
- Specific file modifications
- Step-by-step checklists for completed work

**Step 3**: Keep general knowledge:
- Architecture insights
- Common gotchas
- Useful patterns discovered

---

## What to Keep vs Remove

### ✅ Always Keep

**Architecture Knowledge**:
- How QSettings works (you'll use this again)
- Common patterns in the codebase
- Gotchas and edge cases

**Recent History** (last 2-3 tasks):
- Brief summaries of what you worked on
- Status (completed, handed off, merged)
- Links to PRs or commits

**AI Workflow**:
- Notes for other AI tools
- Session continuity info

### ❌ Remove When Done

**Task-Specific Details**:
- Detailed implementation plans
- Step-by-step checklists
- Specific file paths with line numbers
- Root cause analysis details

**Transient Information**:
- "Currently blocked on X"
- "Waiting for review"
- "Next: implement Y"

---

## Example: Before and After

### Before (Task in Progress)

```markdown
## Active Task
**Fix DNT Bug** - Complex root cause with 3 factors

## Key Findings
[3 pages of detailed analysis]

## Implementation Plan
1. ⏳ Component 1: Schema versioning
2. ⏳ Component 2: Import validation
[10 more detailed steps]

## Critical Files
- srt_translator/gui/settings_manager.py:49-65
[20 more files with line numbers]

## Architecture Context
[5 pages of QSettings details]
```

### After (Task Complete, Starting New Work)

```markdown
## Active Task
**[New Task Name]** - Brief description

## Implementation Plan
### Next Steps
1. ⏳ First step for new task

## Recent Work History
### DNT Corruption Bug (2026-01-25) - Handed Off
- ✅ Root cause analysis completed
- 🔄 Being implemented by other developer

## Key Learnings / Architecture Notes
### QSettings Behavior
- Type Preservation: QSettings serializes faithfully
- Always validate on load
- Platform differences: Registry vs plist vs INI
```

**Result**: Clean context for new task, preserved useful knowledge

---

## When to Archive

### Archive If:
- ✅ Task was very complex (100+ lines in context)
- ✅ You might need detailed history later
- ✅ Multiple developers worked on it
- ✅ Important architectural decisions were made

### Don't Archive If:
- ❌ Simple bug fix or feature
- ❌ Details won't be useful later
- ❌ Everything is in git history anyway

**Archive Location**: `.ai/archive/YYYY-MM-DD-task-name.md`

---

## FAQ

### Q: How often should I clean context.md?

**A**: When starting a new, unrelated task. Don't clean it mid-task or you'll lose continuity.

---

### Q: What if I need details from an old task?

**A**:
1. Check git history (`git log --all -- .ai/context.md`)
2. Check archive (`.ai/archive/`)
3. Check JIRA tickets in `docs/design/`
4. Check PR descriptions

---

### Q: Should I keep "Recent Work History" forever?

**A**: Keep last 2-3 tasks (or last month). Archive older history if needed.

---

### Q: What about partially completed tasks?

**A**: Mark status clearly:

```markdown
### Task X (2026-01-25) - Partial/Paused
- ✅ Analysis complete
- ⏳ Implementation 50% done
- 📌 Paused: waiting for design review
```

---

## Quick Decision Tree

```
Task finished?
│
├─ Starting new unrelated task?
│  └─ YES → Clean context.md, move old task to "Recent Work History"
│
├─ Task very complex (>100 lines)?
│  └─ YES → Archive to .ai/archive/, then clean context.md
│
├─ Task simple or obvious?
│  └─ YES → Just clear "Active Task", start fresh
│
└─ Multiple people involved?
   └─ YES → Keep brief summary in "Recent Work History"
```

---

## Your Current Situation

**What you have**: DNT bug analysis, handed off to other developer

**What to do**:
1. ✅ Already done - Cleaned up to brief summary
2. ✅ Kept useful QSettings knowledge
3. ✅ Marked as "Handed Off" in Recent Work History

**Next**: When you start new work, update "Active Task" section with new task info.

---

## Remember

**Goal**: context.md should be **useful, not comprehensive**

- Keep it scannable (< 500 lines)
- Focus on current work
- Preserve useful knowledge
- Archive detailed history

**Bad**: Giant file with 10 tasks' worth of details
**Good**: Current task + useful knowledge + brief recent history
