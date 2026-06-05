#!/usr/bin/env bash
#
# Factory-reset the SRT Translator GUI to a clean, first-run state (macOS / Linux).
#
# Removes ALL persisted SRT Translator settings so the next launch behaves
# exactly like a brand-new user opening the app for the first time. Use this to
# test the first-run experience of a built .dmg/.app without a Python
# environment.
#
# SRT Translator persists settings via Qt's QSettings in TWO backends, and BOTH
# must be cleared. If you delete only the .ini, the app silently restores your
# old settings from the legacy plist on the next launch via
# migrate_from_native_if_needed() (see srt_translator/gui/settings_manager.py):
#
#   macOS:
#     1. IniFormat    ~/.config/SRTTranslator/SRTTranslator.ini      (current store)
#     2. NativeFormat ~/Library/Preferences/*SRTTranslator*.plist    (legacy / migration source)
#   Linux:
#     1. IniFormat    ~/.config/SRTTranslator/SRTTranslator.ini      (current store)
#     2. NativeFormat ~/.config/SRTTranslator/SRTTranslator.conf     (legacy / migration source)
#
# WARNING: This ERASES your OpenAI API key (stored in plaintext in the .ini),
# target languages, tone/model settings, last-used directories, and all
# AI-generated config (termbase, DNT terms). Save your API key first.
#
# No backup is taken by default: the whole point of this reset is to erase your
# settings (including the plaintext API key), so copying them elsewhere would
# defeat the purpose and leave the key sitting under $TMPDIR. Pass --backup if
# you explicitly want a reversible, timestamped copy first.
#
# Usage:
#   scripts/factory_reset.sh            # prompt, then wipe (no backup)
#   scripts/factory_reset.sh --force    # wipe without prompting
#   scripts/factory_reset.sh --backup   # back up first (contains the API key)
#   scripts/factory_reset.sh --help

FORCE=0   # --force/-f: skip the "Continue? [y/N]" prompt (non-interactive/QA use)
BACKUP=0  # --backup:   save a timestamped copy of both stores first (opt-in;
          #             the copy contains the plaintext API key). Off by default.
for arg in "$@"; do
  case "$arg" in
    -f|--force)  FORCE=1 ;;
    --backup)    BACKUP=1 ;;
    -h|--help)   sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

os="$(uname -s)"
ini_dir="$HOME/.config/SRTTranslator"
ini_file="$ini_dir/SRTTranslator.ini"

# Collect any macOS plist whose name contains SRTTranslator.
shopt -s nullglob 2>/dev/null || true
plists=()
if [ "$os" = "Darwin" ]; then
  plists=("$HOME/Library/Preferences/"*SRTTranslator*.plist)
fi

echo "SRT Translator - factory reset (clean first-run state)"
echo
echo "WARNING: this permanently deletes ALL SRT Translator settings,"
echo "including your OpenAI API key (stored in plaintext). Save your key first."
echo
echo "Targets:"
found=0
if [ -e "$ini_file" ]; then echo "  - INI store:   $ini_file"; found=1; fi
for p in "${plists[@]}"; do echo "  - plist store: $p"; found=1; done
if [ "$os" = "Darwin" ]; then
  echo "  - macOS preferences cache (cfprefsd) will also be flushed"
fi
if [ "$found" -eq 0 ]; then
  echo "  (no settings files found)"
fi
echo

# On non-macOS, if no files exist there is genuinely nothing to do. On macOS the
# preferences may live only in the cfprefsd cache, so we still proceed to flush.
if [ "$found" -eq 0 ] && [ "$os" != "Darwin" ]; then
  echo "Nothing to remove - already in a clean state."
  exit 0
fi

if [ "$FORCE" -ne 1 ]; then
  printf "Continue? [y/N] "
  read -r ans
  case "$ans" in
    y|Y|yes|YES) ;;
    *) echo "Aborted. Nothing was changed."; exit 0 ;;
  esac
fi

# --- Optional backup (opt-in; contains the plaintext API key) ---
if [ "$BACKUP" -eq 1 ] && [ "$found" -ne 0 ]; then
  stamp="$(date +%Y%m%d-%H%M%S)"
  backup_dir="${TMPDIR:-/tmp}/srt_translator_settings_backup_$stamp"
  mkdir -p "$backup_dir"
  if [ -e "$ini_file" ]; then
    cp "$ini_file" "$backup_dir/"
    echo "Backed up INI   -> $backup_dir/SRTTranslator.ini"
  fi
  for p in "${plists[@]}"; do
    if [ -e "$p" ]; then
      cp "$p" "$backup_dir/"
      echo "Backed up plist -> $backup_dir/$(basename "$p")"
    fi
  done
  echo
fi

# --- Delete both stores ---
# The ~/.config/SRTTranslator dir is created exclusively by Qt for this app's
# org (it also holds the Linux .conf native store), so removing the whole folder
# is safe and covers both backends on Linux.
if [ -d "$ini_dir" ]; then
  rm -rf "$ini_dir"
  echo "Removed INI store: $ini_dir"
fi

if [ "$os" = "Darwin" ]; then
  for p in "${plists[@]}"; do
    if [ -e "$p" ]; then
      rm -f "$p"
      echo "Removed plist:     $p"
    fi
  done
  # cfprefsd caches preferences in memory, so deleting the plist on disk is not
  # enough on its own - clear the domains and flush the cache daemon.
  defaults delete SRTTranslator >/dev/null 2>&1 || true
  defaults delete com.SRTTranslator.SRTTranslator >/dev/null 2>&1 || true
  killall cfprefsd >/dev/null 2>&1 || true
  echo "Flushed macOS preferences cache (cfprefsd)."
fi

echo
echo "Done. The next launch of SRT Translator will behave like a first run."
