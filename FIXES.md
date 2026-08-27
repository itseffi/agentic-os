# Fix notes

Status: items 3, 8, 9, 10, 11, 15, 16, 17 and 18 are applied. The rest are documented only. Findings from an audit of
`System/mcp/server.py`, `scripts/`, and `setup.sh`. Each fix below was checked against the
real code path before being written down.

Open question: items 12, 13 and 14 are design calls, not mechanical fixes. They need a
decision before anyone patches them.

## 1. create_task overwrites existing tasks

`create_task` writes to a slug derived from the title with no existence check. Calling it
with a title that already has a task file replaces that file with a blank template and
reports success.

`System/mcp/server.py:570` builds the path, `System/mcp/server.py:589` writes it:

```python
filename = to_slug_filename(title)
filepath = TASKS_DIR / filename
...
with open(filepath, 'w') as f:
    f.write(file_content)
```

Nothing between those lines checks whether `filepath` exists.

### What it costs

A task in progress, then one duplicate `create_task` call with the same title:

| Field | Before | After |
|-------|--------|-------|
| `priority` | P0 | P2 |
| `status` | s | n |
| Next Actions | audited provider, cut over webhooks | empty template |
| Progress Log | "Blocked on finance sign-off" | "Task created via MCP `create_task`" |

The response is `{"success": true, "message": "Task 'Migrate billing to Stripe' created successfully"}`.
Nothing signals that a file was replaced.

Realistic triggers are a retry after a timeout, a second backlog-processing run, or the
user asking for the same task twice.

Slug collisions are a secondary path into the same write. `to_slug_filename` strips
punctuation and collapses whitespace, so `Write launch post`, `Write launch post!`,
`Write-launch-post`, and `write  launch   post` all resolve to `write-launch-post.md`.

### Why not treat it as upsert

Two reasons the overwrite is not defensible as replace-by-title:

1. It does not merge. It resets `priority` to P2 and `status` to n, discarding values the
   caller previously set.
2. The same file ships `find_similar_tasks` and `process_backlog_with_dedup` to stop
   duplicate tasks being created. The design intent is "do not clobber".

### The fix

Check for the file explicitly, after `filepath` is built at `System/mcp/server.py:571`:

```python
if filepath.exists():
    result = {
        "success": False,
        "error": f"Task already exists: {filename}",
        "existing_file": filename,
        "hint": "Use update_task_status to change status, or pass a distinct title.",
    }
    return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]
```

"This task already exists" is a normal, expected outcome that the caller needs to act on,
so it has to be a distinguishable result, not an exception string.

### Why mode 'x' is not sufficient on its own

Changing `System/mcp/server.py:589` to `open(filepath, 'x')` does stop the overwrite.
`FileExistsError` reaches the `except Exception` at `System/mcp/server.py:597` and comes
back as `success: False` with the file intact.

But that handler flattens every failure into the same shape, so an expected outcome and a
real I/O fault become indistinguishable:

```
already exists (expected)  {"success": false, "error": "[Errno 17] File exists: '/abs/.../already.md'"}
missing parent (fault)     {"success": false, "error": "[Errno 2] No such file or directory: '/abs/...'"}
target is a dir (fault)    {"success": false, "error": "[Errno 17] File exists: '/abs/.../adir.md'"}
```

Same keys, same `success` value, differing only inside a free-text `error` string. An agent
consuming this cannot tell "the task is already there, move on" from "the write failed,
retry or escalate".

Matching on the errno does not rescue it. A directory sitting at the target path raises
errno 17 with the byte-identical `File exists` message, so `[Errno 17]` does not mean "a
task file is already there". The response also leaks the absolute filesystem path.

Keep `'x'` as a backstop against a second process writing the same path, but it is not
load-bearing. The explicit check is the fix.

## 2. get_system_status crashes on incomplete frontmatter

`System/mcp/server.py:682-684` subscripts directly where every sibling handler uses `.get()`:

```python
priority_counts = Counter(task['priority'] for task in active_tasks)
status_counts = Counter(task['status'] for task in active_tasks)
category_counts = Counter(task['category'] for task in active_tasks)
```

One task file missing `priority:` takes the whole tool down with `KeyError: 'priority'`.
`get_task_summary` survives the same file because it uses `.get()`.

Fix, matching the defaults already used at `System/mcp/server.py:633-635`:

```python
priority_counts = Counter(task.get('priority', 'P2') for task in active_tasks)
status_counts = Counter(task.get('status', 'n') for task in active_tasks)
category_counts = Counter(task.get('category', 'other') for task in active_tasks)
```

## 3. process_backlog never parses sub-items (APPLIED)

Fixed in `System/mcp/server.py:744-758`. The old code tested indentation on a string whose
indentation had already been removed two lines earlier:

```python
stripped = line.strip()
...
elif stripped.startswith('  - ') and current_item:
```

That branch could never fire. Nested items were promoted to top-level, `subitems` was
always empty, and `count` was inflated. A backlog with 2 items and 2 sub-items reported 4.

Fixed by measuring indentation on the raw line:

```python
for line in lines:
    stripped = line.strip()
    if not stripped.startswith('- '):
        continue
    indent = len(line) - len(line.lstrip())
    if indent >= 2 and current_item is not None:
        current_item['subitems'].append(stripped[2:])
    else:
        if current_item:
            items.append(current_item)
        current_item = {'text': stripped[2:], 'subitems': []}
```

Verified through the real `process_backlog` handler on the input that used to fail:

```
count: 3 (was 6 before the fix)
  'Ship the pricing page' subitems=['draft copy', 'get review']
  'Email Dana'            subitems=['about Q3']
  'Orphan'                subitems=[]
```

A sub-item appearing before any parent is treated as a top-level item rather than crashing.

## 4. process_backlog_with_dedup misses duplicates within one batch

`existing_tasks` is snapshotted at `System/mcp/server.py:823` and never updated inside the
loop, so two similar items in the same call are both written without either being flagged.
That is the exact failure the tool exists to prevent:

```
auto_created: ['draft-the-q3-partner-outreach-email.md',
               'draft-the-q3-partner-outreach-emails.md']
dupes flagged: 0
```

Fix: append each created task to `existing_tasks` right after writing it, so the next
iteration's `find_similar_tasks` can see it.

```python
existing_tasks.append({**metadata, 'filename': safe_filename, 'body_content': ''})
```

The write at `System/mcp/server.py:881` is also unguarded and needs the same existence
check as item 1. Here it should skip and report rather than error, since this call
processes a batch: add the skipped filename to a `skipped` list in the result.

## 5. create_task accepts invalid priority, estimated_time, and empty titles

`category` is coerced to `"other"` when invalid (`System/mcp/server.py:566`). Nothing
equivalent exists for the other inputs.

`priority` is written verbatim, so `URGENT` lands in the frontmatter. `check_priority_limits`
then reports `{'URGENT': 1}` while its thresholds only cover P0/P1/P2, so the task escapes
the limit check entirely, and `get_task_summary` only buckets P0-P3, so it vanishes from
`time_by_priority` too. A typo'd priority makes a task invisible to both accounting paths.

`estimated_time` is written verbatim too. A string value crashes a different tool:

```
get_task_summary CRASH: TypeError unsupported operand type(s) for +: 'int' and 'str'
```

A whitespace-only or punctuation-only title slugs to `untitled-task.md`, so every such task
silently replaces the last one once item 1 is not yet fixed.

Fix, alongside the existing category check:

```python
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}   # near VALID_CATEGORIES at line 52

title = str(arguments.get('title') or '').strip()
if not title:
    result = {"success": False, "error": "'title' is required and must be non-empty"}
    return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]

if priority not in VALID_PRIORITIES:
    priority = "P2"

try:
    estimated_time = int(arguments.get('estimated_time', 30))
except (TypeError, ValueError):
    estimated_time = 30
```

Verified behaviour:

```
{'title': '   '}                          -> 'title' is required and must be non-empty
{'title': 'Real', 'priority': 'URGENT'}   -> ('Real', 'P2', 30)
{'title': 'Real', 'priority': 'P0'}       -> ('Real', 'P0', 30)
{'title': 'Real', 'estimated_time': '45'} -> ('Real', 'P2', 45)
```

## 6. Handlers crash when arguments is null

`System/mcp/server.py:560` reads `arguments['title']` outside the `try`, which starts at
line 588. A call with null arguments raises straight out of `handle_call_tool` instead of
returning the handler's own `success: False`:

```
arguments=None -> TypeError: 'NoneType' object is not subscriptable
```

Same shape at `System/mcp/server.py:606` (`update_task_status`) and
`System/mcp/server.py:977` (`annotate_eval`). Input schemas mark these required, but an MCP
client is not obliged to enforce them.

Fix once at the top of `handle_call_tool`:

```python
arguments = arguments or {}
```

This is behaviour-preserving for the handlers that already test `if arguments:`, since an
empty dict is falsy and takes the same branch as `None` did. It converts the crash into a
`KeyError`, so pair it with the explicit required-field checks from item 5 in each of the
three handlers.

## 7. update_file_frontmatter grows a blank line on every update

`parse_yaml_frontmatter` keeps the newlines that followed the closing `---` inside `body`
(`System/mcp/server.py:63`), and `update_file_frontmatter` then adds its own separator on
top of them (`System/mcp/server.py:369`):

```python
new_content = f"---\n{yaml_str}---\n{body}"
```

Every status change adds one blank line, without limit:

```
old: '\n\n# ' '\n\n\n#' '\n\n\n\n'
new: '\n# T' '\n# T' '\n# T'
```

This is not caused by `create_task`'s `---\n\n` separator. It grows the same way whichever
separator the file was created with.

Fix by normalising in the writer:

```python
new_content = f"---\n{yaml_str}---\n\n{body.lstrip(chr(10))}"
```

Verified idempotent across repeated updates, with body content and the applied status
change both preserved.

## 8. setup.sh overwrites GOALS.md (APPLIED)

Fixed in `setup.sh:217-221`. `GOALS.md` was written with an unguarded `cat >`, while
`BACKLOG.md` and `.gitignore` were both guarded. Re-running setup
destroys the file the README calls "the heart of your Personal OS", replacing it with five
fresh answers and nine empty placeholders.

Two approaches fail here.

A plain existence guard does not work, because the repository ships a `GOALS.md` already.
It is an unfilled template, so `if [ -f "GOALS.md" ]` is true on a fresh clone and setup
would never generate goals at all.

Sniffing the content to tell the shipped template from real work does not work either. A
user who fills in goal 1 and leaves goal 2 as `[Goal Name]` still matches the placeholder,
so the guard classifies their work as an untouched template and overwrites it with no
backup, which is the original bug:

```
user content present before run: 1
still contains a [Goal Name] placeholder (goal 2): 1
-> "GOALS.md is the unedited template; generating your version"
AFTER: user content survived? 0
AFTER: backups created?      0
```

Always keep a copy instead. No heuristic, no way to misclassify:

```bash
if [ -f "GOALS.md" ]; then
    goals_backup="GOALS.md.backup-$(date +%Y%m%d%H%M%S)"
    cp "GOALS.md" "$goals_backup"
    print_warning "Existing GOALS.md backed up to $goals_backup"
fi
```

The cost is one backup of the pristine template on a first run, and one per re-run
afterwards. That is preferable to any chance of discarding real goals.

Verified end to end against the partially-filled case that previously lost data:

```
exit=0 (TERM unset)
  Existing GOALS.md backed up to GOALS.md.backup-20260827145650
  user content survived in backup? 1
  GOALS.md regenerated?            1
```

The questions at `setup.sh:157-203` still run in every case, which is correct once the
existing file is backed up rather than discarded.

The backups hold personal goals, so `GOALS.md.backup-*` is now in `.gitignore:23`,
matching the privacy-first intent of the rest of that file. Confirmed with
`git check-ignore`: a backup file does not appear as untracked.

## 9. setup.sh reports .gitignore preserved when it does not exist (APPLIED)

Fixed in `setup.sh:126-133`. The old condition combined two independent tests, so a
missing template fell into the `else` branch and printed a message about a file that was
not there:

```bash
if [ ! -f ".gitignore" ] && [ -f "System/templates/gitignore" ]; then
```

With no `.gitignore` and no template, it printed "File exists: .gitignore (preserving your
version)". Fixed by separating the cases:

```bash
if [ -f ".gitignore" ]; then
    print_info "File exists: .gitignore (preserving your version)"
elif [ -f "System/templates/gitignore" ]; then
    cp "System/templates/gitignore" ".gitignore"
    print_success "Copied: .gitignore"
else
    print_warning "No .gitignore and no template at System/templates/gitignore"
fi
```

Verified end to end across all three states: no template and no file warns accurately,
template present copies it, existing file is preserved.

## 10. setup.sh aborts when TERM is unset (APPLIED)

Fixed in `setup.sh:83`. `clear` exits 1 when `TERM` is unset, and `set -e` is on at
`setup.sh:6`, so the script died before printing anything, as
`TERM environment variable not set. exit=1`.

Every end-to-end run recorded above now completes with `exit=0` under `env -u TERM`.

Fixed by:

```bash
clear 2>/dev/null || true
```

## 11. Eval runners write results without creating the directory (APPLIED)

Fixed in `scripts/run_routing_evals.py:75` and `scripts/run_memory_impact_evals.py:81`.
Both called `write_text` on a path whose parent might not exist, and worked only because
the results directories happen to be committed. `scripts/run_skill_evals.py:199` already
did this correctly.

```python
out.parent.mkdir(parents=True, exist_ok=True)
```

Confirmed the failure was real, not theoretical. Pre-fix, with the results directory
removed:

```
FileNotFoundError: [Errno 2] No such file or directory:
  '.../Evals/skills/results/20260827T145822Z-routing.json'
```

Post-fix, both runners recreate the directory and complete normally.

## 12. The documented MCP run command targets the wrong workspace

`System/README.md:36-40` says:

```bash
cd System/mcp
pip install pyyaml mcp
python server.py
```

`BASE_DIR` defaults to `Path.cwd()` (`System/mcp/server.py:38`) and `TASKS_DIR.mkdir()`
runs at import, so following the documented command creates `System/mcp/Tasks/` and
`System/mcp/Evals/` and looks for `System/mcp/BACKLOG.md`. The server only finds the real
workspace if `PERSONAL_OS_DIR` is set, which the README does not mention.

Two options, needing a decision:

- Document `PERSONAL_OS_DIR` in the README and leave the default alone.
- Default to the repo root instead of the process working directory:

  ```python
  BASE_DIR = Path(os.environ.get('PERSONAL_OS_DIR') or Path(__file__).resolve().parents[2])
  ```

  `parents[2]` resolves to the repo root from `System/mcp/server.py`, verified.

The second is more robust but changes behaviour for anyone already relying on cwd.

Unrelated but adjacent: `System/requirements.txt` lists `anthropic>=0.18.0`, which is not
imported anywhere in the repo.

## 13. generate_eval imports modules that do not exist

`System/mcp/server.py:947` imports `trace_parser` and `trace_to_eval`. Neither exists
anywhere in the repository, so the tool is advertised in `list_tools` and always returns
`{"success": false, "error": "Trace parser not available: ..."}`.

Needs a decision: ship the two modules, or drop the tool from `handle_list_tools` so it
stops being advertised as available.

## 14. The shipped GOALS.md and the generated one are different documents

The `GOALS.md` committed to the repository and the one `setup.sh` writes share exactly one
heading, `## Ongoing`. Even the title differs.

| Committed `GOALS.md` | Generated by `setup.sh:210-296` |
|----------------------|----------------------------------|
| `# Goals` | `# Goals & Strategic Direction` |
| `## Current Goals` (numbered goals, Key Results) | `## Current Context` |
| `## Ongoing` | `## Ongoing` |
| `## Not Now (Parked)` | `## Success Criteria` |
| `## Review Cadence` | `## Strategic Context`, `## Priority Framework` |

Running setup replaces a goals-and-key-results structure with an interview transcript. Both
are readable by an agent, since `AGENTS.md` only says to read `GOALS.md` for priorities
without pinning a format, so nothing breaks outright. But a user who fills in the committed
template and then runs setup gets a document organised on entirely different lines.

Needs a decision: make the generated file match the shipped template's structure, or
replace the shipped template with the generated layout so there is one format.

## 15. Routing eval matches bare substrings and scores only part of the answer (APPLIED)

Fixed in `scripts/run_routing_evals.py:27-35` and `:55-60`.

`route_skills` matched bare substrings, so keywords fired inside unrelated words:

```
'Write an explanation of the auth flow'   -> writing-plans      ('plan' in 'explanation')
'The migration is incomplete'             -> verification, ...  ('complete' in 'incomplete')
'We abandoned that approach'              -> verification       ('done' in 'abandoned')
'Retrace your footsteps in the changelog' -> writing-plans      ('steps' in 'footsteps')
```

The scorer could not catch that, because it only checked `should_select` and
`should_not_select`. Each case constrains 2 or 3 of the 5 skills and ignores the rest, so a
router returning every skill a case does not explicitly forbid scored 5/5, the same as the
correct router.

Both fixed. Matching is now anchored, via `_boundary_pattern` at
`scripts/run_routing_evals.py:28-35`:

```python
return r"(?<!\w)" + re.escape(keyword.lower()) + r"(?!\w)"
```

Two details that a plain `\b{re.escape(p)}\b` got wrong. `text.lower()` normalised only
one side of the comparison, so a rule written as `Red Green` would never match anything and
never say so. And `\b` cannot anchor a keyword whose first or last character is not a word
character, so `c++` or `-v` would never match either. Lowercasing the keyword and using
lookarounds fixes both:

```
pattern '+1'   \b matches=False   fixed matches=True
pattern 'c++'  \b matches=False   fixed matches=True
'Try Red Green refactor'  \b version=(wrong skill)  fixed=(correct skill)
```

and `should_select` is treated as the complete expected answer:

```python
unexpected = sorted(list(selected - should))
ok = not missing and not unexpected
```

Neither change required rewriting a case:

```
                              current scorer   closed-world
current substring router          5/5              5/5
word-boundary router              5/5              5/5
imprecise router                  5/5              0/5
```

Verified against the live script after the change: the real suite still passes 5/5, the
imprecise router drops to 0/5, and three of the four false positives become `(none)`.
`The migration is incomplete` still selects `writing-plans`, correctly, because *migration*
is a genuine keyword for that skill.

## 16. The eval runners could only test themselves (APPLIED)

All three runners scored something the repository had written for itself. Correcting an
earlier version of this note: it said two of three, on the assumption that
`run_skill_evals.py` had a sound live path. Running that path proved otherwise, so it was
three of three.

`run_routing_evals.py` defined the router it evaluated. `run_memory_impact_evals.py:44-45`
still reads both sides of its A/B comparison out of the cases file. And
`run_skill_evals.py`'s `--provider openai` never sent the skill under test, so it measured
the base model's default behaviour, while its fixed system prompt said "include concrete
verification-oriented guidance" and thereby handed the verification cases a scored token
before the model spoke.

### What changed

A shared `scripts/model_client.py` now holds one hardened `query_chat`, and both runners
take `--provider`.

`run_routing_evals.py` gains `--provider {keyword,openai}`, defaulting to `keyword` so
offline runs are unchanged. The `openai` path sends the skill catalogue built from each
`SKILL.md` frontmatter and the Skill Routing Policy section lifted from `AGENTS.md`, then
parses a JSON array of skill names. Verified against a stub:

```
every skill named        : True
SKILL.md descriptions    : True
AGENTS.md routing policy : True
user message is the case : True
["tdd"]                 -> ['tdd']
["tdd", "verification"] -> ['tdd', 'verification']
[]                      -> []
fenced ```json [...]``` -> ['tdd']
```

The first version also fell back to scanning the reply for skill names when it carried no
array. That scan was blind to negation, exactly like item 18: `tdd does not apply here`
selected tdd, and `this is not a brainstorming task` selected brainstorming, inverting the
model's answer. The fallback is gone. A reply with no array is a protocol failure and is
reported as one, which is better than guessing the opposite of what the model meant:

```
NEGATED prose      -> ModelError: reply contained no JSON array of skill names: 'tdd does not apply here.'
bare prose         -> ModelError: reply contained no JSON array of skill names: 'I think you want the tdd skill here.'
unknown skill name -> ModelError: reply named unknown skill(s): ['not-a-real-skill']
```

`run_skill_evals.py:174-181` now sends the skill under test, built from its own `SKILL.md`
description, under a system prompt free of the scored vocabulary:

```
skill named in prompt : True
leaks 'verification'  : False
```

### Proof it now discriminates

A stub that answers `["tdd"]` regardless of input scores 1/5 rather than 5/5, because only
the tdd case is actually satisfied:

```
model returns ["tdd"]  rc=1  PASS RATE: 1/5 = 0.200
model returns prose    rc=1  PASS RATE: 1/5 = 0.200
```

### Error handling

`query_chat` raises `ModelError` with a readable message instead of the three failures the
old inline client had, and each runner records the error against the case and continues:

```
server 500        - [FAIL] ... (HTTP 500 from http://...: upstream exploded)
null content      - [FAIL] ... (response carried a null content (refusal or tool call))
API error object  - [FAIL] ... (API error: invalid api key)
```

Previously these raised `HTTPError`, returned `None` that crashed scoring with
`AttributeError`, and raised a bare `KeyError: 'choices'` that discarded the API's own
message. Because nothing was written until after the loop, one failure destroyed every
result already computed. Now the run completes and the file is written:

```
results file written despite every request failing: True
  cases recorded : 5 of 5
  first error    : HTTP 500 from http://127.0.0.1:8479/v1: upstream exploded
```

### Still outstanding

`run_memory_impact_evals.py` remains self-referential; making it real means generating both
sides rather than reading them from the cases file. And the live paths are verified only
against a stub. Whether a real model's output clears the token-overlap threshold is untested,
and that threshold is a crude proxy for the behaviour these cases describe.

## 17. Nothing validated routing_cases.json (APPLIED)

Added `validate_cases` at `scripts/run_routing_evals.py:38-73`, called before scoring.

`validate_skill_eval_cases.py` globs `Evals/skills/cases/*.json`, and `routing_cases.json`
sits one level above that, so no schema check covered it at all. Two consequences went
unreported until they were tested for:

A misspelt skill in `should_select` made a case permanently unpassable with no diagnostic
anywhere, since the name can never be selected:

```
typo case: selected=['verification'] missing=['verifcation'] -> can NEVER pass, nothing warns
```

Worse, the closed-world rule from item 15 removed the only thing that caught a
self-contradictory case. Before that change `should_not_select` failed it; afterwards it
passes silently:

```
contradictory case should_select=['tdd'] should_not_select=['tdd']
selection ['tdd']: old rule passes=False   current rule passes=True
```

That is a regression item 15 introduced. Rather than restore a redundant scoring term, the
contradiction is now rejected at load time, along with the other malformations:

```
contradiction: ['tdd'] listed in both should_select and should_not_select
typo:          unknown skill 'verifcation' (not in KEYWORD_RULES)
bogus:         unknown skill 'nonexistent-skill' (not in KEYWORD_RULES)
dup:           duplicate id
dup:           missing or empty 'input'
dup:           'should_select' must be a non-empty list
```

Verified end to end: a contradictory cases file exits 2 with the error above, and the real
`routing_cases.json` reports no errors and still passes 5/5.

## 18. Token-set scoring cannot tell a skill from its opposite (APPLIED)

Found by running `tdd/tdd-code-first-request` rather than trusting that it passed.

The case expects `enforces failing test first` and `uses red green refactor sequence`.
`_score_expectation` compares unordered token sets, so it is blind to negation. A response
arguing *against* TDD outscores the correct one:

```
correct fixture  scores=[0.75, 0.8]  passes=True
INVERTED answer  scores=[1.0, 1.0]   passes=True
```

The inverted answer was "Skip the failing test first, red green refactor is a waste of time,
enforces nothing, just uses your judgement and ships the sequence." It shares every token
with the expectations. The case was passing for the wrong reason, and would pass for advice
that actively contradicts the skill.

The fixture is also written from the expectations, supplying 7 of their 9 tokens, so the
fixture path passes by construction the same way item 16's runners did.

### Two fixes

An offline `reject` list per case, checked in `_find_rejections`. Any listed phrase present
in the response fails the case outright, whatever the overlap score:

```
correct fixture  passed=True   rejected=None
INVERTED answer  passed=False  rejected=['waste of time', 'skip the failing test']
```

`reject` is optional, validated by `validate_skill_eval_cases.py`, and populated for both
tdd cases.

And `--judge openai`, which grades each expectation with a model instead of token overlap,
using the client from item 16. Its prompt says to judge the stance the response takes rather
than whether it reuses the expectation's words. Verified against a stub:

```
judge answers YES -> PASS RATE: 2/2 = 1.000  rc=0
judge answers NO  -> PASS RATE: 0/2 = 0.000  rc=1
```

Judge failures are recorded per case like any other model error rather than aborting the run.

### What this does not fix

`reject` is a blocklist, so it catches the inversions someone thought to write down and
nothing else. The default remains `--judge overlap`, which stays gameable by any response
that reuses the right words in the wrong order. Only the judge actually evaluates the claim
the expectation makes, and it is verified against a stub, not a real model.

## Verifying the fixes

1. Create a task, set status to `s`, edit the progress log. Call `create_task` again with
   the same title. Expect `success: false` and the file unchanged on disk.
2. Call `create_task` with a title differing only in punctuation. Expect the same refusal.
3. Put a task file with no `priority:` in `Tasks/`. Expect `get_system_status` to return
   rather than raise.
4. Run `process_backlog` on a backlog with nested items. Expect the top-level count to
   exclude sub-items, and `subitems` to be populated.
5. Call `process_backlog_with_dedup` with two near-identical items and `auto_create: true`.
   Expect one created task and one flagged duplicate.
6. Call `create_task` with `priority: "URGENT"`, `estimated_time: "45"`, and a
   whitespace-only title. Expect P2, 30, and a refusal respectively.
7. Call each of `create_task`, `update_task_status`, `annotate_eval` with null arguments.
   Expect a structured error, not a traceback.
8. Change one task's status three times. Expect exactly one blank line after the
   frontmatter each time.
9. Run `setup.sh` on a fresh clone. Expect it to generate `GOALS.md` over the unedited
   template. Edit the result, run setup again, and expect the edited version to survive in
   a `GOALS.md.backup-*` file.
10. Run `setup.sh` with `TERM` unset and with no `System/templates/gitignore`. Expect it to
    complete and to report the missing template accurately.
