#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Factory-reset the SRT Translator GUI to a clean, first-run state (Windows).

.DESCRIPTION
    Removes ALL persisted SRT Translator settings so the next launch behaves
    exactly like a brand-new user opening the app for the first time. Use this
    to test the first-run experience of a built .exe without a Python
    environment.

    SRT Translator persists settings via Qt's QSettings in TWO backends, and
    BOTH must be cleared. If you delete only the .ini, the app silently
    restores your old settings from the legacy registry on the next launch via
    migrate_from_native_if_needed() (see srt_translator/gui/settings_manager.py):

      1. IniFormat    %APPDATA%\SRTTranslator\SRTTranslator.ini   (current store)
      2. NativeFormat HKCU:\Software\SRTTranslator                (legacy / migration source)

    WARNING: This ERASES your OpenAI API key (stored in plaintext in the .ini),
    target languages, tone/model settings, last-used directories, and all
    AI-generated config (termbase, DNT terms). Save your API key first.

    No backup is taken by default: the whole point of this reset is to erase
    your settings (including the plaintext API key), so copying them elsewhere
    would defeat the purpose and leave the key sitting in your TEMP directory.
    Pass -Backup if you explicitly want a reversible, timestamped copy first.

.PARAMETER Force
    Skip the interactive confirmation prompt (for automated QA).

.PARAMETER Backup
    Write a timestamped backup of both stores to your TEMP directory before
    deleting. NOTE: this backup contains your API key in plaintext.

.EXAMPLE
    .\scripts\factory_reset.ps1
    Prompts for confirmation, then wipes both stores (no backup).

.EXAMPLE
    .\scripts\factory_reset.ps1 -Force
    Wipes both stores without prompting and without a backup.

.EXAMPLE
    .\scripts\factory_reset.ps1 -Backup
    Backs up both stores first, then wipes them.
#>
[CmdletBinding()]
param(
    # Skip the "Continue? [y/N]" confirmation prompt (for non-interactive/QA use).
    [switch]$Force,
    # Save a timestamped copy of both stores to TEMP before deleting (opt-in;
    # the copy contains the plaintext API key). Off by default.
    [switch]$Backup
)

$ErrorActionPreference = "Stop"

$IniDir   = Join-Path $env:APPDATA "SRTTranslator"
$IniFile  = Join-Path $IniDir "SRTTranslator.ini"
$RegKey   = "HKCU:\Software\SRTTranslator"        # PowerShell PSDrive form
$RegNative = "HKCU\Software\SRTTranslator"        # reg.exe form (for export)

Write-Host "SRT Translator - factory reset (clean first-run state)" -ForegroundColor Cyan
Write-Host ""
Write-Host "WARNING: this permanently deletes ALL SRT Translator settings," -ForegroundColor Yellow
Write-Host "including your OpenAI API key (stored in plaintext)." -ForegroundColor Yellow
Write-Host ""

$iniExists = Test-Path $IniFile
$regExists = Test-Path $RegKey

Write-Host "Targets:"
if ($iniExists) { Write-Host "  - INI store:      $IniFile" } else { Write-Host "  - INI store:      $IniFile  (not present)" }
if ($regExists) { Write-Host "  - Registry store: $RegKey" }      else { Write-Host "  - Registry store: $RegKey  (not present)" }
Write-Host ""

if (-not $iniExists -and -not $regExists) {
    Write-Host "Nothing to remove - already in a clean state." -ForegroundColor Green
    return
}

if (-not $Force) {
    $ans = Read-Host "Continue? [y/N]"
    if ($ans -notmatch '^(y|yes)$') {
        Write-Host "Aborted. Nothing was changed."
        return
    }
}

# --- Optional backup (opt-in; contains the plaintext API key) ---
if ($Backup) {
    $stamp     = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupDir = Join-Path $env:TEMP "srt_translator_settings_backup_$stamp"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

    if ($iniExists) {
        Copy-Item -Path $IniFile -Destination (Join-Path $backupDir "SRTTranslator.ini")
        Write-Host "Backed up INI      -> $backupDir\SRTTranslator.ini"
    }
    if ($regExists) {
        $regBackup = Join-Path $backupDir "SRTTranslator.reg"
        & reg.exe export $RegNative $regBackup /y | Out-Null
        Write-Host "Backed up registry -> $regBackup"
    }
    Write-Host ""
}

# --- Delete both stores ---
# The %APPDATA%\SRTTranslator folder is created exclusively by Qt for this app's
# org, so removing the whole folder (ini + any .lock siblings) is safe.
if ($iniExists) {
    Remove-Item -Path $IniDir -Recurse -Force
    Write-Host "Removed INI store:      $IniDir" -ForegroundColor Green
}
if ($regExists) {
    Remove-Item -Path $RegKey -Recurse -Force
    Write-Host "Removed registry store: $RegKey" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. The next launch of SRT Translator will behave like a first run." -ForegroundColor Green
