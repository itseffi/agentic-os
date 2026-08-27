# Fix: create_task overwrites existing tasks

Status: not applied. Written up after an audit of `System/mcp/server.py`.

## The bug

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

## What it costs

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

## Why not treat it as upsert

Two reasons the overwrite is not defensible as replace-by-title:

1. It does not merge. It resets `priority` to P2 and `status` to n, discarding values the
   caller previously set.
2. The same file ships `find_similar_tasks` and `process_backlog_with_dedup` to stop
   duplicate tasks being created. The design intent is "do not clobber".

## The fix

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

## Second call site

`process_backlog_with_dedup` has the same unguarded write when `auto_create` is true, at
`System/mcp/server.py:881`. It needs the same guard, reporting skipped items rather than
returning an error, since it processes a batch.

That handler has a related defect worth fixing in the same pass: `existing_tasks` is
snapshotted at `System/mcp/server.py:823` and never updated inside the loop, so two similar
items in one batch both get written without being flagged as duplicates. Append each
created task's metadata to `existing_tasks` after writing it.

## Verifying the fix

1. Create a task, set status to `s`, edit the progress log.
2. Call `create_task` again with the same title. Expect `success: false` and the file
   unchanged on disk.
3. Call `create_task` with a title differing only in punctuation. Expect the same refusal.
4. Call `process_backlog_with_dedup` with two near-identical items and `auto_create: true`.
   Expect one created task and one flagged duplicate.
