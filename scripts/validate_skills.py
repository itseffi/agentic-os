#!/usr/bin/env python3
"""Validate canonical skill-pack structure and repository guardrails."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / ".agents" / "skills"

if not SKILLS_DIR.exists():
    print("ERROR: missing .agents/skills directory")
    sys.exit(1)

errors = []
checked = 0
for skill_dir in sorted([p for p in SKILLS_DIR.iterdir() if p.is_dir()]):
    skill_name = skill_dir.name
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        errors.append(f"{skill_dir}: missing SKILL.md")
        continue

    checked += 1
    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---"):
        errors.append(f"{skill_file}: missing YAML frontmatter")
        continue

    fm = text.split("---", 2)
    if len(fm) < 3:
        errors.append(f"{skill_file}: malformed frontmatter")
        continue

    frontmatter = fm[1]
    body = fm[2].strip()

    name_match = re.search(r"^name:\s*(.+)", frontmatter, re.MULTILINE)
    if not name_match:
        errors.append(f"{skill_file}: missing frontmatter field 'name'")
        skill_declared_name = None
    else:
        skill_declared_name = name_match.group(1).strip()
        if skill_declared_name != skill_name:
            errors.append(
                f"{skill_file}: frontmatter name '{skill_declared_name}' must match folder '{skill_name}'"
            )
    if not re.search(r"^description:\s*.+", frontmatter, re.MULTILINE):
        errors.append(f"{skill_file}: missing frontmatter field 'description'")

    has_process_marker = any(
        marker in body
        for marker in [
            "## The Process",
            "## Instructions",
            "### Step 1",
            "### Phase 1",
            "1. ",
            "## Red-Green-Refactor",
            "## Task Structure",
        ]
    )
    if not has_process_marker:
        errors.append(f"{skill_file}: missing clear process/instructions section")

    if "## When to Use" not in body:
        errors.append(f"{skill_file}: missing '## When to Use' section")
    if "## When Not to Use" not in body:
        errors.append(f"{skill_file}: missing '## When Not to Use' section")

    openai_yaml = skill_dir / "agents" / "openai.yaml"
    if not openai_yaml.exists():
        errors.append(f"{skill_dir}: missing agents/openai.yaml")
    else:
        raw = openai_yaml.read_text(encoding="utf-8")
        name_cfg = re.search(r"^name:\s*(.+)$", raw, re.MULTILINE)
        desc_cfg = re.search(r"^description:\s*(.+)$", raw, re.MULTILINE)
        version_cfg = re.search(r"^version:\s*(.+)$", raw, re.MULTILINE)
        trigger_cfg = re.search(r"^\s*trigger:\s*(.+)$", raw, re.MULTILINE)

        if not name_cfg:
            errors.append(f"{openai_yaml}: missing 'name'")
            name_value = None
        else:
            name_value = name_cfg.group(1).strip()

        if name_value != skill_name:
            errors.append(f"{openai_yaml}: name must match folder '{skill_name}'")
        if not desc_cfg:
            errors.append(f"{openai_yaml}: missing 'description'")
        if not version_cfg or version_cfg.group(1).strip() != "1":
            errors.append(f"{openai_yaml}: version must be 1")
        if "invocation:" not in raw:
            errors.append(f"{openai_yaml}: missing 'invocation' object")
        elif not trigger_cfg or trigger_cfg.group(1).strip() not in {"implicit", "explicit"}:
            errors.append(f"{openai_yaml}: invocation.trigger must be implicit or explicit")

# Validate docs for stale paths if this repo remains single-source skills.
for md in ROOT.rglob("*.md"):
    rel = md.relative_to(ROOT)
    text = md.read_text(encoding="utf-8", errors="ignore")
    if "Skills/" in text:
        errors.append(f"{rel}: contains stale 'Skills/' path")
    if "scripts/sync_skills.sh" in text:
        errors.append(f"{rel}: contains stale sync_skills.sh reference")
    if ".claude/skills/" in text and rel != Path("System/integrations/granola/SETUP_SKILL.md"):
        errors.append(f"{rel}: contains direct .claude/skills path")

# The shipped GOALS.md and the one setup.sh writes must stay one format. They diverged into
# two documents sharing a single heading, so a user who filled in the template and then ran
# setup got a file organised on entirely different lines.
goals_md = ROOT / "GOALS.md"
setup_sh = ROOT / "setup.sh"
if goals_md.exists() and setup_sh.exists():
    generated = setup_sh.read_text(encoding="utf-8")
    if 'cat > "GOALS.md" << EOF' in generated:
        template = generated.split('cat > "GOALS.md" << EOF\n', 1)[1].split("\nEOF\n", 1)[0]
        want = [l.strip() for l in template.splitlines() if l.startswith("#")]
        have = [l.strip() for l in goals_md.read_text(encoding="utf-8").splitlines()
                if l.startswith("#")]
        if want != have:
            errors.append(
                "GOALS.md headings differ from the template setup.sh writes; "
                f"{len(set(want) ^ set(have))} heading(s) differ"
            )

if errors:
    print(f"FAIL: checked {checked} skill(s), found {len(errors)} issue(s)")
    for err in errors:
        print(f"- {err}")
    sys.exit(1)

print(f"PASS: checked {checked} skill(s)")
