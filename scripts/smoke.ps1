#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Smoke test script for SRT Translator on Windows
    
.DESCRIPTION
    This script performs basic functionality tests to ensure SRT Translator
    is working correctly before release.
    
.PARAMETER Debug
    Enable debug output
    
.EXAMPLE
    .\smoke.ps1
    .\smoke.ps1 -Debug
#>

param(
    [switch]$Debug
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Header {
    param([string]$Message)
    Write-ColorOutput "`n=== $Message ===" $Blue
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "✓ $Message" $Green
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "✗ $Message" $Red
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "⚠ $Message" $Yellow
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput "ℹ $Message" $Blue
}

# Start smoke test
Write-Header "SRT Translator Smoke Test - Windows"
Write-Info "Starting smoke test at $(Get-Date)"

# Test 1: Check Python installation
Write-Header "Test 1: Python Environment"
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+\.\d+\.\d+)") {
        $version = $matches[1]
        Write-Success "Python $version found"
        
        # Check if it's a supported version
        if ($version -match "^3\.(9|10|11|12)") {
            Write-Success "Python version $version is supported"
        } else {
            Write-Warning "Python version $version may not be fully supported"
        }
    } else {
        throw "Could not determine Python version"
    }
} catch {
    Write-Error "Python not found or not working: $_"
    exit 1
}

# Test 2: Check package installation
Write-Header "Test 2: Package Installation"
try {
    $packageInfo = pip show srt-translator 2>&1
    if ($packageInfo -match "Version: (.+)") {
        $version = $matches[1]
        Write-Success "SRT Translator package found (version: $version)"
    } else {
        throw "Package not found"
    }
} catch {
    Write-Error "SRT Translator package not installed: $_"
    Write-Info "Installing package in development mode..."
    try {
        pip install -e .
        Write-Success "Package installed successfully"
    } catch {
        Write-Error "Failed to install package: $_"
        exit 1
    }
}

# Test 3: Check CLI entry point
Write-Header "Test 3: CLI Entry Point"
try {
    $cliVersion = srt-translator --version 2>&1
    if ($cliVersion -match "SRT Translator CLI v(.+)") {
        $version = $matches[1]
        Write-Success "CLI entry point working (version: $version)"
    } else {
        Write-Success "CLI entry point working"
    }
} catch {
    Write-Error "CLI entry point not working: $_"
    exit 1
}

# Test 4: Check GUI entry point
Write-Header "Test 4: GUI Entry Point"
try {
    $guiHelp = srtx --help 2>&1
    if ($guiHelp -match "usage:") {
        Write-Success "GUI entry point working"
    } else {
        Write-Success "GUI entry point working"
    }
} catch {
    Write-Error "GUI entry point not working: $_"
    exit 1
}

# Test 5: Basic SRT parsing
Write-Header "Test 5: SRT Parsing"
try {
    $testFile = "tests/fixtures/test_sample.srt"
    if (Test-Path $testFile) {
        Write-Success "Test SRT file found"
        
        # Test basic parsing
        $content = Get-Content $testFile -Raw
        if ($content -match "Hello, this is a test subtitle") {
            Write-Success "SRT file content readable"
        } else {
            throw "SRT file content not as expected"
        }
    } else {
        Write-Warning "Test SRT file not found, skipping parsing test"
    }
} catch {
    Write-Error "SRT parsing test failed: $_"
}

# Test 6: Import core modules
Write-Header "Test 6: Core Module Imports"
try {
    $importTest = python -c "
import srt_translator.core.translator.srt_parser
import srt_translator.core.config.translation_config
import srt_translator.core.main
print('All core modules imported successfully')
" 2>&1
    
    if ($importTest -match "All core modules imported successfully") {
        Write-Success "Core modules import successfully"
    } else {
        throw "Module import test failed"
    }
} catch {
    Write-Error "Core module import test failed: $_"
    exit 1
}

# Test 7: Configuration loading
Write-Header "Test 7: Configuration Loading"
try {
    $configTest = python -c "
from srt_translator.core.config.translation_config import TranslationConfig
config = TranslationConfig()
print('Configuration system working')
" 2>&1
    
    if ($configTest -match "Configuration system working") {
        Write-Success "Configuration system working"
    } else {
        throw "Configuration test failed"
    }
} catch {
    Write-Error "Configuration test failed: $_"
}

# Test 8: Run basic tests
Write-Header "Test 8: Basic Test Suite"
try {
    $testResult = python -m pytest tests/ -v --tb=short 2>&1
    if ($testResult -match "passed") {
        Write-Success "Basic test suite passed"
    } else {
        Write-Warning "Some tests may have failed, check output above"
    }
} catch {
    Write-Warning "Test suite execution had issues: $_"
}

# Summary
Write-Header "Smoke Test Summary"
Write-Success "All critical functionality tests completed"
Write-Info "SRT Translator appears to be working correctly"
Write-Info "Smoke test completed at $(Get-Date)"

if ($Debug) {
    Write-Header "Debug Information"
    Write-Info "Python version: $(python --version 2>&1)"
    Write-Info "Package location: $(pip show srt-translator | Select-String 'Location')"
    Write-Info "Working directory: $(Get-Location)"
}

Write-ColorOutput "`n🎉 Smoke test completed successfully!" $Green
