# Design doc — Customizing Your Termbase

**Audience:** Content creators translating courses into multiple languages. This document explains a simple, low-risk process to produce higher-quality `termbase.json` files the **srt_translator** will consume, using supplemental bilingual content (for example, official corporate pages like Amazon Leadership Principles) and optional AI assistance. The text assumes you can download and open JSON files but does not require coding knowledge.

---

## What This Step Does

Customizing your termbase allows you to reuse terminology from existing translated content so future subtitles stay consistent.

## When You Should Use This

You already have translated website or product content.
Your brand uses specific wording consistently.
You want subtitles to match existing language choices.

## What to Provide to the AI Agent

Translated web pages.
Marketing copy.
Product descriptions.
Help center articles.
Previous subtitle files.

## How the AI Uses This Content

Using the AI prompts below, you can use your own AI agent to analyze your examples and extract preferred terms and phrases to add to the termbase before translation begins.

## Summary / goal

Many machine translations are correct in meaning but can fail to use company-preferred phrasing, role titles, or domain-specific terms. The goal of this design is to give content creators a straightforward, practical workflow to produce a stronger termbase that the srt_translator already understands and uses. The workflow relies on an external customization step — either an AI agent or a simple helper tool — that augments the srt_translator’s native termbase format. The srt_translator itself remains unchanged; it only accepts the final `termbase.json` in the exact shape it already uses. This keeps the translation runtime deterministic while enabling creators to safely benefit from external knowledge and automation.

---

## What the srt_translator does and does not do

The srt_translator applies a single JSON termbase during translation. The termbase has the following, simple structure:

```json
{
  "ar": {
    "OKRs": "أهداف ونتائج رئيسية",
    "leadership principles": "مبادئ القيادة"
  },
  "zh-Hans": {
    "Leadership Principles": "领导力准则",
    "Fulfillment center": "仓库"
  }
}
```

The app treats that JSON as authoritative. It does not attempt to fetch evidence from web pages on your behalf, it does not require a reviewer to sign off every entry, and it does not accept any alternative JSON schema. This simplicity keeps runtime behavior predictable while allowing flexible, external workflows for termbase creation and review.

---

## High-level user experience (customer-facing flow)

A content creator following this design will perform the following high-level steps:

1. Use the srt_translator to generate and export an initial `termbase.json` for the target language(s). This gives a baseline of the app's suggested mappings.
2. Collect supplemental bilingual content — for example, official company pages, translated slides, previous subtitles, or glossary documents. The Amazon Leadership Principles zh-Hans page is a strong example of an authoritative source.
3. Run an external customization step with an AI agent. The customization step reviews the original `termbase.json` and the supplemental content, and produces a `termbase.patch.json` — a JSON file in the exact srt_translator schema that includes additions and suggested changes.
4. Review the patch in a text editor. If you see a change you don't like, manually remove it from `termbase.patch.json`.
5. Once you are satisfied with the results, ask your AI agent to produce a final `termbase.json` by applying the reviewed patch to the original termbase. Avoid asking the agent to merge feedback and the termbase in a single step, as this makes review harder and increases the risk of unintended changes. Upload or commit this file in the same way the app expects.

This flow keeps the srt_translator unchanged, minimizes technical demands on the content creator, and gives a safe path to inject company-accurate phrasing into automated translations.

---

## Practical details and step-by-step guidance

### 1. Gather evidence

Create a short list of URLs and files that contain authoritative original content and its official translations. For example, if a course references Amazon-specific concepts, gather the original-language Leadership Principles page and the official translated versions (for example, zh-Hans), along with relevant internal glossaries, translated slide decks, and any previously translated subtitles. Put these links and files in a single folder or a simple text manifest so they are easy to hand to an AI agent or a helper tool.

### 2. Export the seed termbase from the srt_translator

Use the app's **Export** button in the termbase editor to get the current `termbase.json`. This file is your working seed. If the app produces termbase snapshots per batch, export the snapshot that corresponds to the course you are translating.

### 3. Run an external customization step (patch-first workflow)

In this workflow, the AI agent does not rewrite the existing termbase directly. Instead, it produces a patch that explicitly describes *what should change* and *why*.

You provide the AI agent with two inputs:

1. The current `termbase.json` generated by the srt_translator.
2. Supplemental feedback or bilingual material, such as reviewer comments, official company translations, or previously translated content.

If both an original-language source and one or more translated versions of the same content are provided, the AI agent must treat the original-language source as canonical. Translated versions should be used only to confirm official target-language phrasing. The agent should not infer new source terms from translated text alone when an original source is available.

If an original-language source is not provided or cannot be clearly identified, the agent may use translated material as evidence, but any proposed mappings based on translated-only sources must be marked as requiring review.

The AI agent's task is to compare the feedback against the existing termbase and produce a **patch artifact** that makes intent explicit. Each proposed change must fall into one of the following categories:

- **Add** — introduce a new source → target mapping that does not already exist.
- **Modify** — replace the target value for an existing source string.

Removing entries from a termbase is intentionally out of scope for this workflow and can be done manually later if needed.

Whether a change is an addition or a modification is determined by comparison with your existing `termbase.json`: new source keys are additions, while existing source keys with new target values are modifications.

The output of this step is a `termbase.patch.json` file in the same schema the srt_translator already understands. The patch exists purely for review and does not affect translation until it is explicitly merged into a final `termbase.json`.

### Required output format from the AI

When you run the AI customization step, the agent must format its output so it is safe for copy and paste by a non-technical user.

Each output file must be clearly separated and labeled, and each file must appear as its own standalone JSON block. You should be able to copy and paste each block directly into its own file without editing or cleanup.

If the output is mixed together, unlabeled, wrapped in explanations, or otherwise difficult to separate, stop and ask the AI to reformat the output before proceeding.

### What the AI should not do

The AI customization step is intentionally conservative. It should not:

- regenerate or rewrite the full termbase
- remove existing entries from the termbase
- infer terminology from subtitle or sentence context
- include markdown, URLs, or formatting in source keys
- correct general translation quality beyond what is explicitly provided in feedback

### 4. Review the patch using a text editor (no coding required)

In this workflow, review happens using your AI agent and a standard text editor. You compare the current termbase entries and the proposed changes by reading the JSON files directly.

The review step should make clear whether a suggested mapping is company-specific, because company-specific suggestions should generally be favored for courses about that company or its products.

### 5. Create the final `termbase.json` and upload it

After accepting suggestions, task your AI agent to produce the final `termbase.json`. Upload this final file to the srt_translator exactly as you would a termbase today. The srt_translator will then apply the mappings during translation.


---

## How to work with variants

Variants are alternative surface forms of the same source phrase that appear in natural text. Because the srt_translator expects `source → target` mappings in a language dictionary, the simplest and most robust convention is to add each variant as its own `source` key that maps to the same `target` string. For example, the following two entries both map to the same target phrase and ensure coverage of different surface forms:

```json
{
  "zh-Hans": {
    "Single-threaded Leader": "单一负责人",
    "single threaded leader": "单一负责人"
  }
}
```

When customizing a termbase, auto-generate obvious variants such as hyphenation/non-hyphenation, differences in capitalization, and singular/plural forms. The AI prompt already has the variant instructions, but you will want to double-check the results.

---

## Example with Amazon Leadership Principles

If you have the Amazon Leadership Principles page in English and the zh-Hans page, an AI agent should search the two pages and, for the canonical term “Leadership Principles,” add the mapping:

```json
{
  "zh-Hans": {
    "Leadership Principles": "领导力准则"
  }
}
```

When you review the patch, you can verify this mapping by checking the original and translated pages side-by-side.

---

## Default and conservative merge rules (for non-technical creators)

To reduce risk, instruct your AI agent to follow conservative defaults when proposing changes to the termbase. These defaults are designed to minimize accidental regressions and to ensure that human reviewers remain in control.

During review, content creators should verify proposed changes against their source material. Mappings backed by official public URLs can generally be accepted with confidence. Mappings based on reviewer feedback or inferred from context should be confirmed with a trusted reviewer, especially if the content creator does not speak the target language. When a proposed mapping conflicts with an existing entry for the same source string, always require manual resolution.

These defaults are intentionally conservative. They prevent the agent from silently overwriting a trusted mapping.

---


## Quality assurance and acceptance criteria

To ensure this process produces reliable results, check the following before you consider the termbase ready for production use:

1. The final `termbase.json` is valid JSON and follows the exact schema `{"<lang>": {"<source>": "<target>"}}`. The srt_translator will reject non-conforming structure.
2. The majority of added/changed mappings backed by official sources are accepted without manual editing and pass sample-in-context checks.
3. All conflicts between existing mappings and proposed changes are resolved explicitly — none are changed silently.
4. A small sample translation that exercises the new terms shows natural usage and correct collocation in context.

---

## Privacy, security, and practical notes

Do not share or upload private corporate documents to an external service without permission. If you use an external AI agent that fetches evidence URLs, ensure the agent respects access controls and privacy policies. Prefer running agents within your organization or with a controlled third party when you deal with proprietary materials.

---

## Closing

This design keeps the srt_translator intentionally simple while giving content creators a safe, auditable path to improve termbase quality using supplemental bilingual content. The key ideas are: keep the runtime termbase schema unchanged, perform evidence-backed customization outside the app, represent variants as separate source keys, and require an explicit review before committing the final `termbase.json`. Following this pattern will reduce post-translation editing and increase the accuracy and consistency of your course translations.

---

## Appendix: Reference AI Prompts (Optional)

The following prompts can be used with your preferred AI agent to execute the patch-first workflow described in this document.

If the AI output is not clearly formatted, ask it to reply again using the required format.

### Prompt 1 — Produce `termbase.patch.json`

````text
You are an assistant that proposes conservative improvements to a termbase used by the srt_translator.

IMPORTANT — Original vs. Translated Sources
- If both an original-language source and one or more official translated versions of the same content are provided, treat the original-language source as canonical for identifying source terms.
- Use translated versions only to confirm official target-language phrasing.
- Do NOT infer or invent source-language terms based solely on translated text when an original source is available.
- If no original-language source is available, the agent may use translated material as evidence, but any mappings derived this way MUST be flagged for review.

INPUTS I WILL PROVIDE
(A) termbase.json in this exact schema:
    {"<lang>": {"<source>": "<target>"}}
(B) supplemental bilingual material and/or reviewer feedback (URLs, excerpts, emails, prior translations).

YOUR TASK
Produce EXACTLY ONE JSON output: `termbase.patch.json`.

OUTPUT FORMAT (MANDATORY — COPY/PASTE SAFE)
Output MUST be exactly the following, in this order, and nothing else:

**Note for content creators:** The `REVIEW THESE TERMS` block is for human review only. **Do not** include the review text or the `--- FILE: … ---` marker in the JSON file. Copy **only** the JSON contained inside the fenced code block into `termbase.patch.json`.

1) A plain-text section titled exactly:
REVIEW THESE TERMS:
List only the specific `source → target` mappings that you believe warrant human confirmation, one mapping per line, using the exact arrow `→`. If none, write:
(none)

2) A line that is exactly:
--- FILE: termbase.patch.json ---

3) A fenced JSON code block containing ONLY pretty-printed JSON (not minified), using the top-level language map schema:
```json
{
  "<lang>": {
    "<source>": "<target>",
    ...
  },
  ...
}
```

ABSOLUTE RULES (do not deviate)
- Do NOT output any other text before, after, or between the sections above. If you cannot comply with the format, output ONLY:
  FORMAT_ERROR
- The JSON must be valid, pretty-printed, and use Unicode characters unescaped (readable non-ASCII).
- The patch must use the top-level schema `{"<lang>": {...}}` (this matches the app loader).
- Include ONLY proposed additions or modifications. Do NOT include deletions or delete markers.
- Do NOT create duplicates that differ only by capitalization unless the reviewer explicitly requested casing variants.
- Source keys must be plain phrases: strip surrounding markdown, bracket wrappers, or URLs. If reviewer text contains formatted links like `[text](url)`, extract only `text` as the source key.
- Generate variants only for plural/singular or hyphenation/non-hyphenation when likely to appear in subtitles.
- If uncertain about any mapping, omit it rather than guessing.
- The patch must contain only string → string mappings; omit any candidate mapping where either the source or the target is not a string.

REVIEW FLAGGING RULES
Flag a mapping for review (include it under the REVIEW header) ONLY if at least one of the following is true:
- The mapping is inferred rather than explicitly supported by reviewer evidence or aligned original+translated sources.
- The term is idiomatic, highly context-dependent, or culturally sensitive.
- The change overwrites an existing mapping in a non-obvious way (significant meaning change).
- The mapping was derived from translated-only evidence (no canonical original-language source available).

OTHER CONSTRAINTS
- Do not attempt to merge the patch into the termbase in this step — the patch is for review only.
- Do not call external services or perform web requests.
- Do not include explanations, reasoning, or help text in the output.

When I provide inputs, follow the rules exactly and output only the REVIEW block, the `--- FILE` line, and the fenced JSON block containing `termbase.patch.json`.

--- END OF PROMPT ---
````

---

### Prompt 2 — Apply an approved patch to produce final `termbase.json`

```text
You are an assistant that applies an approved termbase.patch.json to produce a final termbase.json that the srt_translator GUI can import directly.

INPUTS (plain text):
- ORIGINAL_JSON: the current termbase exported from the SRT app (may be either):
    A) top-level languages: {"<lang>": {"<source>": "<target>"}}
    B) wrapper schema: {"termbase": {"<lang>": {"<source>": "<target>"}}}  (accepted for robustness)
- PATCH_JSON: the reviewed and approved termbase.patch.json (may be top-level or wrapper).

GOAL
Produce a single final JSON document `termbase.json` using the exact top-level schema the existing loader expects:

{
  "<lang>": {
    "<source>": "<target>",
    ...
  },
  ...
}

IMPORTANT OUTPUT RULES
- Output ONLY the final JSON document (no headers, no review text, no explanation).
- The JSON must be valid, pretty-printed, and use Unicode characters unescaped.
- The final JSON must use the top-level language map schema (no "termbase" wrapper).

NORMALIZATION (first)
1. If ORIGINAL_JSON contains a top-level "termbase" key, set ORIGINAL := ORIGINAL_JSON["termbase"]; otherwise ORIGINAL := ORIGINAL_JSON.
2. If PATCH_JSON contains a top-level "termbase" key, set PATCH := PATCH_JSON["termbase"]; otherwise PATCH := PATCH_JSON.
3. After normalization, ORIGINAL and PATCH must be dictionaries mapping language tags → {source: target} dictionaries.

MERGE RULES (apply PATCH → ORIGINAL)
1. For each language L in PATCH:
   a. If L not in ORIGINAL, add ORIGINAL[L] = {}.
   b. For each source key S_raw in PATCH[L]:
      i. Extract a clean source key S by stripping leading/trailing whitespace and removing surrounding markdown or bracket/URL wrappers (e.g., [text](url) → text). Preserve internal punctuation and original casing for S.
      ii. If ORIGINAL[L] already contains a key that differs from S only by capitalization (case-insensitive match), do not create a new key. Overwrite the existing ORIGINAL[L] entry's value with PATCH[L][S_raw] and preserve the existing key's exact casing.
      iii. Otherwise set ORIGINAL[L][S] = PATCH[L][S_raw] (this adds or overwrites).
2. Do NOT remove keys from ORIGINAL.
3. Overwrites are allowed and applied only when PATCH explicitly provides a mapping.
4. Do NOT invent or guess mappings not present in PATCH.
5. Treat distinct language tags as distinct (do not auto-merge "zh" and "zh-Hans"). If both exist and appear related, do not reconcile automatically.

VALIDATION / SAFEGUARDS
- If PATCH contains entries that are not string→string, ignore those invalid entries and continue merging valid ones (prefer partial success).
- If PATCH is empty or missing, return ORIGINAL (normalized) as-is.
- If ORIGINAL is empty or missing, return PATCH (normalized) as-is.
- No network calls or web requests.

FINAL OUTPUT
- Output the merged result as a single top-level JSON object:
  {
    "<lang>": {
      "<source>": "<target>",
      ...
    },
    ...
  }
- Output ONLY that JSON document (pretty-printed, Unicode unescaped), and nothing else.

STRICT CONSTRAINT
- Do not output any explanatory text, logs, or a review list. The output must be a single valid JSON document in the required top-level schema suitable for direct upload using the SRT GUI Import Termbase button.

--- END OF PROMPT ---
```
