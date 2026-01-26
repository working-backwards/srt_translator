# AI Workflow Directory

This directory contains files to support AI-assisted development workflows across multiple AI tools (Claude Code, Cursor, ChatGPT, etc.).

## Files in This Directory

### `context.md` ⭐ MOST IMPORTANT
**Purpose**: Session continuity across AI tools and time

**What it contains**:
- Current active task and status
- Key findings from investigation
- Implementation plan with checklist
- Critical file locations with line numbers
- Architecture context and gotchas
- Notes for switching between AI tools

**When to update**:
- Before switching AI tools (Claude Code → Cursor)
- After major discoveries or decisions
- Before ending a work session
- When resuming work after days/weeks

**How to use**:
```bash
# Starting new session
1. Read context.md (5 minutes)
2. Review linked design docs
3. Pick up where you left off

# Switching tools
1. Update context.md with current progress
2. Note any blockers or open questions
3. Open new tool and reference context.md
```

### `prompts.md`
**Purpose**: Learn which prompts work best with each AI tool

**What it contains**:
- Effective prompts with explanations
- Ineffective prompts with lessons learned
- Prompt patterns that consistently work
- Tool-specific phrasing tips

**When to update**:
- After getting particularly good results from an AI
- After a prompt fails to get desired outcome
- When discovering new prompt patterns

**How to use**:
Before asking an AI tool something complex, check this journal for similar past prompts that worked well.

### `decisions.md` (Future - Optional)
**Purpose**: Track major design decisions made with AI assistance

**What it would contain**:
- Decision context (what we were trying to solve)
- Options considered (from different AI tools)
- What was chosen and why
- Alternatives rejected and why

**When to create**: If you find yourself forgetting why certain approaches were chosen.

## Why This Directory Exists

### Problem Without It
- **Context loss** when switching AI tools
- **Re-explaining** project context every session
- **Forgetting** what Claude Code found vs what Cursor suggested
- **No learning** from past successful prompts
- **Wasted time** re-investigating same issues

### Solution With It
- ✅ **Fast context switching** between AI tools (< 5 minutes)
- ✅ **Resume work** after days/weeks without re-reading all code
- ✅ **Learn** which prompts work best over time
- ✅ **Track** what each AI tool contributed
- ✅ **Share knowledge** with team members

## Workflow Integration

### Example Session: Bug Investigation

**With Claude Code** (Analysis Phase):
1. Ask Claude Code to investigate bug
2. Claude Code creates JIRA ticket in `docs/design/`
3. Update `context.md` with findings
4. Add effective prompts to `prompts.md`

**Switching to Cursor** (Implementation Phase):
1. Cursor reads `context.md` (has full context)
2. Cursor reads `docs/design/JIRA_*.md` (has implementation spec)
3. Cursor implements following `.cursorrules`
4. Update `context.md` with implementation status

**Using ChatGPT** (Review Phase):
1. Copy relevant sections from `context.md`
2. Copy JIRA ticket from `docs/design/`
3. Ask ChatGPT for alternative approaches
4. Update `context.md` with decision made

## Best Practices

### ✅ Do
- Update `context.md` before switching tools
- Keep `context.md` current (last updated date)
- Add prompts to `prompts.md` when they work exceptionally well
- Reference this directory when resuming work after time away
- Use `context.md` "Implementation Plan" checklist to track progress

### ❌ Don't
- Let `context.md` become stale (update before ending session)
- Write novel-length updates (keep it concise and scannable)
- Copy/paste entire codebase into context (link to files instead)
- Forget to update "Last Updated" and "Active Tool" fields

## File Sizes

Keep files manageable:
- `context.md`: < 500 lines (archive old sessions to separate files if needed)
- `prompts.md`: Unlimited (this grows over time, which is good)
- `decisions.md`: < 200 lines per file (create dated archives if needed)

## Maintenance

### Weekly
- Review `context.md` and archive completed tasks
- Add any new effective prompts to `prompts.md`

### Monthly
- Review `prompts.md` for patterns
- Consider creating prompt templates for common tasks
- Archive old context if file gets too large

### When Task Completes
- Update `context.md` status to "Completed"
- Move completed task context to archive if needed
- Clear "Active Task" section for next task

## Git Tracking

These files **should be committed** to git because:
- ✅ Session continuity across machines
- ✅ Team can see current work context
- ✅ Historical record of design decisions
- ✅ Learning resource for prompt engineering

**Exception**: If you have personal notes or API keys, create `.ai/personal.md` and add it to `.gitignore`.

## Related Directories

```
.ai/                    # AI workflow support (this directory)
docs/design/            # JIRA tickets and design specs
docs/architecture/      # High-level architecture
.cursorrules           # Cursor-specific AI instructions
```

## Questions?

If you're unsure whether to add something to this directory, ask:
1. Will this help me resume work later? → `context.md`
2. Will this help me write better prompts? → `prompts.md`
3. Will this help explain why we chose X over Y? → `decisions.md` (future)

---

**Remember**: These files are tools to make YOU more effective, not bureaucracy. If they're not helping, adjust them or skip them.
