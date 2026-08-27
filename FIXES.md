# Fix notes

Status: items 3, 8, 9 and 10 are applied. The rest are documented only. Findings from an audit of
`System/mcp/server.py`, `scripts/`, and `setup.sh`. Each fix below was checked against the
real code path before being written down.

Open question: items 12, 13 and 14 are design calls, not mechanical fixes. They need a decision
before anyone patches them.

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

Open point: the backups are untracked files holding personal goals, in a repository whose
`.gitignore` is explicitly privacy-first. Adding `GOALS.md.backup-*` to `.gitignore` would
match that intent, but it was left out as it goes beyond the fix.

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

## 11. Eval runners write results without creating the directory

`scripts/run_routing_evals.py:85` and `scripts/run_memory_impact_evals.py:91` call
`write_text` on a path whose parent may not exist. `scripts/run_skill_evals.py:199` gets
this right. Both currently work only because the results directories are committed.

Fix, in both files before the write:

```python
out.parent.mkdir(parents=True, exist_ok=True)
```

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
