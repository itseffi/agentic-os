# Fix notes

Status: items 3, 8, 9, 10, 11, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25 and 26 are applied. The rest are documented only. Findings from an audit of
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

Correcting an overstatement in an earlier version of this section. It said the reject list
catches "the inversions someone thought to write down", which implied it covers the realistic
ones. It does not. The demonstration used to justify it was circular: the inverted sentence
was built out of the blocklist, so it proved only that the blocklist matches itself.

A realistic inversion discusses the skill in the skill's own vocabulary while advising
against it. It names none of the blocked phrases and still scores 0.75 to 1.00:

```
scores=[0.75, 0.8] rejected=None PASSED=True
  "You could do the red-green-refactor sequence with a failing test first, but for this
   small change I'd write the code and add a test after."
scores=[1.0, 1.0]  rejected=None PASSED=True
  "Normally TDD enforces a failing test first and uses the red green refactor sequence;
   here that's overkill, so implement first."
```

So `reject` catches only blunt inversions that happen to name a listed phrase. Blunt ones
mostly fail on overlap anyway, since they lack the vocabulary. The dangerous case, right
words and wrong stance, passes.

`test_overlap_judge_cannot_detect_stance` in `scripts/test_eval_runners.py` pins this as a
known gap, so it is visible rather than implied, and tells whoever closes it to update this
section. Only `--judge openai` evaluates the claim, and it is verified against a stub, not a
real model.

All three runners now say what a green run is green about, on stdout and in the results file,
so a pass rate cannot be quoted as evidence of correctness on its own.

A first attempt at this was itself asymmetric and had to be redone. The skill runner has two
independent axes, `--provider` for where responses come from and `--judge` for how they are
scored, and only the judge was disclosed. So `--provider fixture --judge openai` printed
nothing at all and recorded `judge_caveat: None`, while every response it scored was canned
text from `Evals/skills/fixtures`. The memory runner, the most self-referential of the three,
had no `provider` field and no caveat of any kind.

Each self-referential axis is now disclosed independently:

| run | caveats emitted |
|-----|-----------------|
| skill evals, fixture + overlap | `provider_caveat`, `judge_caveat` |
| skill evals, fixture + openai judge | `provider_caveat` |
| routing, keyword | `provider_caveat` |
| memory impact | `provider_caveat` (no provider option exists) |
| routing, openai | none, and no NOTE |

`test_every_self_referential_axis_is_disclosed` runs that whole matrix, asserting one NOTE
per caveat and the matching key in the written file, and that the one genuinely non-canned
combination stays silent.

Running that test by hand then showed the routing runner held two separate strings, one
printed and one recorded, which had already drifted apart: stdout named `--provider openai`
as the alternative while the file said only "built-in keyword table, not an agent". Skill
evals and memory each used a single variable for both. Routing now does too, via
`KEYWORD_CAVEAT`, and the test asserts the printed and recorded text are identical, which
fails if they diverge again:

```
- run_routing_evals.py: printed and recorded caveats match
  (printed {'something else entirely'} vs recorded {"--provider keyword scores ..."})
```

## 19. The repository had no tests at all (APPLIED)

Added `scripts/test_eval_runners.py`, 45 checks, run with `python3 scripts/test_eval_runners.py`.

Every fix in this note was verified once, in a throwaway script, and then discarded. Nothing
in the repository could re-run any of it, and there were no tests anywhere: no `tests/`
directory, no `test_*.py`, no pytest. The eval runners were the only executable checks, and
nothing checked them.

That is why several fixes here broke each other, each caught by review rather than by a
suite:

- closed-world scoring (item 15) silently disabled the contradiction check (item 17)
- `\b` anchors (item 15) stopped keywords like `c++` matching at all
- the routing prose fallback (item 16) selected the skill a model had just ruled out

The suite covers exactly those regressions, plus the model client's failure modes, the
routing prompt contents, case validation, and the reject phrases. It uses a stub HTTP server
on an ephemeral port, no network, and no test framework, matching the other scripts here.

Confirmed it fails when the bugs come back. Reverting `_boundary_pattern` to a bare substring
and removing the `reject` lists:

```
FAIL: 6 of 45 check(s) failed
- no false positive: 'Write an explanation of the auth flow' (selected ['writing-plans'])
- no false positive: 'We abandoned that approach' (selected ['verification'])
- true positive survives
- inverted answer fails (it passed)
- failure names the phrases (None)
```

and passing again once restored.

One check was wrong on the first run and was corrected rather than the code: it asserted the
skill prompt shared no scored vocabulary at all, but the overlap came from the skill's own
`SKILL.md` description, which a real agent also sees. The check now excludes the description
and tests the scaffolding around it, which is where the old `verification-oriented guidance`
contamination lived. The description still overlaps the expectations heavily, which is a
standing argument for `--judge openai` over token overlap.

## 20. Runners sent a bogus `Bearer none` credential (APPLIED)

Fixed in `scripts/model_client.py` and both runners' `--api-key` defaults.

`--api-key` defaulted to the literal string `"none"`, which was sent verbatim:

```
with the shipped --api-key default, the header sent is: 'Bearer none'
```

That gives a local endpoint needing no key a bogus credential, and a real endpoint an auth
error rather than a clear statement that no key was configured. I noted this in the original
audit and then never fixed it.

The default is now empty, and `query_chat` sends no `Authorization` header unless a key is
actually set. Covered by `test_auth_header`:

```
api_key=''        sends None
api_key='none'    sends None
api_key='sk-real' sends 'Bearer sk-real'
```

## 21. --base-url silently defaulted while --model was required (APPLIED)

Fixed in both runners' argument parsers and their validation.

`--model` was checked and exited 2 with a clear message. `--base-url` was not: it defaulted
to `http://localhost:8080/v1`, so the same class of misconfiguration produced a red eval
instead of an error message:

```
PASS RATE: 0/5 = 0.000
- [FAIL] route-verification-no-evidence -> selected=(none)  (could not reach http://localhost:8080/v1: [Errno 111] Connection refused)
- [FAIL] route-tdd-code-first -> selected=(none)  (could not reach http://localhost:8080/v1: [Errno 111] Connection refused)
```

A 0/5 that reads like the router is broken, when nothing was configured. Both settings are
now validated together before any request:

```
$ run_routing_evals.py --provider openai
ERROR: --model and --base-url required when --provider openai (or set OPENAI_MODEL / OPENAI_BASE_URL)
$ run_skill_evals.py --judge openai
ERROR: --model and --base-url required by --judge openai (or set OPENAI_MODEL / OPENAI_BASE_URL)
```

The help text was also stale. `--base-url` and `--model` said "for --provider openai", but
`--judge openai` needs both, a check added in item 18 without updating the strings beside it.

`test_model_settings_are_required_not_defaulted` covers all four combinations, asserting
exit 2, that the message names the missing flags, that no request is attempted, and that the
help mentions `--judge openai`.

## 22. Routing and skill cases duplicated the same prompts (APPLIED)

Added `Evals/scenarios.json`; both suites now reference shared prompts by id.

Three of the five routing cases were copies of a skill eval case. One was verbatim, and two
had already drifted apart:

```
1.00  route-verification-no-evidence  / verification-no-evidence-claim
        'Mark this complete, tests should pass now.'          (identical)
0.86  route-tdd-code-first            / tdd-code-first-request
        'Implement it first, we can test later.'
        "Implement this first, we'll test later."
0.74  route-writing-plans-migration   / writing-plans-multi-step-migration
        'Plan a multi-file migration with checkpoints before editing code.'
        'Plan a multi-file migration with validation checkpoints.'
```

Two costs. Editing a scenario in one suite silently leaves the other on the old wording,
which had already happened twice. And the two suites look like independent signals while
largely exercising the same prompts, so a green board reads as two confirmations of one
thing.

Sharing is the right relationship here, not separation: routing asks which skill applies to
a prompt, and the skill evals ask whether a response to that same prompt follows the skill.
They compose. So the prompts moved to `Evals/scenarios.json` and each case references one by
id:

```json
{ "id": "route-tdd-code-first", "scenario": "code-first-request", "should_select": ["tdd"] }
```

A case supplies its prompt inline via `input` or by `scenario` id, never both, never neither.
Both validators enforce that and reject unknown scenario ids.

`test_no_duplicated_prompts_across_suites` fails on any near-identical pair across suites
while allowing identical ones, since identical now means both reference the same id.
`test_scenario_references_are_validated` covers the three malformed forms.

The migration was caught by the suite rather than by review: `test_closed_world_scoring` was
still reading `case["input"]` and raised `KeyError: 'input'`, which is the first time this
session that a regression was found by a test instead of by being pointed out.

## 23. Scoring differed per runner, with vacuous passes in two of them (APPLIED)

Tested each runner's scoring in isolation rather than through a green suite. Routing was
sound; the other two were not.

Routing scores exact set equality, no partial credit in either direction:

```
selected=tdd              should=tdd   pass=True
selected=-                should=tdd   pass=False
selected=tdd,verification should=tdd   pass=False
```

`run_memory_impact_evals._contains_phrase` did not do what its name says. It tested token-set
subset membership, so it matched the words in any order, scattered anywhere in the response,
and returned `True` for an empty phrase:

```
exact                         -> True
SHUFFLED                      -> True
SCATTERED across a sentence   -> True
EMPTY PHRASE                  -> True
```

All 16 expectations across the shipped cases hold under strict contiguous matching too, so
the loose reading bought nothing and only obscured what the check meant. It now matches a
contiguous phrase, with the same lookaround anchoring used for routing keywords.

Two vacuous passes, both now rejected rather than scored:

- A skill expectation of `""` scored 1.00, because `_score_expectation` returned 1.0 for an
  expectation with no tokens. It raises now, and the validator rejects empty strings inside
  `expected`.
- A memory case with both expectation lists empty passed with nothing asserted. And nothing
  validated `Evals/memory/cases.json` at all, the same gap item 17 closed for the routing
  cases and never closed here.

`validate_cases` in the memory runner now checks ids, duplicates, the three required text
fields, at least one expectation, and rejects empty phrases:

```
$ run_memory_impact_evals.py            # against a vacuous case file
ERROR: 1 invalid case(s) in Evals/memory/cases.json
- vacuous: needs at least one expectation; empty lists pass vacuously
exit=2
```

`test_scoring_per_runner` pins what a pass means in each runner, and `test_no_vacuous_passes`
covers the rejections. Order-blindness in the skill metric is left as-is and stays pinned by
`test_overlap_judge_cannot_detect_stance`; it is inherent to token overlap, which is why
`--judge openai` exists.

## 24. Result files silently overwrote each other, and two helpers were copy-pasted (APPLIED)

Added `scripts/eval_io.py`; all three runners now use it.

Result filenames are stamped to the second, `{timestamp}-{provider}.json`, so two runs
inside the same second resolved to the same path and the second destroyed the first. Noted
in the original audit as minor and never fixed, more than twenty commits ago.

It surfaced as a confusing failure rather than as lost data. Running a runner and then the
test suite within the same second produced:

```
File "scripts/test_eval_runners.py", line 366, in <setcomp>
    recorded = {" ".join(str(payload[k]).split()) for k in expected_keys}
KeyError: 'provider_caveat'
```

Nothing to do with the collision on its face. The disclosure test identified the file it had
just written by diffing a glob of the results directory; when the runner overwrote an
existing path instead of creating one, the diff was empty, `payload` was `{}`, and the
KeyError landed three lines later. A real bug reported as an unrelated crash.

Two fixes. `unique_results_path` appends `-2`, `-3` and so on rather than overwriting:

```
RESULTS: Evals/skills/results/20260827T154336Z-routing.json
RESULTS: Evals/skills/results/20260827T154336Z-routing-2.json
RESULTS: Evals/skills/results/20260827T154336Z-routing-3.json
```

And the test now reads the path the runner prints instead of inferring it, so a collision
could not be misreported again.

The same commit removes duplication introduced by item 22's own fix: `load_scenarios` and
`case_input` had been copy-pasted into both runners, which is exactly the pattern item 22
had just eliminated from the case files. Both now import from `eval_io`, along with the
memory runner.

`test_results_paths_do_not_collide` runs the routing eval three times in immediate
succession and asserts three distinct paths, all present on disk.

## 25. Validation errors named a repo-relative path from any tree (APPLIED)

Both runners printed `CASES_PATH.relative_to(ROOT)` on a validation failure, and `ROOT` comes
from `__file__`. Run a copy of the script against a bad file anywhere on disk and it still
reported a repo path:

```
ERROR: 1 invalid case(s) in Evals/memory/cases.json
```

That output is indistinguishable from the checked-in file being broken, and it caused exactly
that false alarm: the demonstration in item 23 was a synthetic file in a scratch directory,
but the message read as though `Evals/memory/cases.json` in this repository had failed. It
had not, and does not:

```
cases: 3
validation errors: none
PASS RATE: 3/3 = 1.000
```

Errors now name the absolute path, which is what `validate_skill_eval_cases.py` already did:

```
ERROR: 1 invalid case(s) in /tmp/.../scratchpad/mem2/Evals/memory/cases.json
```

Routine success output keeps the relative form, which is friendlier and unambiguous in
context. `test_error_messages_name_an_absolute_path` builds a sandboxed copy of each runner
with a deliberately bad case file and asserts the error names the sandbox and not this
repository.

## 26. The skill case validator lagged the other two (APPLIED)

Comparing the three validators side by side, `validate_skill_eval_cases.py` was missing
checks the routing and memory validators already had, and two of the gaps had teeth.

**No duplicate-id check.** Both other validators reject a repeated case id; this one accepted
two cases sharing `id: "dup"`.

**No check that `skill` matches the filename.** The runner picks fixtures by the `skill`
field, not the filename, and applies `--skill` against it. So a file named `tdd.json`
declaring `"skill": "verification"` scored its cases against verification's fixture responses
and reported a clean pass:

```
PASS RATE: 1/1 = 1.000
- [PASS] verification/borrowed
```

A file named tdd.json, tested entirely against another skill's fixtures, silently.

**No check that a fixture response exists per case.** A case without one aborted the run
mid-suite with an uncaught `FileNotFoundError` or `KeyError` rather than a validation error.

All three are now checked, along with `skill` naming a real pack in `.agents/skills`.

The fixture check was wrong on its first attempt and the new test caught it: it read
`if fixture_ids and case_id not in fixture_ids`, so an empty fixture file produced an empty
set, the guard was falsy, and validation was skipped for precisely the file that most needed
it. Loading is now tracked with its own flag.

`test_skill_case_validator_parity` builds a sandbox per scenario and covers duplicate ids,
filename mismatch, unknown skill pack, missing fixture response, and that a well-formed file
still passes.

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
