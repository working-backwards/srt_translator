# Testing a Clean / First-Run State

This guide explains how to reset SRT Translator to a **completely clean state**,
so the app behaves exactly as it would for a brand-new user launching it for the
first time. It is aimed at QA and release testers working with a **built `.exe`
or `.dmg`** — no Python environment is required.

## Why this is needed

SRT Translator persists user state (API key, language selections, tone/model
settings, last-used directories, and AI-generated termbase/DNT data) on the
local machine. Once you have run the app even once, that state sticks around and
**masks the first-run experience**. You can no longer see:

- the empty/default form a new user sees,
- the "enter your OpenAI API key" prompts and onboarding flow,
- first-run defaults for model, tone, and languages,
- any setup validation or empty-state messaging.

Common situations where you need a genuine clean state:

- **QA of a release build** — verifying the out-of-the-box experience of the
  `.exe` / `.dmg` before shipping.
- **Reproducing a new-user bug report** — a problem that only happens when no
  settings exist yet.
- **Testing onboarding / first-run UI changes** — confirming prompts, defaults,
  and empty states render correctly.
- **Clearing a corrupted or stale config** — starting over after experimenting
  with different settings.
- **Demos and screenshots** — capturing the pristine first-run UI.

> [!WARNING]
> A clean reset **erases your OpenAI API key**. The key is stored in **plaintext**
> in the app's settings (the app does not use the OS keychain — see
> [architecture.md](architecture.md)). Save your key somewhere safe before
> resetting; you will re-enter it on next launch, which is itself part of the
> authentic first-run experience.

## The critical detail: there are TWO settings stores

SRT Translator uses Qt's `QSettings` with **two different backends**, and a
clean reset must clear **both**. Clearing only one is the most common mistake.

| Backend | Role | Windows | macOS | Linux |
|---|---|---|---|---|
| **IniFormat** | Current store (what the app reads/writes today) | `%APPDATA%\SRTTranslator\SRTTranslator.ini` | `~/.config/SRTTranslator/SRTTranslator.ini` | `~/.config/SRTTranslator/SRTTranslator.ini` |
| **NativeFormat** | Legacy store / migration source | `HKCU\Software\SRTTranslator` (registry) | `~/Library/Preferences/*SRTTranslator*.plist` | `~/.config/SRTTranslator/SRTTranslator.conf` |

**Why both matter:** on launch, if the IniFormat store is empty, the app runs a
one-shot migration that **copies everything back from the legacy NativeFormat
store** (`migrate_from_native_if_needed()` in
[`settings_manager.py`](../../srt_translator/gui/settings_manager.py)). So if you
delete only the `.ini` file, your old settings **silently come back** on the
next launch and you do *not* get a clean first-run. You must clear the legacy
store too.

On macOS there is an extra wrinkle: preferences are cached in memory by
`cfprefsd`, so deleting the `.plist` on disk is not enough on its own — the
cache must also be flushed.

## The easy way: use the factory-reset scripts

The repo ships scripts that wipe **both** stores, with a confirmation prompt.

By design they take **no backup by default** — the goal is to erase your
settings (including the plaintext API key), so copying them elsewhere would
defeat the purpose and leave the key sitting in a temp folder. If you want a
reversible copy first, pass `-Backup` / `--backup` (see
[Reverting](#reverting-restoring-your-settings)).

### Windows (`.exe`)

```powershell
# From the repo root:
.\scripts\factory_reset.ps1

# Non-interactive (e.g. automated QA):
.\scripts\factory_reset.ps1 -Force

# Back up both stores first (backup contains your API key in plaintext):
.\scripts\factory_reset.ps1 -Backup
```

### macOS (`.dmg`) / Linux

```bash
# From the repo root:
bash scripts/factory_reset.sh

# Non-interactive:
bash scripts/factory_reset.sh --force

# Back up first (backup contains your API key in plaintext):
bash scripts/factory_reset.sh --backup
```

Both scripts:

1. Print exactly which stores they will delete.
2. Ask for confirmation (unless `-Force` / `--force`).
3. Delete the IniFormat store **and** the legacy NativeFormat store (registry on
   Windows; plist + `cfprefsd` flush on macOS; `.conf` on Linux).
4. Optionally (only with `-Backup` / `--backup`) write a timestamped copy of each
   store to `TEMP` / `$TMPDIR` first and print the backup path.

### Flags

| Windows (`.ps1`) | macOS/Linux (`.sh`) | Default | What it does |
|---|---|---|---|
| *(none)* | *(none)* | — | Interactive: lists the target stores, asks `Continue? [y/N]`, then wipes both. No backup. |
| `-Force` | `--force` / `-f` | off | **Skip the confirmation prompt.** For non-interactive/automated QA runs. Does not change what is deleted. |
| `-Backup` | `--backup` | off | **Save a timestamped copy of both stores** to `TEMP`/`$TMPDIR` before deleting, so the reset is reversible. ⚠️ The copy contains your **API key in plaintext** — that's why it's opt-in. |
| `Get-Help .\factory_reset.ps1` | `--help` / `-h` | — | Show usage. |

Flags are independent and combinable, e.g. `-Force -Backup` / `--force --backup`
= back up first, then wipe, without prompting.

### Recommended test loop

1. **Quit the app completely** (so it isn't holding settings in memory or
   re-writing them on exit).
2. Run the factory-reset script for your platform.
3. Launch the `.exe` / `.app`.
4. Confirm you see the genuine first-run state: no API key, default model/tone,
   empty language selection, default directories.

## Reverting (restoring your settings)

This only applies if you ran the reset with `-Backup` / `--backup`. Without that
flag, no backup is taken — re-launch the app and re-enter your settings instead.

From a backup folder, restore with:

- **Windows INI:** copy `SRTTranslator.ini` from the backup folder back to
  `%APPDATA%\SRTTranslator\`.
- **Windows registry:** double-click the backed-up `SRTTranslator.reg`, or run
  `reg import "<path>\SRTTranslator.reg"`.
- **macOS / Linux INI:** copy `SRTTranslator.ini` back to
  `~/.config/SRTTranslator/`.
- **macOS plist:** copy the `*.plist` back to `~/Library/Preferences/` and run
  `killall cfprefsd` to refresh the cache.

Or simply re-launch the app and re-enter your settings from scratch.

## Manual alternative (no scripts)

If you prefer to do it by hand, delete both stores directly.

**Windows (PowerShell):**

```powershell
Remove-Item -Recurse -Force "$env:APPDATA\SRTTranslator" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "HKCU:\Software\SRTTranslator" -ErrorAction SilentlyContinue
```

**macOS:**

```bash
rm -rf ~/.config/SRTTranslator
find ~/Library/Preferences -iname '*SRTTranslator*'   # confirm the real filename
defaults delete SRTTranslator 2>/dev/null || true
rm -f ~/Library/Preferences/*SRTTranslator*.plist
killall cfprefsd                                       # flush the cache
```

## Related: clearing only part of the config

If you do **not** want a full reset — e.g. keep your API key but regenerate AI
config — use the Python developer scripts instead (these require a dev
environment and operate via `SettingsManager`):

- `scripts/clear_ai_only.py` — clears only the `ai_*` keys (termbase, DNT terms,
  source language, timestamps); **preserves** API key, languages, tone, and
  directories.
- `scripts/clear_ai_config.py` — clears AI-generated config and resets GUI state.

See [`scripts/README.md`](../../scripts/README.md) for details.
