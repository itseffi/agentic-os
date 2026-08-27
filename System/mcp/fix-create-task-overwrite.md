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

Change the write mode at `System/mcp/server.py:589` from `'w'` to `'x'`:

```python
with open(filepath, 'x') as f:
```

That is the whole fix. `'x'` refuses to open a file that already exists, raising
`FileExistsError`, which the `except Exception` at `System/mcp/server.py:597` already
catches and turns into `success: False`. The existing file is left untouched:

```
'x' alone -> {'success': False, 'error': "[Errno 17] File exists: '/tmp/.../t.md'"}
file preserved: True
```

No separate existence check is needed for correctness.

### Optional: a better error message

`'x'` returns a raw errno string. If the caller deserves something clearer, add an
explicit check after `filepath` is built at `System/mcp/server.py:571`:

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

This is a message improvement, not a second layer of protection. Keep `'x'` regardless,
since it is what actually prevents the overwrite.

The check does not guard a race. Everything between the check and the write is
synchronous with no `await`, so no other coroutine in this single-threaded stdio server
can interleave. Only a second process writing the same path could, which `'x'` handles on
its own.

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
