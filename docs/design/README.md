# Design Documents

This directory contains design specifications, JIRA-style tickets, and architectural decision records (ADRs) for the SRT Translator project.

## Document Types

### JIRA Tickets
Design documents formatted as JIRA tickets with:
- Summary and description
- Root cause analysis (for bugs)
- Implementation details
- Test plans
- Acceptance criteria
- Effort estimates

**Naming Convention**: `JIRA_<DESCRIPTION>.md`

**Examples**:
- `JIRA_DNT_CORRUPTION_BUG.md` - Root cause analysis for DNT corruption
- `JIRA_STARTUP_VALIDATION.md` - Defense-in-depth validation system

### Architecture Decision Records (Future)
When architectural decisions are made, document them here following ADR format:
- Context
- Decision
- Consequences
- Status

**Naming Convention**: `ADR_<NUMBER>_<DESCRIPTION>.md`

## Organization

```
docs/
  design/
    JIRA_*.md           # Bug analysis and feature specs
    ADR_*.md            # Architectural decisions (future)
  architecture/         # High-level architecture docs
    ARCHITECTURE.md
    ...
  guides/              # User and developer guides
    GUI_USER_MANUAL.md
    CREATOR_GUIDE.md
    ...
```

## When to Create Design Docs

### Always Create for:
- Complex bugs requiring root cause analysis
- Features touching multiple files/components
- Architectural changes affecting core engine
- Changes requiring schema migrations
- Security-related modifications

### Optional for:
- Simple bug fixes (1-2 line changes)
- Cosmetic UI tweaks
- Documentation updates
- Test additions without code changes

## Using Design Docs with AI Tools

### Claude Code
- Creates comprehensive JIRA tickets with root cause analysis
- Use for: "Create a JIRA ticket for [feature/bug]"
- Outputs structured docs ready for implementation

### Cursor
- Reviews design docs for implementation
- Use: "Read docs/design/JIRA_*.md and implement the solution"
- Gets full context from written specs

### ChatGPT
- Reviews design approach for alternatives
- Use: "Review this design doc and suggest improvements"
- Good for strategic feedback, not codebase-specific implementation

## Historical Value

These documents serve as:
1. **Implementation Guides** - Detailed specs for developers
2. **Historical Record** - Why decisions were made
3. **Learning Resource** - Examples of problem-solving approaches
4. **Documentation** - Complement code comments with design rationale

## Maintenance

- Keep docs in sync with implementation
- Add "Status: Implemented" header when done
- Reference implemented features in git commits
- Archive old/obsolete docs to `docs/design/archive/`
