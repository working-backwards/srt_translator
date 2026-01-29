# AI Prompting Journal

Track effective and ineffective prompts to build a personal library of what works with different AI tools.

---

## Effective Prompts

### Claude Code - Root Cause Analysis

**Date**: 2026-01-25

**Prompt**:
> "I don't want you to fix the bug yet. I want you to tell me why the bug is happening, why it is not reproduceable on every machine, and how to fix it."

**Why it worked**:
- Explicitly separated analysis from implementation
- Asked for three distinct things: root cause, reproducibility explanation, solution
- "Why not reproducible" was key - led to Windows Registry vs Mac plist insight
- Forced deep investigation instead of quick fix

**Result**:
- Identified 3-factor root cause (asymmetric save + QSettings serialization + historical corruption)
- Discovered platform-specific behavior (Windows Registry preserves corruption)
- Created comprehensive JIRA ticket with edge cases

**Tool**: Claude Code

**Task Type**: Bug investigation

**Key Insight**: Asking "why not reproducible on all machines?" is a powerful debugging question that reveals environmental factors.

---

### Claude Code - Defensive Design Specification

**Date**: 2026-01-25

**Prompt**:
> "Can you create a title and description for a Jira ticket for the defensive approach?"

**Why it worked**:
- Asked for structured output format (JIRA ticket)
- "Defensive approach" clarified solution strategy (not just fix the bug)
- Got implementation-ready spec with acceptance criteria

**Result**:
- JIRA_STARTUP_VALIDATION.md with 3-layer defense strategy
- Import-time validation, startup validation, defensive loading
- Test plan, edge cases, effort estimates included

**Tool**: Claude Code

**Task Type**: Design documentation

**Key Insight**: Asking for JIRA format gets structured, implementation-ready specifications.

---

### Claude Code - Follow-up Clarification

**Date**: 2026-01-25

**Prompt**:
> "Does this fix just check the schema versioning, or does it check the actual config? For instance, what happens if I upload a Termbase that is in the wrong format, quit the GUI, restart the GUI?"

**Why it worked**:
- Identified gap in proposed solution (only validated on startup, not import)
- Concrete scenario helped AI understand the edge case
- "For instance" with specific example made the question clear

**Result**:
- Updated JIRA ticket with Component 2 (import-time validation)
- Added 4 integration tests for import validation
- More comprehensive defense-in-depth approach

**Tool**: Claude Code

**Task Type**: Design review / gap analysis

**Key Insight**: Concrete scenarios ("what happens if...") help AI find gaps in proposed solutions.

---

## Ineffective Prompts

### Initial Bug Report (Too Vague)

**Date**: 2026-01-25

**Prompt** (hypothetical):
> "Help me fix this bug"

**Why it would fail**:
- No context about what the bug is
- No indication whether I want analysis or implementation
- Would get generic troubleshooting steps

**Lesson**: Always provide context and specify what kind of help you need (analysis, implementation, review, etc.)

---

### Ambiguous Investigation Request

**Date**: 2026-01-25

**Prompt** (hypothetical):
> "Search for DNT in the codebase"

**Why it's suboptimal**:
- Could use quick Grep (finds string matches only)
- Doesn't signal need for thorough investigation
- Won't find related patterns or similar issues

**Better Alternative**:
> "Find all places in the codebase where DNT terms are saved or loaded, and explain the data flow"

**Lesson**: Phrase searches as "find all places" or "understand how" to trigger deeper exploration.

---

## Prompt Patterns That Work

### Pattern: Explicit Separation of Phases

**Template**: "I don't want you to [implement/fix] yet. I want you to [analyze/explain/design] first."

**Example**: "I don't want you to implement the validation yet. I want you to design the approach and identify edge cases."

**When to use**: Complex features where planning is critical

---

### Pattern: Three-Part Questions

**Template**: "Why does X happen? Why doesn't it happen on Y? How should we fix it?"

**Example**: "Why does the corruption occur? Why only on Windows machines? How should we prevent it?"

**When to use**: Debugging reproducibility issues or platform-specific bugs

---

### Pattern: Concrete Scenario Testing

**Template**: "What happens if [specific user action sequence]?"

**Example**: "What happens if I upload a malformed termbase, quit the GUI, restart the GUI?"

**When to use**: Testing proposed solutions for gaps or edge cases

---

### Pattern: Structured Output Request

**Template**: "Create a [format] for [task]"

**Example**: "Create a JIRA ticket for the defensive validation approach"

**When to use**: When you need implementation-ready documentation

---

## Tool-Specific Notes

### Claude Code
- **Strengths**: Deep codebase analysis, multi-file investigation, creating design docs
- **Best for**: "Why" questions, "Find all" searches, creating JIRA tickets
- **Phrasing**: Use "analyze", "investigate", "create a ticket for"

### Cursor (to be filled in as used)
- **Strengths**: TBD
- **Best for**: TBD
- **Phrasing**: TBD

### ChatGPT (to be filled in as used)
- **Strengths**: General strategy, architecture patterns, writing content
- **Best for**: TBD
- **Phrasing**: TBD

---

## Metrics to Track

As you use this journal, consider tracking:
- Which prompts led to correct solutions vs. needed iteration
- Which tool responded best to which prompt style
- How prompt phrasing affected quality of output
- Patterns that consistently work vs. consistently fail

---

## Future Sections to Add

- [ ] Cursor-specific effective prompts
- [ ] ChatGPT-specific effective prompts
- [ ] Prompts for code review
- [ ] Prompts for test generation
- [ ] Prompts for documentation writing
