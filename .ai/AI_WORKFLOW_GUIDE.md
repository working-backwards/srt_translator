# AI-Assisted Development Workflow

This document describes the workflow setup for effective multi-tool AI-assisted development. This workflow can be replicated across projects.

**Created**: 2026-01-25
**Status**: Production-ready, tested on SRT Translator project

---

## Overview

This workflow enables seamless collaboration between multiple AI tools (Claude Code, Cursor, ChatGPT) with minimal context loss and maximum learning.

### Key Benefits
- ✅ **5-minute context switching** between AI tools
- ✅ **Resume work after weeks** without re-reading entire codebase
- ✅ **Learn from past prompts** - build personal AI interaction library
- ✅ **Organized design documentation** with git history
- ✅ **Team collaboration** - share context across developers

### Time Investment
- **Setup**: 15-20 minutes (one-time per project)
- **Daily overhead**: ~10 minutes (5 min read context, 5 min update)
- **Time saved**: Hours of context rebuilding and re-explaining

---

## Directory Structure

```
project-root/
├── .ai/                           # AI workflow support
│   ├── README.md                  # Overview of workflow
│   ├── context.md                 # ⭐ Current session context (daily driver)
│   ├── prompts.md                 # Prompt journal for learning
│   ├── QUICK_START.md             # Quick reference for new tasks
│   ├── MANAGING_COMPLETED_TASKS.md # How to keep context clean
│   ├── SETUP_COMPLETE.md          # Setup verification
│   ├── AI_WORKFLOW_GUIDE.md       # This document
│   └── archive/                   # Old context files (optional)
│       └── YYYY-MM-DD-task.md
│
├── docs/
│   └── design/                    # Design documents and JIRA tickets
│       ├── README.md              # Design docs organization
│       ├── JIRA_*.md              # JIRA-style tickets
│       └── ADR_*.md               # Architecture Decision Records (future)
│
└── .cursorrules                   # Cursor-specific AI instructions
```

---

## Core Files

### 1. `.ai/context.md` ⭐ MOST IMPORTANT

**Purpose**: Session continuity across AI tools and time

**Contents**:
```markdown
# Current Session Context

**Last Updated**: YYYY-MM-DD
**Branch**: branch-name
**Active Tool**: Claude Code / Cursor / ChatGPT

## Active Task
**[Task Name]** - Brief description
**Status**: In progress / Blocked / Complete

## Implementation Plan
### Completed
- ✅ Done items

### Next Steps
1. ⏳ Next thing to do
2. ⏳ Second thing

## Recent Work History
### Previous Task (Date) - Status
- Brief summary (2-3 lines)

## Key Learnings / Architecture Notes
(Useful knowledge to keep for future work)

## Notes for Other AI Tools
(How to use with Cursor, ChatGPT, etc.)
```

**When to update**:
- ✅ Start of session: Read (5 min)
- ✅ During work: Mark completed items
- ✅ Before switching tools: Update current status
- ✅ End of session: Update progress (3 min)
- ✅ When stuck: Note blockers

### 2. `.ai/prompts.md` - Prompt Journal

**Purpose**: Learn which prompts work best with each AI tool

**Contents**:
- Effective prompts with explanations
- Ineffective prompts with lessons learned
- Prompt patterns that consistently work
- Tool-specific phrasing tips (Claude Code vs Cursor vs ChatGPT)

**When to update**:
- After getting exceptionally good AI response
- After prompt fails to get desired outcome
- When discovering new prompt patterns

### 3. `docs/design/JIRA_*.md` - Design Documents

**Purpose**: Implementation-ready specifications for complex work

**When to create**:
- Complex bugs requiring root cause analysis
- Features touching 3+ files
- Architectural changes
- Anything requiring team discussion

**Contents**:
- Summary and description
- Root cause analysis (for bugs)
- Implementation approach
- Test plan
- Acceptance criteria
- Effort estimates

### 4. `.cursorrules` - Cursor Configuration

**Purpose**: Project-specific AI instructions for Cursor

**Contents**:
- Code style requirements
- Architecture rules (e.g., "NEVER import global settings in core")
- Logging standards
- Testing requirements
- Common gotchas

**Note**: This file is specific to Cursor but provides valuable context for all AI tools.

---

## Workflow by Activity

### Starting a New Task

**1. Update `context.md` (3 minutes)**
```markdown
## Active Task
**[New Task Name]** - Brief description
**Status**: Just started

## Implementation Plan
### Next Steps
1. ⏳ First thing to do
2. ⏳ Second thing to do
```

**2. Work on task**
- Mark items ✅ as completed
- Add findings to "Key Learnings"
- Note file locations

**3. Update before ending (2 minutes)**
- Mark progress
- Update "Last Updated" field
- Note any blockers

### Switching AI Tools

**Claude Code → Cursor**:
```
1. Update context.md:
   - Current progress
   - Set "Active Tool: Cursor"

2. In Cursor:
   - "Read .ai/context.md first"
   - Continue where Claude Code left off
```

**Cursor → ChatGPT**:
```
1. Copy relevant sections from context.md
2. Ask ChatGPT for strategic review
3. Update context.md with decision made
```

**Any tool → Claude Code**:
```
1. Update context.md with current status
2. Set "Active Tool: Claude Code"
3. Claude Code reads context and continues
```

### Completing a Task

**Option 1: Clear for New Task** (Most Common)
```
1. Move completed task to "Recent Work History" (2-3 lines)
2. Clear detailed implementation plans
3. Keep useful "Key Learnings"
4. Start new task in "Active Task" section
```

**Option 2: Archive** (Optional, for complex tasks)
```bash
mv .ai/context.md .ai/archive/2026-01-25-task-name.md
# Then start fresh from template
```

**Option 3: Brief Summary** (For collaboration)
```
Keep 2-3 sentence summary in "Recent Work History"
Clear detailed sections
```

**See `.ai/MANAGING_COMPLETED_TASKS.md` for full guide**

### Collaborating with Team

**Handing Off Work**:
```markdown
1. Update context.md:
   - Mark items as 🔄 (in progress by other)
   - Add collaboration note
   - Set "Status: Handed off to [Developer]"

2. Share JIRA tickets from docs/design/
3. Commit and push
```

**Receiving Work**:
```
1. Read their context.md
2. Read linked JIRA tickets from docs/design/
3. Continue their Implementation Plan
4. Update "Active Tool" to your tool
```

---

## Tool-Specific Usage

### Claude Code

**Best for**:
- Deep codebase exploration ("Find all places where X is used")
- Root cause analysis ("Why is this bug happening?")
- Creating design documents ("Create a JIRA ticket for X")
- Multi-file refactoring
- Test generation

**Effective prompts**:
```
"I don't want you to fix yet. I want you to tell me why
the bug is happening, why it's not reproducible on all
machines, and how to fix it."

"Create a JIRA ticket for [feature] with implementation
approach, test plan, and acceptance criteria."

"Find all places in the codebase where [X] is handled
and explain the data flow."
```

**Integration with workflow**:
- Updates context.md with findings
- Creates JIRA tickets in docs/design/
- Adds effective prompts to prompts.md

### Cursor

**Best for**:
- Active implementation with autocomplete
- Focused coding sessions on specific files
- Quick iterations with tab-completion
- Independent code review of designs

**Effective prompts**:
```
"Read .ai/context.md and docs/design/JIRA_X.md,
then implement the solution following .cursorrules"

"Review this implementation for edge cases, security
issues, and alignment with .cursorrules"
```

**Integration with workflow**:
- Reads context.md for current state
- Reads .cursorrules automatically
- Updates context.md with implementation status

### ChatGPT

**Best for**:
- High-level strategy and architecture
- General software engineering principles
- Writing non-code content (docs, blog posts)
- Independent review of designs

**Effective prompts**:
```
"What are common patterns for implementing [X]?"

"Review this design approach and suggest alternatives"

"Compare [Pattern A] vs [Pattern B] for [use case]"
```

**Integration with workflow**:
- Copy relevant sections from context.md
- Use for strategy, not codebase-specific implementation
- Update context.md with decisions made

---

## Prompt Patterns That Work

### Pattern: Explicit Separation of Phases
**Template**: "I don't want you to [implement/fix] yet. I want you to [analyze/explain/design] first."

**When to use**: Complex features where planning is critical

### Pattern: Three-Part Questions
**Template**: "Why does X happen? Why doesn't it happen on Y? How should we fix it?"

**When to use**: Debugging reproducibility issues or platform-specific bugs

### Pattern: Concrete Scenario Testing
**Template**: "What happens if [specific user action sequence]?"

**When to use**: Testing proposed solutions for gaps or edge cases

### Pattern: Structured Output Request
**Template**: "Create a [format] for [task]"

**When to use**: When you need implementation-ready documentation

**See `.ai/prompts.md` for more examples**

---

## Setup Instructions (New Project)

### 1. Create Directory Structure (5 minutes)

```bash
# In project root
mkdir -p .ai/archive
mkdir -p docs/design

# Create files
touch .ai/README.md
touch .ai/context.md
touch .ai/prompts.md
touch .ai/QUICK_START.md
touch .ai/MANAGING_COMPLETED_TASKS.md
touch docs/design/README.md
```

### 2. Copy Template Files (5 minutes)

Copy these files from SRT Translator project:
- `.ai/README.md` - Overview
- `.ai/QUICK_START.md` - Quick reference
- `.ai/MANAGING_COMPLETED_TASKS.md` - Maintenance guide
- `docs/design/README.md` - Design docs guide

### 3. Create Initial context.md (5 minutes)

```markdown
# Current Session Context

**Last Updated**: YYYY-MM-DD
**Branch**: [branch]
**Active Tool**: [tool]

## Active Task
**[First task]** - Brief description

## Implementation Plan
### Next Steps
1. ⏳ First step

## Key Learnings / Architecture Notes
(Add as you discover)

## Notes for Other AI Tools
### If Using Cursor
1. Read this context file first
2. Follow .cursorrules
3. Run linter before committing
```

### 4. Create or Update .cursorrules (5 minutes)

Add project-specific rules:
- Code style requirements
- Architecture constraints
- Testing requirements
- Common gotchas

### 5. Start Using (0 minutes - just work!)

Begin your first task and update context.md as you go.

**Total setup time**: 15-20 minutes

---

## Maintenance

### Daily
- ✅ Read context.md at start (5 min)
- ✅ Update context.md at end (3 min)
- ✅ Mark completed items during work

### Weekly
- ✅ Review context.md and clean up if needed
- ✅ Add effective prompts to prompts.md

### When Task Completes
- ✅ Move to "Recent Work History"
- ✅ Clear detailed implementation plans
- ✅ Keep useful "Key Learnings"

### Monthly (Optional)
- ✅ Review prompts.md for patterns
- ✅ Archive old context if file gets large (>500 lines)
- ✅ Update .cursorrules based on lessons learned

---

## Success Metrics

You'll know this workflow is working when:

✅ **Context switching is fast**: < 10 minutes to switch between AI tools
✅ **Resuming work is easy**: < 10 minutes to resume after weeks away
✅ **Prompts are improving**: You're reusing patterns that work
✅ **No re-explaining**: AI tools understand context immediately
✅ **Team can collaborate**: Others can pick up your work from context.md

---

## Troubleshooting

### Q: context.md is getting too long (>500 lines)

**A**: Archive old tasks:
```bash
mv .ai/context.md .ai/archive/2026-01-25-project-phase.md
# Start fresh from template
```

### Q: I forgot to update context.md

**A**: No problem! Take 5 minutes now to document current state. Better late than never.

### Q: Should I commit .ai/ to git?

**A**: YES! Benefits:
- Session continuity across machines
- Team visibility
- Historical record of design decisions

**Exception**: Add `.ai/personal.md` to `.gitignore` if you have personal notes.

### Q: What if teammate doesn't use this workflow?

**A**: Still useful for YOU:
- Resume your own work easily
- Track your own learning
- Document your decisions

They can benefit passively by reading your context when needed.

---

## Customization

This workflow is a starting point. Customize to your needs:

**Add sections** that help you:
- Personal notes section in context.md
- Tool comparison notes in prompts.md
- Decision log (.ai/decisions.md)

**Remove sections** that don't help:
- If prompts.md doesn't add value, skip it
- If Recent Work History is redundant, remove it

**Change structure**:
- Different directory names
- Different file organization
- Different template formats

**The goal**: Make it work for YOU, not follow rules blindly.

---

## Real-World Example: DNT Corruption Bug

### What Happened

**Task**: Investigate why termbase data appears in DNT field after Clear All → Regenerate workflow.

**Claude Code Session 1** (Analysis):
```
Prompt: "I don't want you to fix the bug yet. I want you
to tell me why the bug is happening, why it is not
reproduceable on every machine, and how to fix it."

Result:
- Created JIRA_DNT_CORRUPTION_BUG.md with root cause analysis
- Updated context.md with 3-factor root cause
- Added QSettings knowledge to "Key Learnings"
- Added effective prompt to prompts.md
```

**Claude Code Session 2** (Design):
```
Prompt: "Create a JIRA ticket for the defensive approach"

Result:
- Created JIRA_STARTUP_VALIDATION.md with 3-layer defense
- Updated context.md with implementation plan
- Ready for handoff to implementation
```

**Handoff to Another Developer**:
```
1. Shared JIRA tickets from docs/design/
2. Updated context.md: "Status: Handed off"
3. Cleaned context.md: removed detailed plans, kept learnings
4. Other developer can read JIRA tickets and implement
```

**Time Investment**:
- Claude Code analysis: 30 minutes
- Claude Code design: 20 minutes
- Context updates: 10 minutes
- **Total: 60 minutes**

**Value Delivered**:
- Comprehensive root cause analysis
- Implementation-ready design spec
- Knowledge preserved for future QSettings work
- Seamless handoff to another developer

---

## Why This Workflow Exists

### Problems It Solves

**Before this workflow**:
- ❌ Context loss when switching AI tools
- ❌ Re-explaining project every session
- ❌ No record of what AI tools suggested
- ❌ No learning from past prompts
- ❌ Design docs scattered or missing
- ❌ Hours wasted rebuilding context

**After this workflow**:
- ✅ 5-minute context switching
- ✅ Resume work after weeks in < 10 minutes
- ✅ Build personal AI prompt library
- ✅ Organized design documentation
- ✅ Team collaboration support
- ✅ Learn what works with each AI tool

### Core Principles

1. **Minimize Context Loss**: context.md preserves everything needed to resume work
2. **Learn Over Time**: prompts.md captures what works
3. **Support Multiple Tools**: Each AI tool has strengths, use them all
4. **Enable Collaboration**: Share context and designs with team
5. **Stay Lean**: Archive old work, keep context scannable

---

## Comparison to Other Approaches

### vs. No Structure (Ad-Hoc AI Usage)
**Problem**: Context loss, repetitive explanations, no learning
**This workflow**: Structured context, accumulated learning

### vs. Notion/Confluence for Context
**Problem**: Not in git, not AI-readable, context switching overhead
**This workflow**: Markdown in repo, AI can read it directly

### vs. Just Comments in Code
**Problem**: No high-level context, no prompt history, no design docs
**This workflow**: Separate layers (code + context + design + prompts)

### vs. Detailed Project Management Tools
**Problem**: Too heavy, takes time away from coding
**This workflow**: Lightweight (~10 min/day), focused on AI collaboration

---

## Adoption Path

### Week 1: Start Simple
- Create context.md only
- Update at end of each day
- Don't worry about other files

### Week 2: Add Prompts
- When AI gives great response, add to prompts.md
- Start building your prompt library

### Week 3: Add Design Docs
- For complex features, create JIRA ticket in docs/design/
- Link from context.md

### Week 4: Optimize
- Customize workflow to your needs
- Remove what doesn't help
- Add what's missing

**After 4 weeks**: Workflow becomes second nature, 10 min/day overhead.

---

## Resources

### Templates
- `.ai/QUICK_START.md` - New task template
- `.ai/MANAGING_COMPLETED_TASKS.md` - Cleanup guide
- This file - Complete workflow documentation

### Examples
- SRT Translator project - Real-world implementation
- DNT Corruption Bug - Case study of workflow in action

### Further Reading
- `.cursorrules` - Cursor-specific best practices
- `docs/design/README.md` - Design docs organization

---

## Questions?

This workflow is proven on the SRT Translator project and ready to replicate on other projects.

**Key files to copy**:
1. This file (`AI_WORKFLOW_GUIDE.md`) - Complete workflow documentation
2. `.ai/QUICK_START.md` - Quick reference
3. `.ai/MANAGING_COMPLETED_TASKS.md` - Maintenance guide
4. `.ai/README.md` - Overview
5. `docs/design/README.md` - Design docs guide

**Estimated setup time for new project**: 15-20 minutes

**Daily overhead**: ~10 minutes (5 min read, 5 min update)

**Time saved**: Hours of context rebuilding per week

---

**Version**: 1.0
**Last Updated**: 2026-01-25
**Status**: Production-ready
**Tested On**: SRT Translator project (Python, PySide6, multi-platform)
