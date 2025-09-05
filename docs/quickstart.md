# Quickstart (GUI)

> **Before you translate:** create an **AI Config**. This builds your **DNT** (Do-Not-Translate) list and **Termbase** (preferred translations) so brand names, product terms, and course jargon stay consistent.

## 1) Install
- Download the latest macOS/Windows build (coming soon), then launch the app.

## 2) Add your source `.srt` files
- Click **Add files** and choose the subtitle files in the **original language**.

## 3) Create AI Config (required for creators)
- Click **Generate Translation Settings**.
- **Pick files deliberately** (order matters):
  1. **Intro / welcome** subtitles where instructors say their name, product/brand, course title.
  2. **Term-dense** subtitles where the most domain-specific vocabulary appears.
- The app scans the beginning of the material to find terms (details below).
- If you later add/change files or languages, click **Regenerate**.

## 4) Choose target languages
- Select target languages in **Languages**.

## 5) Translate
- Click **Translate**. The app produces translated `.srt` files per language.

## 6) Evaluate & Report
- The app writes both **`eval_report.html`** and **`eval_report.md`** with the same guidance:
  - A **Ready / Review / Fix** banner
  - **What to do next** checklist
  - **KPIs** (files, languages, issues, warnings, source language, DNT/Termbase coverage)

## 7) Fix (if needed) & Publish
- If the report says **✅ Ready**, you're done—publish.
- If **⚠️ Review** or **❌ Fix**, follow the "What to do next" steps at the top of the report.
