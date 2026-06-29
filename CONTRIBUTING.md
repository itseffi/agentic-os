# Contributing to Agentic-OS

Thank you for your interest in contributing! This guide covers how to add features, fix bugs, and extend the AI-installer skill system.

## License

This project is licensed under [CC BY-NC-SA 4.0](LICENSE). By contributing, you agree that your contributions will be licensed under the same terms.

## Development Workflow

1. **Fork** the repository
2. **Create a feature branch** from `main`
3. **Make your changes** following the patterns below
4. **Test manually** across at least one AI runtime (see Testing section)
5. **Submit a PR** with a clear description of what changed and why

## Project Structure

```
agentic-os/
├── setup.sh                         # Entry point — shell bootstrap
├── .agents/
│   └── skills/
│       ├── <existing-skills>/       # 47 canonical skills
│       └── agentic-os-setup/        # AI-installer skill (this feature)
│           ├── SKILL.md             # Orchestrator — AI reads this first
│           ├── catalog.md           # Signal catalog (known repo patterns)
│           ├── agents/openai.yaml   # Agent Skills open standard metadata
│           ├── templates/           # Rule templates the AI fills
│           ├── adapters/            # Per-runtime output formatting
│           └── examples/            # Calibration examples
├── examples/                        # Test repo fixtures (UJ-1 through UJ-4)
│   ├── uj-1-node-monorepo/          # Node.js monorepo with Cursor rules
│   ├── uj-2-architect-monorepo/     # Complex multi-concern with BMAD
│   ├── uj-3-flask-simple/           # Simple Flask project
│   └── uj-4-rust-antigravity/       # Rust workspace with AGENTS.md
├── tests/                           # Automated test suite
│   ├── test_setup.sh               # Shell tests (flag parsing, routing)
│   ├── test_content.py             # Python tests (content validation)
│   └── results/                    # Test output (gitignored)
├── Workflows/                       # Daily and strategic workflows
├── Tutorials/                       # Learning guides
├── Evals/                           # Validation scripts and fixtures
└── System/                          # MCP server, integrations, templates
```

## How to Contribute

### Adding a Signal to the Catalog

Signals are filesystem patterns that indicate something about a repo's structure. To add one:

1. Edit `.agents/skills/agentic-os-setup/catalog.md`
2. Add an entry following this format:

```markdown
## Signal: <pattern>

**Pattern:** <what to look for on the filesystem>
**Indicates:** <what it means about the repo>
**Complexity impact:** <+1 tier signal, neutral, or -1>
**Setup implications:**
- <what the AI should do differently when this is detected>
**Coexistence:** <how agentic-os should behave alongside this>
```

3. Test: invoke the AI-installer on a repo containing this pattern and verify it's detected

### Adding a Rule Template

Rule templates define output patterns the AI fills with detected values. To add one:

1. Create a new file in `.agents/skills/agentic-os-setup/templates/`
2. Follow this structure:

```markdown
# Template: <Rule Type Name>

## Intent
<One sentence: what behavior this rule enforces>

## Inputs Required
- {variable}: <what the AI needs to detect to fill this>

## Output Pattern (Cursor .mdc)
<Example output for Cursor>

## Output Pattern (CLAUDE.md section)
<Example output for Claude Code>

## Output Pattern (AGENTS.md section)
<Example output for Antigravity>

## When to Use
- Complexity tier: <which tiers this applies to>
- Detected: <what signals must be present>
- NOT when: <conditions that exclude this template>
```

3. Test: verify the AI generates correct output from this template for each runtime

### Adding a Runtime Adapter

Adapters teach the AI how to format output for a specific tool. To add one:

1. Create a new file in `.agents/skills/agentic-os-setup/adapters/`
2. Include:
   - File path convention (where output goes for this runtime)
   - Format specification (what valid output looks like)
   - Constraints (what this runtime can/cannot express)
   - Merge behavior (create new file vs extend existing)
   - Examples (2-3 concrete output samples)

3. Update `setup.sh` to accept the new runtime name in `--runtime` validation
4. Test: run the AI-installer targeting only this runtime on a sample repo

### Modifying setup.sh

The shell script handles bootstrapping and teardown. It:
- Parses flags (`--ai`, `--runtime`, `--dry-run`, `--track`, `--target`, `--auto`, `--remove`, `--help`)
- Bootstraps workspace infrastructure into the target (dirs, BACKLOG.md, Workflows/, skills, symlinks, .gitignore, CLAUDE.md skills reference)
- Writes the context bridge file (`.agents/.agentic-os-setup-context.json`)
- Prints invocation instructions (`/agentic-os-setup` for Claude Code, or "Run the agentic-os-setup skill" for others)
- Handles clean uninstall (reading manifest, deleting tracked files)

Rules:
- POSIX sh compatible (no bashisms)
- No external dependencies beyond git, jq (for --remove), and standard Unix utilities
- Never add AI logic to the script — that belongs in SKILL.md

### Modifying SKILL.md

The orchestrator is the most sensitive file. Changes should:
- Maintain the section order (mode detection → scan → classify → propose → approve → write)
- Not break any of the 4 supported runtimes
- Preserve the non-destructive file policy (never modify user files)
- Keep the approval gate (never write without human confirmation)

## Testing

### Automated Tests

The project includes two automated test layers:

```bash
# Shell tests — validates setup.sh flag parsing, routing, and remove logic
sh tests/test_setup.sh

# Python tests — validates content structure (manifest schema, .mdc frontmatter, markers)
pytest tests/test_content.py
```

Test results are written to `tests/results/` (gitignored):
- Shell: `tests/results/shell/report.txt` (plaintext pass/fail summary)
- Python: `tests/results/python/report.xml` (JUnit XML, configured in `pytest.ini`) + `tests/results/python/report.txt` (plaintext, generated by `tests/conftest.py`)

The shell tests require only `sh`, `jq`, and standard POSIX tools. The Python tests require `pytest` and `pyyaml`.

### Test Fixtures

The `examples/` directory contains real repo structures for each user journey:
- `uj-1-node-monorepo/` — Node.js monorepo with 3 existing Cursor rules
- `uj-2-architect-monorepo/` — Complex multi-concern with BMAD, 10 Cursor rules, existing AGENTS.md
- `uj-3-flask-simple/` — Simple Flask project with no AI config
- `uj-4-rust-antigravity/` — Rust workspace with existing AGENTS.md

Use these with `--target` to test setup.sh against specific scenarios. The script bootstraps workspace infrastructure and the skill into the target, then you invoke it locally:
```bash
./setup.sh --ai --target examples/uj-3-flask-simple --runtime claude
# Then open the target in your AI tool: /agentic-os-setup (Claude Code) or "Run the agentic-os-setup skill"
```

### Manual Testing Protocol

AI behavior is non-deterministic, so the AI-installer skill also requires manual validation:

1. **Run setup** against a fixture or real repo: `./setup.sh --ai --runtime <target>`
2. **Invoke the skill** in your AI runtime of choice
3. **Verify:**
   - Correct complexity tier detected
   - Appropriate output proposed (not over/under-generating)
   - Dry-run shows accurate diffs
   - No conflicts with existing configs
   - Generated files are valid for their target runtime
   - `setup.sh --remove` cleanly removes everything
4. **Test coexistence** (if applicable):
   - Existing .cursor/rules/ are untouched
   - Existing AGENTS.md is extended, not replaced
   - _bmad/ detection triggers persona deferral

### Evals

For changes to canonical skills (not the AI-installer), run the existing eval suite:

```bash
python scripts/validate_skills.py
python scripts/run_skill_evals.py --provider fixture
python scripts/run_routing_evals.py
```

## What Makes a Good PR

- **Atomic:** One concern per PR (a signal, a template, an adapter — not all at once)
- **Tested:** Evidence that you ran the manual testing protocol
- **Documented:** If you add a signal, template, or adapter, the PR description shows example input → output
- **Non-breaking:** Classic `setup.sh` (no flags) behavior is unchanged
- **No secrets:** Generated configs can expose repo structure — never include real project data in examples

## Code of Conduct

Be respectful, constructive, and collaborative. This is a community project — treat others as you'd want to be treated. Harassment, discrimination, and toxic behavior will not be tolerated.

## Questions?

Open an issue with the `question` label if you're unsure about an approach before investing time in a PR.
