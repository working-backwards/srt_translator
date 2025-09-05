# Create AI Config (DNT & Termbase)

**Goal:** lock down names and terminology before translation.

- **DNT (Do-Not-Translate):** exact strings that must stay the same (brand, product, people).
- **Termbase:** preferred translations for domain terms (so "input metrics" doesn't become 10 different phrases).

## Recommended workflow (creators)

1) **Add your source `.srt` files** in a deliberate order:
   - First add **intro / welcome** subtitles where instructors state names, brand, course title.
   - Next add **term-dense** subtitles that contain the most domain-specific vocabulary for the class.
2) Click **Generate Translation Settings**.
3) Review the **DNT** and **Termbase** lists in the app. If they look light or off-topic:
   - Reorder your input list (put term-dense files earlier),
   - Add/replace files with stronger vocabulary,
   - Click **Regenerate**.

> **Why order matters:** the app scans the **beginning** of your selected content to extract terms. Put the most useful material **first**.

## "Tokens" in plain English

The app scans about **12,500 tokens** from the start of your selected files. In everyday terms:

- **~12,500 tokens ≈ 9,000–10,000 English words**, roughly **45–65 minutes** of spoken content (varies with speaking speed and style).
- It's the **first chunk** of your material—not the whole course.

If your DNT/Termbase feels incomplete, move the **most term-dense** segments into the **first hour** of the selection and regenerate.

## When to regenerate

- You changed the set or the order of input `.srt` files
- You changed target languages
- Your DNT/Termbase looks too short or misses key terms

## Optional for experts, recommended for creators

Technically you can translate without DNT/Termbase. For **non-technical creators**, we strongly recommend:
- **Always** generate AI Config first
- **Spot-check** the lists
- Then translate
