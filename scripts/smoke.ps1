# Smoke test script for SRT Translator (Windows PowerShell)
# Tests basic functionality: parse SRT, verify structure, write output

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "🧪 Starting SRT Translator smoke test..." -ForegroundColor Cyan

# Test directory
$TEST_DIR = "smoke_test_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $TEST_DIR -Force | Out-Null
Set-Location $TEST_DIR

Write-Host "📁 Created test directory: $TEST_DIR" -ForegroundColor Green

# Create a minimal test SRT file
$srtContent = @"
1
00:00:01,000 --> 00:00:04,000
Hello world
This is a test subtitle

2
00:00:05,000 --> 00:00:08,000
Testing SRT parser
And writer functionality
"@
$srtContent | Out-File -FilePath "test.srt" -Encoding UTF8

Write-Host "📝 Created test SRT file with 2 subtitle entries" -ForegroundColor Green

# Test 1: Parse the SRT file
Write-Host "🔍 Testing SRT parsing..." -ForegroundColor Yellow
$parseScript = 'import sys; sys.path.insert(0, ".."); from srt_core.translator.srt_parser import SRTParser; subtitles = SRTParser.parse_file("test.srt"); print(f"Found {len(subtitles)} subtitles") if len(subtitles) == 2 else exit(1)'

python -c $parseScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ SRT parsing test failed" -ForegroundColor Red
    exit 1
}

# Test 2: Write the SRT file
Write-Host "💾 Testing SRT writing..." -ForegroundColor Yellow
$writeScript = 'import sys; sys.path.insert(0, ".."); from srt_core.translator.srt_parser import SRTParser; subtitles = SRTParser.parse_file("test.srt"); SRTParser.write_file("output.srt", subtitles); import os; print("Output file created") if os.path.exists("output.srt") else exit(1)'

python -c $writeScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ SRT writing test failed" -ForegroundColor Red
    exit 1
}

# Test 3: Verify CLI entry point exists
Write-Host "🔧 Testing CLI entry point..." -ForegroundColor Yellow
$cliScript = 'import sys; sys.path.insert(0, ".."); from srt_core.main import main; print("CLI main function found")'

python -c $cliScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ CLI entry point test failed" -ForegroundColor Red
    exit 1
}

# Test 4: Verify version information
Write-Host "📋 Testing version information..." -ForegroundColor Yellow
$versionScript = 'import sys; sys.path.insert(0, ".."); from srt_core import __version__; print(f"Version: {__version__}")'

python -c $versionScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Version information test failed" -ForegroundColor Red
    exit 1
}

# Cleanup
Set-Location ..
Remove-Item -Path $TEST_DIR -Recurse -Force

Write-Host ""
Write-Host "🎉 All smoke tests passed!" -ForegroundColor Green
Write-Host "✅ SRT parsing works" -ForegroundColor Green
Write-Host "✅ SRT writing works" -ForegroundColor Green
Write-Host "✅ CLI entry point available" -ForegroundColor Green
Write-Host "✅ Version information accessible" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 SRT Translator is ready for basic operations" -ForegroundColor Cyan
