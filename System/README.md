# System

Reusable components that power Personal OS. Most users won't need to modify these.

## Contents

```
System/
├── mcp/                    # Optional MCP server
│   └── server.py           # Task management with deduplication
├── templates/              # Setup templates
│   ├── config.yaml         # Configuration template
│   └── gitignore           # Git ignore template
└── integrations/           # External tool integrations
    ├── granola/            # Granola meeting sync
    ├── slack/              # Slack message checks
    ├── linear/             # Linear issue sync
    ├── google-calendar/    # Calendar-aware planning
    └── atlassian/          # Jira + Confluence
```

## MCP Server (Optional)

The MCP server provides AI agents with structured tools for task management:

| Tool | Description |
|------|-------------|
| `list_tasks` | Filter and view tasks |
| `create_task` | Create new task with metadata |
| `update_task_status` | Change task status |
| `process_backlog_with_dedup` | Smart backlog processing |
| `get_task_summary` | Statistics and overview |

### Running the Server

```bash
pip install -r System/requirements.txt
python System/mcp/server.py
```

The server operates on the repository the script lives in. Set `PERSONAL_OS_DIR` to point it
at a different workspace:

```bash
PERSONAL_OS_DIR=/path/to/your/personal-os python System/mcp/server.py
```

Most users don't need the MCP server - AGENTS.md works directly with files.

## Templates

Used by `setup.sh` to initialize a new Personal OS:

- **config.yaml** - Optional configuration
- **gitignore** - Keeps personal data local

## Integrations

External tools that extend Personal OS:

| Integration | Description |
|-------------|-------------|
| [Granola](integrations/granola/) | Sync meeting notes and transcripts |
| [Slack](integrations/slack/) | Check channel and DM activity |
| [Linear](integrations/linear/) | Sync issues with local tasks |
| [Google Calendar](integrations/google-calendar/) | Plan around schedule and free slots |
| [Atlassian](integrations/atlassian/) | Jira issue and Confluence workflows |

See [integrations/README.md](integrations/README.md) for setup guides.

## When to Modify

**Usually don't:**
- Templates work for most use cases
- MCP server is optional

**Consider modifying when:**
- Adding custom categories to config.yaml
- Creating new integrations
- Extending MCP server tools
