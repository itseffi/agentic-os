#!/bin/sh
# Shell test runner for setup.sh flag parsing and mode routing.
# Runs against the test fixtures in examples/.
# Results written to tests/results/shell/

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SETUP="$REPO_ROOT/setup.sh"
RESULTS="$SCRIPT_DIR/results/shell"

# Counters
PASS=0
FAIL=0
TOTAL=0

mkdir -p "$RESULTS"

# --- Test Helpers ---

assert_exit() {
    test_name="$1"
    expected_exit="$2"
    shift 2
    TOTAL=$((TOTAL + 1))

    actual_output=$("$@" 2>&1) || true
    # Re-run to capture exit code
    set +e
    "$@" > /dev/null 2>&1
    actual_exit=$?
    set -e

    if [ "$actual_exit" -eq "$expected_exit" ]; then
        PASS=$((PASS + 1))
        printf "  PASS: %s\n" "$test_name"
    else
        FAIL=$((FAIL + 1))
        printf "  FAIL: %s (expected exit %d, got %d)\n" "$test_name" "$expected_exit" "$actual_exit"
        printf "    Output: %s\n" "$actual_output" >> "$RESULTS/failures.log"
    fi
}

assert_output_contains() {
    test_name="$1"
    pattern="$2"
    shift 2
    TOTAL=$((TOTAL + 1))

    actual_output=$("$@" 2>&1) || true

    if echo "$actual_output" | grep -qF -- "$pattern"; then
        PASS=$((PASS + 1))
        printf "  PASS: %s\n" "$test_name"
    else
        FAIL=$((FAIL + 1))
        printf "  FAIL: %s (output missing: %s)\n" "$test_name" "$pattern"
        printf "    Full output: %s\n" "$actual_output" >> "$RESULTS/failures.log"
    fi
}

assert_file_exists() {
    test_name="$1"
    filepath="$2"
    TOTAL=$((TOTAL + 1))

    if [ -f "$filepath" ]; then
        PASS=$((PASS + 1))
        printf "  PASS: %s\n" "$test_name"
    else
        FAIL=$((FAIL + 1))
        printf "  FAIL: %s (file not found: %s)\n" "$test_name" "$filepath"
    fi
}

assert_file_not_exists() {
    test_name="$1"
    filepath="$2"
    TOTAL=$((TOTAL + 1))

    if [ ! -f "$filepath" ]; then
        PASS=$((PASS + 1))
        printf "  PASS: %s\n" "$test_name"
    else
        FAIL=$((FAIL + 1))
        printf "  FAIL: %s (file should not exist: %s)\n" "$test_name" "$filepath"
    fi
}

# --- Clean state ---

rm -f "$RESULTS/failures.log"
printf "Shell Test Runner — %s\n\n" "$(date)"

# ============================================================
# Test Suite 1: --help
# ============================================================

printf "Suite 1: --help\n"

assert_exit "help exits 0" 0 sh "$SETUP" --help
assert_output_contains "help shows --ai" "--ai" sh "$SETUP" --help
assert_output_contains "help shows --runtime" "--runtime" sh "$SETUP" --help
assert_output_contains "help shows --target" "--target" sh "$SETUP" --help
assert_output_contains "help shows --auto" "--auto" sh "$SETUP" --help
assert_output_contains "help shows --remove" "--remove" sh "$SETUP" --help

echo ""

# ============================================================
# Test Suite 2: --ai routing
# ============================================================

printf "Suite 2: --ai routing\n"

assert_exit "ai mode succeeds with skill present" 0 sh "$SETUP" --ai --runtime claude
assert_output_contains "ai prints skill installed" "Skill installed" sh "$SETUP" --ai --runtime claude
assert_output_contains "ai prints context written" "Context written" sh "$SETUP" --ai --runtime claude

# Clean up context file
rm -f "$REPO_ROOT/.agents/.agentic-os-setup-context.json"

echo ""

# ============================================================
# Test Suite 3: --runtime validation
# ============================================================

printf "Suite 3: --runtime validation\n"

assert_exit "valid runtime claude" 0 sh "$SETUP" --ai --runtime claude
rm -f "$REPO_ROOT/.agents/.agentic-os-setup-context.json"

assert_exit "valid runtime multi" 0 sh "$SETUP" --ai --runtime claude,cursor,cline,antigravity
rm -f "$REPO_ROOT/.agents/.agentic-os-setup-context.json"

assert_exit "invalid runtime errors" 1 sh "$SETUP" --ai --runtime invalid
assert_exit "partial invalid errors" 1 sh "$SETUP" --ai --runtime claude,bad
assert_output_contains "invalid shows valid list" "Valid runtimes" sh "$SETUP" --ai --runtime bad

echo ""

# ============================================================
# Test Suite 4: --remove
# ============================================================

printf "Suite 4: --remove\n"

assert_exit "remove with no manifest exits 0" 0 sh "$SETUP" --remove
assert_output_contains "remove says no installation" "No agentic-os installation" sh "$SETUP" --remove

# Test remove with a manifest
FIXTURE_DIR="$RESULTS/remove-test"
mkdir -p "$FIXTURE_DIR/.agents"
echo "test content" > "$FIXTURE_DIR/test-file.md"
printf '{"files":[{"path":"test-file.md","created_at":"2026-01-01","content_hash":"sha256:abc"}]}' > "$FIXTURE_DIR/.agents/.agentic-os-manifest.json"

sh "$SETUP" --remove --target "$FIXTURE_DIR" > /dev/null 2>&1
assert_file_not_exists "remove deletes tracked file" "$FIXTURE_DIR/test-file.md"
assert_file_not_exists "remove deletes manifest" "$FIXTURE_DIR/.agents/.agentic-os-manifest.json"

rm -rf "$FIXTURE_DIR"

echo ""

# ============================================================
# Test Suite 5: --target
# ============================================================

printf "Suite 5: --target\n"

assert_exit "target with valid dir" 0 sh "$SETUP" --ai --runtime claude --target "$REPO_ROOT/examples/uj-3-flask-simple"
rm -f "$REPO_ROOT/examples/uj-3-flask-simple/.agents/.agentic-os-setup-context.json"
rmdir "$REPO_ROOT/examples/uj-3-flask-simple/.agents" 2>/dev/null || true

assert_exit "target with invalid dir errors" 1 sh "$SETUP" --ai --target /nonexistent
assert_output_contains "target error message" "does not exist" sh "$SETUP" --ai --target /nonexistent

echo ""

# ============================================================
# Test Suite 6: --auto
# ============================================================

printf "Suite 6: --auto\n"

assert_exit "auto without runtime errors" 1 sh "$SETUP" --ai --auto
assert_output_contains "auto error says requires runtime" "requires explicit --runtime" sh "$SETUP" --ai --auto

assert_exit "auto with runtime succeeds" 0 sh "$SETUP" --ai --auto --runtime claude
rm -f "$REPO_ROOT/.agents/.agentic-os-setup-context.json"

# Verify context bridge has auto: true
sh "$SETUP" --ai --auto --runtime claude > /dev/null 2>&1
if grep -q '"auto": true' "$REPO_ROOT/.agents/.agentic-os-setup-context.json"; then
    PASS=$((PASS + 1))
    TOTAL=$((TOTAL + 1))
    printf "  PASS: context bridge contains auto: true\n"
else
    FAIL=$((FAIL + 1))
    TOTAL=$((TOTAL + 1))
    printf "  FAIL: context bridge missing auto: true\n"
fi
rm -f "$REPO_ROOT/.agents/.agentic-os-setup-context.json"

echo ""

# ============================================================
# Test Suite 7: Flag combinations
# ============================================================

printf "Suite 7: Flag combinations\n"

assert_exit "ai + dry-run + runtime" 0 sh "$SETUP" --ai --dry-run --runtime claude
rm -f "$REPO_ROOT/.agents/.agentic-os-setup-context.json"

assert_exit "ai + auto + runtime + target" 0 sh "$SETUP" --ai --auto --runtime cursor --target "$REPO_ROOT/examples/uj-1-node-monorepo"
rm -f "$REPO_ROOT/examples/uj-1-node-monorepo/.agents/.agentic-os-setup-context.json"
rmdir "$REPO_ROOT/examples/uj-1-node-monorepo/.agents" 2>/dev/null || true

assert_exit "ai + auto + runtime + dry-run" 0 sh "$SETUP" --ai --auto --runtime claude --dry-run
rm -f "$REPO_ROOT/.agents/.agentic-os-setup-context.json"

assert_exit "unknown flag errors" 1 sh "$SETUP" --bogus

echo ""

# ============================================================
# Summary
# ============================================================

printf "============================================================\n"
printf "Results: %d/%d passed" "$PASS" "$TOTAL"
if [ "$FAIL" -gt 0 ]; then
    printf " (%d FAILED)\n" "$FAIL"
    printf "See: %s/failures.log\n" "$RESULTS"
    # Write summary report
    printf "FAIL: %d/%d passed (%d failed) — %s\n" "$PASS" "$TOTAL" "$FAIL" "$(date)" > "$RESULTS/report.txt"
    exit 1
else
    printf " (all passed)\n"
    # Write summary report
    printf "PASS: %d/%d passed — %s\n" "$PASS" "$TOTAL" "$(date)" > "$RESULTS/report.txt"
    exit 0
fi
