#!/bin/bash
# Smoke test script for SRT Translator
# Tests basic functionality: parse SRT, verify structure, write output

set -e  # Exit on any error

echo "🧪 Starting SRT Translator smoke test..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test directory
TEST_DIR="smoke_test_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "📁 Created test directory: $TEST_DIR"

# Create a minimal test SRT file
cat > "test.srt" << 'EOF'
1
00:00:01,000 --> 00:00:04,000
Hello world
This is a test subtitle

2
00:00:05,000 --> 00:00:08,000
Testing SRT parser
And writer functionality
EOF

echo "📝 Created test SRT file with 2 subtitle entries"

# Test 1: Parse the SRT file
echo "🔍 Testing SRT parsing..."
python3 -c "
import sys
sys.path.insert(0, '..')
from srt_core.translator.srt_parser import SRTParser

subtitles = SRTParser.parse_file('test.srt')
if len(subtitles) == 2:
    print('✅ SRT parsing successful: found', len(subtitles), 'subtitles')
    for i, sub in enumerate(subtitles, 1):
        print(f'   {i}. {sub.start} --> {sub.end}: \"{sub.content}\"')
else:
    print('❌ SRT parsing failed: expected 2 subtitles, got', len(subtitles))
    sys.exit(1)
"

# Test 2: Write the SRT file
echo "💾 Testing SRT writing..."
python3 -c "
import sys
sys.path.insert(0, '..')
from srt_core.translator.srt_parser import SRTParser

subtitles = SRTParser.parse_file('test.srt')
SRTParser.write_file('output.srt', subtitles)

# Verify output file exists and has content
import os
if os.path.exists('output.srt'):
    with open('output.srt', 'r') as f:
        content = f.read()
    if 'Hello world' in content and 'Testing SRT parser' in content:
        print('✅ SRT writing successful: output.srt created with correct content')
    else:
        print('❌ SRT writing failed: output file missing expected content')
        sys.exit(1)
else:
    print('❌ SRT writing failed: output.srt not created')
    sys.exit(1)
"

# Test 3: Verify CLI entry point exists
echo "🔧 Testing CLI entry point..."
python3 -c "
import sys
sys.path.insert(0, '..')
try:
    from srt_core.main import main
    print('✅ CLI main function found and importable')
except ImportError as e:
    print('❌ CLI main function import failed:', e)
    sys.exit(1)
"

# Test 4: Verify version information
echo "📋 Testing version information..."
python3 -c "
import sys
sys.path.insert(0, '..')
try:
    from srt_core import __version__
    print(f'✅ Version information available: {__version__}')
except ImportError as e:
    print('❌ Version information import failed:', e)
    sys.exit(1)
"

# Cleanup
cd ..
rm -rf "$TEST_DIR"

echo ""
echo "${GREEN}🎉 All smoke tests passed!${NC}"
echo "✅ SRT parsing works"
echo "✅ SRT writing works" 
echo "✅ CLI entry point available"
echo "✅ Version information accessible"
echo ""
echo "🚀 SRT Translator is ready for basic operations"
