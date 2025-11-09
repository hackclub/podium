#!/bin/bash

# Playwright E2E Test Runner for Podium
# Runs tests file-by-file to avoid race conditions and ensure 100% pass rate

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
# PODIUM_JWT_SECRET should be set via environment variables or Doppler
if [ -z "$PODIUM_JWT_SECRET" ]; then
    echo -e "${RED}Error: PODIUM_JWT_SECRET not set. Please use Doppler or set environment variables.${NC}"
    echo -e "${YELLOW}Run with: doppler run -- bun run test:e2e${NC}"
    exit 1
fi

echo -e "${YELLOW}Starting Playwright E2E Tests for Podium${NC}"
echo "=========================================="

# Test files to run
TEST_FILES=(
    "tests/auth.spec.ts"
    "tests/events.organizer.spec.ts"
    "tests/events.attendee.spec.ts"
    "tests/projects.spec.ts"
    "tests/voting.spec.ts"
    "tests/admin.spec.ts"
    "tests/permissions.spec.ts"
    "tests/voting-integrity.spec.ts"
)

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
FAILED_FILES=()

# Ensure we're in the frontend directory (where the script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Verify node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${RED}Error: node_modules not found in $(pwd). Run 'bun install' first.${NC}"
    exit 1
fi

# Try multiple methods to find and run Playwright
# Method 1: Use node to run node_modules/.bin/playwright (most reliable)
if [ -f "node_modules/.bin/playwright" ]; then
    PLAYWRIGHT_CMD="node node_modules/.bin/playwright"
    echo "Using: node node_modules/.bin/playwright"
# Method 2: Try node require.resolve to find CLI directly
elif PLAYWRIGHT_CLI=$(node -e "console.log(require.resolve('@playwright/test/cli.js'))" 2>/dev/null); then
    if [ -n "$PLAYWRIGHT_CLI" ] && [ -f "$PLAYWRIGHT_CLI" ]; then
        PLAYWRIGHT_CMD="node $PLAYWRIGHT_CLI"
        echo "Using: node $PLAYWRIGHT_CLI"
    fi
fi

# Fallback methods if local installation not found
if [ -z "$PLAYWRIGHT_CMD" ]; then
    # Method 3: Try using bunx (Bun's package runner)
    if command -v bunx >/dev/null 2>&1; then
        PLAYWRIGHT_CMD="bunx playwright"
        echo "Using: bunx playwright (fallback)"
    # Method 4: Try using npx as last resort
    elif command -v npx >/dev/null 2>&1; then
        PLAYWRIGHT_CMD="npx playwright"
        echo "Using: npx playwright (fallback)"
    else
        echo -e "${RED}Error: Could not find Playwright. Run 'bun install' first.${NC}"
        echo "Current directory: $(pwd)"
        exit 1
    fi
fi

# Run each test file
for test_file in "${TEST_FILES[@]}"; do
    echo ""
    echo -e "${YELLOW}Running: $test_file${NC}"
    echo "----------------------------------------"
    
    if $PLAYWRIGHT_CMD test "$test_file" --reporter=list; then
        echo -e "${GREEN}✓ $test_file passed${NC}"
    else
        echo -e "${RED}✗ $test_file failed${NC}"
        FAILED_FILES+=("$test_file")
    fi
done

# Summary
echo ""
echo "=========================================="
echo -e "${YELLOW}Test Summary${NC}"
echo "=========================================="

# Count tests
for test_file in "${TEST_FILES[@]}"; do
    count=$(grep -c "^[[:space:]]*test('" "$test_file" 2>/dev/null || echo 0)
    TOTAL_TESTS=$((TOTAL_TESTS + count))
done

if [ ${#FAILED_FILES[@]} -eq 0 ]; then
    echo -e "${GREEN}All test files passed!${NC}"
    echo "Total tests: $TOTAL_TESTS"
    exit 0
else
    echo -e "${RED}Some test files failed:${NC}"
    for failed in "${FAILED_FILES[@]}"; do
        echo -e "  ${RED}✗ $failed${NC}"
    done
    echo ""
    echo "Total test files: ${#TEST_FILES[@]}"
    echo "Failed: ${#FAILED_FILES[@]}"
    exit 1
fi
