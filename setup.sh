#!/bin/sh

# Personal OS Setup Script
# Creates directories, copies templates, and guides you through goals creation
# Supports AI-assisted setup via --ai flag

set -e

# Resolve script's own directory before any cd
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors for output (portable via tput or ANSI)
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo ""
    echo "============================================================"
    echo "  $1"
    echo "============================================================"
    echo ""
}

print_success() {
    printf "${GREEN}✓${NC} %s\n" "$1"
}

print_info() {
    printf "${BLUE}ℹ${NC} %s\n" "$1"
}

print_warning() {
    printf "${YELLOW}!${NC} %s\n" "$1"
}

print_error() {
    printf "${RED}✗${NC} %s\n" "$1"
}

show_help() {
    cat << 'USAGE'
Usage: setup.sh [OPTIONS]

Personal OS setup — classic interactive or AI-assisted.

Options:
  --ai            Enable AI-assisted setup (skips classic questionnaire)
  --runtime LIST  Comma-separated runtimes to target (claude,cursor,cline,antigravity)
                  Default: all detected runtimes
  --dry-run       Preview what AI would generate without writing files
  --track         Keep generated files tracked in git (default: gitignored)
  --target PATH   Run setup against a different directory (default: current directory)
  --auto          Skip interactive approval (requires --runtime)
  --remove        Uninstall agentic-os generated files using manifest
  --help          Show this help message

Examples:
  ./setup.sh                                  Classic interactive setup
  ./setup.sh --ai                             AI-assisted setup for all runtimes
  ./setup.sh --ai --runtime claude            AI-assisted setup for Claude Code only
  ./setup.sh --ai --dry-run                   Preview AI proposals without writing
  ./setup.sh --ai --target ./my-project       Run against a different directory
  ./setup.sh --ai --auto --runtime claude     Unattended setup (no approval prompt)
  ./setup.sh --remove                         Clean uninstall of generated files
USAGE
}

# --- Flag Parsing ---

MODE="classic"
RUNTIMES=""
DRY_RUN=false
TRACK=false
AUTO=false
TARGET_DIR=""
VALID_RUNTIMES="claude cursor cline antigravity"

while [ $# -gt 0 ]; do
    case "$1" in
        --help)
            show_help
            exit 0
            ;;
        --ai)
            MODE="ai"
            shift
            ;;
        --runtime)
            if [ -z "$2" ] || [ "$(echo "$2" | cut -c1)" = "-" ]; then
                print_error "Error: --runtime requires a comma-separated list"
                echo "Valid runtimes: claude, cursor, cline, antigravity"
                exit 1
            fi
            RUNTIMES="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --track)
            TRACK=true
            shift
            ;;
        --target)
            if [ -z "$2" ] || [ "$(echo "$2" | cut -c1)" = "-" ]; then
                print_error "Error: --target requires a directory path"
                exit 1
            fi
            TARGET_DIR="$2"
            shift 2
            ;;
        --auto)
            AUTO=true
            shift
            ;;
        --remove)
            MODE="remove"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Run 'setup.sh --help' for usage information."
            exit 1
            ;;
    esac
done

# --- Validate --runtime values ---

validate_runtimes() {
    OLD_IFS="$IFS"
    IFS=','
    set -- $RUNTIMES
    IFS="$OLD_IFS"
    for rt in "$@"; do
        valid=false
        for vrt in $VALID_RUNTIMES; do
            if [ "$rt" = "$vrt" ]; then
                valid=true
                break
            fi
        done
        if [ "$valid" = "false" ]; then
            print_error "Invalid runtime: $rt"
            echo "Valid runtimes: claude, cursor, cline, antigravity"
            exit 1
        fi
    done
}

if [ -n "$RUNTIMES" ]; then
    validate_runtimes
fi

# --- Validate --auto requires --runtime ---

if [ "$AUTO" = "true" ] && [ -z "$RUNTIMES" ]; then
    print_error "Error: --auto requires explicit --runtime (cannot auto-detect in unattended mode)"
    echo "Example: setup.sh --ai --auto --runtime claude,cursor"
    exit 1
fi

# --- Resolve target directory ---

if [ -n "$TARGET_DIR" ]; then
    if [ ! -d "$TARGET_DIR" ]; then
        print_error "Error: target directory does not exist: $TARGET_DIR"
        exit 1
    fi
    cd "$TARGET_DIR"
    print_info "Target directory: $TARGET_DIR"
fi

# --- Remove Mode ---

handle_remove() {
    MANIFEST=".agents/.agentic-os-manifest.json"

    if ! command -v jq >/dev/null 2>&1; then
        print_error "Error: jq is required for --remove. Install:"
        echo "  macOS:  brew install jq"
        echo "  Linux:  apt install jq  (or yum install jq)"
        exit 2
    fi

    if [ ! -f "$MANIFEST" ]; then
        print_info "No agentic-os installation found (no manifest at $MANIFEST)"
        exit 0
    fi

    print_header "Removing Agentic-OS Generated Files"

    file_count=$(jq -r '.files | length' "$MANIFEST")
    i=0
    while [ "$i" -lt "$file_count" ]; do
        filepath=$(jq -r ".files[$i].path" "$MANIFEST")
        if [ -f "$filepath" ]; then
            rm "$filepath"
            print_success "Deleted: $filepath"
        else
            print_warning "Already missing: $filepath"
        fi
        i=$((i + 1))
    done

    # Remove gitignore managed block
    if [ -f ".gitignore" ]; then
        if grep -q "# === AGENTIC-OS GENERATED" ".gitignore"; then
            # Remove the managed block (between start and end markers inclusive)
            sed_tmp=".gitignore.tmp.$$"
            awk '/^# === AGENTIC-OS GENERATED/{skip=1; next} /^# === END AGENTIC-OS GENERATED/{skip=0; next} !skip' ".gitignore" > "$sed_tmp"
            mv "$sed_tmp" ".gitignore"
            print_success "Removed gitignore managed block"
        fi
    fi

    # Remove context bridge file
    if [ -f ".agents/.agentic-os-setup-context.json" ]; then
        rm ".agents/.agentic-os-setup-context.json"
        print_success "Deleted: .agents/.agentic-os-setup-context.json"
    fi

    # Remove manifest itself
    rm "$MANIFEST"
    print_success "Deleted: $MANIFEST"

    echo ""
    print_success "Agentic-OS uninstall complete. Your original files are untouched."
    exit 0
}

if [ "$MODE" = "remove" ]; then
    handle_remove
fi

# --- AI-Assisted Mode ---

handle_ai() {
    SKILL_DIR=".agents/skills/agentic-os-setup"
    SKILL_FILE_ABS="$SCRIPT_DIR/$SKILL_DIR/SKILL.md"
    CONTEXT_FILE=".agents/.agentic-os-setup-context.json"

    # Verify skill exists (ships in-tree with agentic-os, not in target dir)
    if [ ! -f "$SKILL_FILE_ABS" ]; then
        print_error "AI-installer skill not found at $SKILL_FILE_ABS"
        echo "This file should ship with agentic-os. Please check your installation."
        exit 1
    fi

    # Check jq availability (non-blocking for --ai, just warn)
    if ! command -v jq >/dev/null 2>&1; then
        print_warning "jq not found. Install jq for --remove support later:"
        echo "  macOS:  brew install jq"
        echo "  Linux:  apt install jq  (or yum install jq)"
    fi

    # --- Workspace Bootstrapping (copy infrastructure, never overwrite) ---
    print_header "Bootstrapping Workspace"

    # Directories
    for dir in "Tasks" "Knowledge"; do
        if [ -d "$dir" ]; then
            print_info "Directory exists: $dir/"
        else
            mkdir -p "$dir"
            print_success "Created: $dir/"
        fi
    done

    # BACKLOG.md
    if [ ! -f "BACKLOG.md" ]; then
        cat > "BACKLOG.md" << 'BACKLOGEOF'
# Backlog

Drop raw notes or todos here. Say `process my backlog` when you're ready for triage.
BACKLOGEOF
        print_success "Created: BACKLOG.md"
    else
        print_info "Exists: BACKLOG.md"
    fi

    # Workflows
    if [ ! -d "Workflows" ] && [ -d "$SCRIPT_DIR/Workflows" ]; then
        cp -r "$SCRIPT_DIR/Workflows" "Workflows"
        print_success "Copied: Workflows/"
    else
        print_info "Exists: Workflows/"
    fi

    # .agents/skills (all canonical skill packs)
    if [ ! -d ".agents/skills" ]; then
        mkdir -p ".agents"
        cp -r "$SCRIPT_DIR/.agents/skills" ".agents/skills"
        print_success "Copied: .agents/skills/ (all canonical skill packs)"
    else
        # Skills dir exists — ensure the setup skill is present
        if [ ! -d ".agents/skills/agentic-os-setup" ]; then
            cp -r "$SCRIPT_DIR/.agents/skills/agentic-os-setup" ".agents/skills/agentic-os-setup"
            print_success "Copied: .agents/skills/agentic-os-setup/"
        else
            print_info "Exists: .agents/skills/agentic-os-setup/"
        fi
    fi

    # Bridge: .claude/skills
    if [ ! -d ".claude" ]; then
        mkdir -p ".claude"
    fi
    if [ ! -e ".claude/skills" ]; then
        # No skills path at all — create symlink
        ln -sfn "../.agents/skills" ".claude/skills"
        print_success "Created symlink: .claude/skills -> ../.agents/skills"
    elif [ -L ".claude/skills" ]; then
        print_info "Exists: .claude/skills symlink"
    elif [ -d ".claude/skills" ]; then
        # .claude/skills is a real directory (not symlink) — ensure agentic-os-setup is there too
        if [ ! -d ".claude/skills/agentic-os-setup" ]; then
            cp -r "$SCRIPT_DIR/.agents/skills/agentic-os-setup" ".claude/skills/agentic-os-setup"
            print_success "Copied: .claude/skills/agentic-os-setup/ (bridge directory)"
        else
            print_info "Exists: .claude/skills/agentic-os-setup/"
        fi
    fi
    if [ ! -L "skills" ] && [ ! -e "skills" ]; then
        ln -s ".agents/skills" "skills"
        print_success "Created symlink: skills -> .agents/skills"
    else
        print_info "Exists: skills symlink"
    fi

    # .gitignore from template (never overwrite)
    if [ ! -f ".gitignore" ] && [ -f "$SCRIPT_DIR/System/templates/gitignore" ]; then
        cp "$SCRIPT_DIR/System/templates/gitignore" ".gitignore"
        print_success "Copied: .gitignore (from template)"
    else
        print_info "Exists: .gitignore (preserving your version)"
    fi

    # Ensure CLAUDE.md has skills reference (append if missing, never overwrite existing content)
    if [ -f "CLAUDE.md" ]; then
        if ! grep -q ".agents/skills" "CLAUDE.md"; then
            printf '\n## Skills\n\nCanonical skills are available at `.agents/skills/*/SKILL.md` (also accessible via `.claude/skills/`).\nTo run a skill: read its SKILL.md and follow the instructions within.\n' >> "CLAUDE.md"
            print_success "Appended skills reference to CLAUDE.md"
        else
            print_info "CLAUDE.md already references skills"
        fi
    else
        cat > "CLAUDE.md" << 'CLAUDEEOF'
@AGENTS.md

## Skills

Canonical skills are available at `.agents/skills/*/SKILL.md` (also accessible via `.claude/skills/`).
To run a skill: read its SKILL.md and follow the instructions within.
CLAUDEEOF
        print_success "Created: CLAUDE.md (with AGENTS.md reference + skills)"
    fi

    # --- End Bootstrap ---

    # Build runtime list for context bridge
    if [ -z "$RUNTIMES" ]; then
        runtime_json='["claude","cursor","cline","antigravity"]'
    else
        runtime_json="["
        first=true
        OLD_IFS="$IFS"
        IFS=','
        for rt in $RUNTIMES; do
            if [ "$first" = "true" ]; then
                runtime_json="${runtime_json}\"${rt}\""
                first=false
            else
                runtime_json="${runtime_json},\"${rt}\""
            fi
        done
        IFS="$OLD_IFS"
        runtime_json="${runtime_json}]"
    fi

    # Write context bridge file (skill is now local after bootstrap)
    mkdir -p "$(dirname "$CONTEXT_FILE")"
    cat > "$CONTEXT_FILE" << EOF
{
  "runtimes": ${runtime_json},
  "dry_run": ${DRY_RUN},
  "track": ${TRACK},
  "auto": ${AUTO}
}
EOF

    print_header "AI-Assisted Setup Ready"

    print_success "Workspace bootstrapped"
    print_success "Skill installed: .agents/skills/agentic-os-setup/SKILL.md"
    print_success "Context written: $CONTEXT_FILE"
    echo ""
    print_info "Runtimes: $(echo "$runtime_json" | tr -d '[]"')"
    [ "$DRY_RUN" = "true" ] && print_info "Mode: dry-run (no files will be written)"
    [ "$AUTO" = "true" ] && print_info "Mode: auto-approval (will write without interactive confirmation)"
    [ "$TRACK" = "true" ] && print_info "Track: generated files will be committed (not gitignored)"
    echo ""
    echo "Now invoke the AI-installer skill in your AI tool:"
    echo ""
    echo "  Claude Code:   /agentic-os-setup  (or say \"Run the agentic-os-setup skill\")"
    echo "  Cursor:        \"Run the agentic-os-setup skill\""
    echo "  Cline:         \"Run the agentic-os-setup skill\""
    echo "  Antigravity:   \"Run the agentic-os-setup skill\""
    echo ""
    print_info "Target repo: $(pwd)"
    print_info "The AI will scan your repo, infer GOALS.md, and generate runtime-specific configuration."
    exit 0
}

if [ "$MODE" = "ai" ]; then
    handle_ai
fi

# --- Classic Mode (unchanged behavior below this line) ---

ensure_symlink() {
    local target="$1"
    local link_path="$2"

    if [ -L "$link_path" ]; then
        ln -sfn "$target" "$link_path"
        print_success "Updated symlink: $link_path -> $target"
        return
    fi

    if [ -e "$link_path" ]; then
        print_warning "Skipped symlink (path exists and is not a symlink): $link_path"
        return
    fi

    ln -s "$target" "$link_path"
    print_success "Created symlink: $link_path -> $target"
}

ask_question() {
    local prompt="$1"
    local example="$2"
    local response=""

    echo "" >&2
    echo "$prompt" >&2
    if [ -n "$example" ]; then
        printf "${BLUE}%s${NC}\n" "$example" >&2
    fi
    read -r response
    echo "$response"
}

ask_multiline() {
    local prompt="$1"
    local response=""

    echo ""
    echo "$prompt"
    echo "(Type your answer, then press Ctrl+D when done)"
    echo ""
    response=$(cat)
    echo "$response"
}

# Start setup
clear
print_header "Welcome to Personal OS Setup"

echo "This setup will help you:"
echo "  1. Create your workspace structure"
echo "  2. Define your goals and priorities"
echo "  3. Configure your AI assistant"
echo ""
echo "Takes about 2 minutes. Be honest and specific."
echo ""
read -r -p "Press Enter to begin..."

# Create directories
print_header "Creating Workspace"

for dir in "Tasks" "Knowledge"; do
    if [ -d "$dir" ]; then
        print_info "Directory exists: $dir/"
    else
        mkdir -p "$dir"
        print_success "Created: $dir/"
    fi
done

# Validate canonical skills location
if [ -d ".agents/skills" ]; then
    print_success "Found canonical skills: .agents/skills/"
else
    print_warning "Missing .agents/skills/. Skills-based routing may not work until restored."
fi

# Create multi-agent bridge symlinks
if [ ! -d ".claude" ]; then
    mkdir -p ".claude"
    print_success "Created: .claude/"
fi

ensure_symlink "../.agents/skills" ".claude/skills"
ensure_symlink ".agents/skills" "skills"

# Copy template files
print_header "Setting Up Templates"

if [ ! -f ".gitignore" ] && [ -f "System/templates/gitignore" ]; then
    cp "System/templates/gitignore" ".gitignore"
    print_success "Copied: .gitignore"
else
    print_info "File exists: .gitignore (preserving your version)"
fi

# Create BACKLOG.md
if [ ! -f "BACKLOG.md" ]; then
    cat > "BACKLOG.md" << 'EOF'
# Backlog

Drop raw notes or todos here. Say `process my backlog` when you're ready for triage.
EOF
    print_success "Created: BACKLOG.md"
else
    print_info "File exists: BACKLOG.md"
fi

# Goals creation
print_header "Building Your Personal Goals"

echo "Now let's create your GOALS.md - the heart of your Personal OS."
echo ""
echo "I'll ask you about your goals and priorities."
echo "This helps your AI agent make smarter decisions about task priorities."
echo ""
echo "Be honest and specific - this is for you, not anyone else."
echo "You can always edit GOALS.md later to refine your thinking."
echo ""
read -r -p "Ready to dive in? Press Enter to start..."

# Collect answers (keeping it short - 5 essential questions)

# Section 1: Current Situation
print_header "1. Current Situation"

ans_role=$(ask_question \
    "What's your current role?" \
    "Product Manager, Senior Engineer, Founder, VP Product")

# Section 2: Vision
print_header "2. Your Vision"

ans_vision=$(ask_question \
    "What's your primary professional vision? What are you building toward?" \
    "Become VP Product, Launch a successful product, Build a thriving consultancy")

# Section 3: Success This Year
print_header "3. Success This Year"

ans_success_12mo=$(ask_question \
    "In 12 months, what would make you think 'this was a successful year'?" \
    "Shipped 3 major features, Built a team of 10, Became recognized expert in my field")

# Section 4: This Quarter
print_header "4. This Quarter"

ans_q1_goals=$(ask_question \
    "What are your objectives for THIS QUARTER (next 90 days)?" \
    "Launch new feature, Improve activation by 20%, Build PM practice")

# Section 5: Top Priorities
print_header "5. Top Priorities"

ans_top3=$(ask_question \
    "What are your top 3 priorities right now? (Be brutally honest)" \
    "1. Ship Q1 roadmap, 2. Build thought leadership, 3. Develop AI product skills")

# Set empty placeholders for sections user can fill in later
ans_company=""
ans_vision_why=""
ans_success_5yr=""
ans_current_focus=""
ans_q1_metrics=""
ans_skills=""
ans_relationships=""
ans_challenges=""
ans_opportunities=""

# Generate GOALS.md
print_header "Generating Your GOALS.md"

CURRENT_DATE=$(date +"%B %d, %Y")

cat > "GOALS.md" << EOF
# Goals & Strategic Direction

*Last updated: ${CURRENT_DATE}*

## Current Context

### What's your current role?
${ans_role}${ans_company:+ at }${ans_company}

### What's your primary professional vision? What are you building toward?
${ans_vision}

${ans_vision_why:+**Why this matters:**
${ans_vision_why}}

## Success Criteria

### In 12 months, what would make you think 'this was a successful year'?
${ans_success_12mo}

### What's your 5-year north star? Where do you want to be?
${ans_success_5yr}

## Ongoing

### What are you actively working on right now?
${ans_current_focus}

### What are your objectives for THIS QUARTER (next 90 days)?
${ans_q1_goals}

${ans_q1_metrics:+**How will you measure success on those quarterly objectives?**
${ans_q1_metrics}}

### What skills do you need to develop to achieve your vision?
${ans_skills}

### What key relationships or network do you need to build?
${ans_relationships}

## Strategic Context

### What's currently blocking you or slowing you down?
${ans_challenges}

### What opportunities are you exploring or considering?
${ans_opportunities}

## Priority Framework

When evaluating new tasks and commitments:

**P0 (Critical/Urgent)** - Must do THIS WEEK:
- Directly advances quarterly objectives
- Time-sensitive opportunities
- Critical stakeholder communication
- Immediate blockers to remove

**P1 (Important)** - This month:
- Builds key skills or expertise
- Advances product strategy
- Significant career development
- High-value learning opportunities

**P2 (Normal)** - Scheduled work:
- Supports broader objectives
- Maintains stakeholder relationships
- Operational efficiency
- General learning and exploration

**P3 (Low)** - Nice to have:
- Administrative tasks
- Speculative projects
- Activities without clear advancement value

## What are your top 3 priorities right now?

${ans_top3}

---

**Your AI assistant uses this document to prioritize tasks and suggest what to work on each day.**

*Review and update this weekly as your priorities shift.*

EOF

print_success "Created: GOALS.md"

# Final summary
print_header "Setup Complete!"

echo "Your Personal OS is ready to use."
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Review GOALS.md and refine as needed"
echo "2. Read AGENTS.md to understand how your AI agent works"
echo "3. Confirm bridge symlinks: .claude/skills and skills"
echo "4. Start adding tasks or notes to BACKLOG.md"
echo "5. Tell your AI: 'Read AGENTS.md and help me process my backlog'"
echo ""
echo "Want AI-powered setup? Run: setup.sh --ai"
echo ""
print_success "Happy organizing!"
echo ""
