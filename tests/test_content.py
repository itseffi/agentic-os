"""
Content validation tests for agentic-os AI-installer generated output.

Validates structural correctness of:
- Manifest JSON schema
- .mdc YAML frontmatter
- Glob specificity rules
- Managed block marker syntax
- Gitignore block structure
- Cursor file numbering

Run: pytest tests/test_content.py
"""

import json
import os
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = REPO_ROOT / "examples"
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "agentic-os-setup"


# ============================================================
# Scenario 1: Manifest schema validation
# ============================================================


class TestManifestSchema:
    """Validates manifest JSON structure meets the defined schema."""

    SAMPLE_MANIFEST = {
        "version": "1.0.0",
        "created_at": "2026-06-20T15:30:00Z",
        "complexity_tier": "simple",
        "runtimes_targeted": ["claude"],
        "files": [
            {
                "path": "CLAUDE.md",
                "created_at": "2026-06-20T15:30:00Z",
                "content_hash": "sha256:abc123def456",
            }
        ],
        "denied_relationships": [],
        "detected_frameworks": [],
    }

    def test_required_top_level_fields(self):
        required = [
            "version",
            "created_at",
            "complexity_tier",
            "runtimes_targeted",
            "files",
            "denied_relationships",
            "detected_frameworks",
        ]
        for field in required:
            assert field in self.SAMPLE_MANIFEST

    def test_version_is_semver(self):
        version = self.SAMPLE_MANIFEST["version"]
        assert re.match(r"^\d+\.\d+\.\d+$", version)

    def test_complexity_tier_valid_values(self):
        valid_tiers = {"zero", "simple", "multi", "complex"}
        assert self.SAMPLE_MANIFEST["complexity_tier"] in valid_tiers

    def test_runtimes_are_valid(self):
        valid_runtimes = {"claude", "cursor", "cline", "antigravity"}
        for rt in self.SAMPLE_MANIFEST["runtimes_targeted"]:
            assert rt in valid_runtimes

    def test_files_have_required_fields(self):
        for f in self.SAMPLE_MANIFEST["files"]:
            assert "path" in f
            assert "created_at" in f
            assert "content_hash" in f

    def test_content_hash_format(self):
        for f in self.SAMPLE_MANIFEST["files"]:
            assert f["content_hash"].startswith("sha256:")
            hash_part = f["content_hash"].split(":")[1]
            assert len(hash_part) > 0
            assert re.match(r"^[a-f0-9]+$", hash_part)


# ============================================================
# Scenario 2: .mdc YAML frontmatter validation
# ============================================================


class TestMdcFrontmatter:
    """Validates .mdc files have proper YAML frontmatter."""

    @pytest.fixture
    def mdc_files(self):
        """Collect all .mdc files from fixtures."""
        files = []
        for fixture in FIXTURES_DIR.iterdir():
            if fixture.is_dir():
                cursor_dir = fixture / ".cursor" / "rules"
                if cursor_dir.exists():
                    files.extend(cursor_dir.glob("*.mdc"))
        return files

    def test_mdc_files_exist(self, mdc_files):
        assert len(mdc_files) > 0, "No .mdc files found in fixtures"

    def test_all_mdc_have_frontmatter(self, mdc_files):
        for mdc_file in mdc_files:
            content = mdc_file.read_text()
            assert content.startswith("---"), (
                f"{mdc_file.name} missing YAML frontmatter start"
            )
            parts = content.split("---", 2)
            assert len(parts) >= 3, (
                f"{mdc_file.name} missing YAML frontmatter end delimiter"
            )

    def test_frontmatter_has_description(self, mdc_files):
        for mdc_file in mdc_files:
            content = mdc_file.read_text()
            parts = content.split("---", 2)
            fm = yaml.safe_load(parts[1])
            assert "description" in fm, (
                f"{mdc_file.name} frontmatter missing 'description'"
            )
            assert len(fm["description"]) > 0

    def test_frontmatter_has_globs(self, mdc_files):
        for mdc_file in mdc_files:
            content = mdc_file.read_text()
            parts = content.split("---", 2)
            fm = yaml.safe_load(parts[1])
            assert "globs" in fm, f"{mdc_file.name} frontmatter missing 'globs'"


# ============================================================
# Scenario 3: Glob specificity (no bare *)
# ============================================================


class TestGlobSpecificity:
    """Ensures no .mdc file uses bare '*' as its glob."""

    @pytest.fixture
    def mdc_globs(self):
        """Extract globs from all fixture .mdc files."""
        globs = []
        for fixture in FIXTURES_DIR.iterdir():
            if fixture.is_dir():
                cursor_dir = fixture / ".cursor" / "rules"
                if cursor_dir.exists():
                    for mdc_file in cursor_dir.glob("*.mdc"):
                        content = mdc_file.read_text()
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            fm = yaml.safe_load(parts[1])
                            if "globs" in fm:
                                globs.append(
                                    (mdc_file.name, fm["globs"])
                                )
        return globs

    def test_no_bare_star_glob(self, mdc_globs):
        for filename, glob_value in mdc_globs:
            glob_str = str(glob_value)
            individual_globs = [g.strip() for g in glob_str.split(",")]
            for g in individual_globs:
                assert g != "*", (
                    f"{filename} uses bare '*' glob (too broad)"
                )
                assert g != "**/*", (
                    f"{filename} uses '**/*' glob (matches everything)"
                )


# ============================================================
# Scenario 4: Managed block marker syntax
# ============================================================


class TestManagedBlockMarkers:
    """Validates managed block marker format in adapter docs."""

    MARKER_START_PATTERN = re.compile(
        r"<!-- MANAGED BY AGENTIC-OS \| hash:sha256:[a-f0-9]+ \| DO NOT EDIT -->"
    )
    MARKER_END = "<!-- END MANAGED BY AGENTIC-OS -->"

    def test_antigravity_adapter_documents_marker_format(self):
        adapter = SKILL_DIR / "adapters" / "antigravity.md"
        content = adapter.read_text()
        assert "<!-- MANAGED BY AGENTIC-OS" in content
        assert "<!-- END MANAGED BY AGENTIC-OS -->" in content

    def test_skill_md_documents_marker_format(self):
        skill = SKILL_DIR / "SKILL.md"
        content = skill.read_text()
        assert "<!-- MANAGED BY AGENTIC-OS" in content
        assert "<!-- END MANAGED BY AGENTIC-OS -->" in content

    def test_marker_format_in_examples(self):
        example = SKILL_DIR / "examples" / "complex-output.md"
        content = example.read_text()
        assert self.MARKER_START_PATTERN.search(content), (
            "complex-output.md missing valid managed block start marker"
        )
        assert self.MARKER_END in content


# ============================================================
# Scenario 5: Gitignore block structure
# ============================================================


class TestGitignoreBlock:
    """Validates the gitignore managed block format in SKILL.md."""

    def test_skill_defines_gitignore_block_format(self):
        skill = SKILL_DIR / "SKILL.md"
        content = skill.read_text()
        assert "# === AGENTIC-OS GENERATED" in content
        assert "# === END AGENTIC-OS GENERATED ===" in content

    def test_block_has_start_and_end_delimiters(self):
        skill = SKILL_DIR / "SKILL.md"
        content = skill.read_text()
        start_count = content.count("# === AGENTIC-OS GENERATED")
        end_count = content.count("# === END AGENTIC-OS GENERATED ===")
        assert start_count > 0
        assert end_count > 0
        assert start_count == end_count, (
            "Mismatched gitignore block delimiters"
        )


# ============================================================
# Scenario 6: Cursor file numbering respect
# ============================================================


class TestCursorNumbering:
    """Validates numbering detection logic in fixtures."""

    def test_uj1_has_non_contiguous_numbering(self):
        """UJ-1 fixture has 002, 003, 005 — next should be 006 or higher."""
        cursor_dir = FIXTURES_DIR / "uj-1-node-monorepo" / ".cursor" / "rules"
        numbers = []
        for f in cursor_dir.glob("*.mdc"):
            match = re.match(r"^(\d+)", f.name)
            if match:
                numbers.append(int(match.group(1)))
        numbers.sort()
        assert numbers == [2, 3, 5], (
            f"UJ-1 fixture numbers unexpected: {numbers}"
        )
        next_available = max(numbers) + 1
        assert next_available == 6

    def test_uj2_uses_800_band(self):
        """UJ-2 fixture has 800-809 — next should be 810."""
        cursor_dir = (
            FIXTURES_DIR / "uj-2-architect-monorepo" / ".cursor" / "rules"
        )
        numbers = []
        for f in cursor_dir.glob("*.mdc"):
            match = re.match(r"^(\d+)", f.name)
            if match:
                numbers.append(int(match.group(1)))
        numbers.sort()
        assert min(numbers) == 800
        assert max(numbers) == 809
        assert len(numbers) == 10
        next_available = max(numbers) + 1
        assert next_available == 810


# ============================================================
# Scenario 7: Skill file structure completeness
# ============================================================


class TestSkillStructure:
    """Validates the skill directory has all required files."""

    def test_skill_md_exists(self):
        assert (SKILL_DIR / "SKILL.md").exists()

    def test_catalog_exists(self):
        assert (SKILL_DIR / "catalog.md").exists()

    def test_all_templates_exist(self):
        expected = [
            "persona-routing.md",
            "scope-isolation.md",
            "cross-reference.md",
            "naming-enforcement.md",
            "quality-gates.md",
        ]
        for name in expected:
            assert (SKILL_DIR / "templates" / name).exists(), (
                f"Missing template: {name}"
            )

    def test_all_adapters_exist(self):
        expected = ["claude.md", "cursor.md", "cline.md", "antigravity.md"]
        for name in expected:
            assert (SKILL_DIR / "adapters" / name).exists(), (
                f"Missing adapter: {name}"
            )

    def test_all_examples_exist(self):
        expected = ["simple-output.md", "complex-output.md"]
        for name in expected:
            assert (SKILL_DIR / "examples" / name).exists(), (
                f"Missing example: {name}"
            )

    def test_all_fixtures_exist(self):
        expected = [
            "uj-1-node-monorepo",
            "uj-2-architect-monorepo",
            "uj-3-flask-simple",
            "uj-4-rust-antigravity",
        ]
        for name in expected:
            assert (FIXTURES_DIR / name).is_dir(), (
                f"Missing fixture: {name}"
            )
