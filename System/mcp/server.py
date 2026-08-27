#!/usr/bin/env python3
"""
MCP Server for Personal OS - Task Management
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from collections import Counter

# MCP server for task management

import yaml
import re
from difflib import SequenceMatcher
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom JSON encoder for handling date/datetime objects
class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles date and datetime objects"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

# Configuration - PERSONAL_OS_DIR, else the repository this file lives in.
# Defaulting to the process working directory meant the documented invocation,
# `cd System/mcp && python server.py`, created System/mcp/Tasks and System/mcp/Evals and
# looked for System/mcp/BACKLOG.md, silently operating on an empty workspace.
BASE_DIR = Path(os.environ.get('PERSONAL_OS_DIR') or Path(__file__).resolve().parents[2])
TASKS_DIR = BASE_DIR / 'Tasks'
EVALS_DIR = BASE_DIR / 'Evals'

# Ensure directories exist
TASKS_DIR.mkdir(exist_ok=True, parents=True)
EVALS_DIR.mkdir(exist_ok=True, parents=True)

# Duplicate detection configuration
DEDUP_CONFIG = {
    "similarity_threshold": 0.6,  # How similar before flagging as potential duplicate
    "check_categories": True,     # Same category increases similarity score
}

VALID_CATEGORIES = {"technical", "outreach", "research", "writing", "admin", "personal", "other"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}

def parse_yaml_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content"""
    if not content.startswith('---'):
        return {}, content
    
    try:
        parts = content.split('---', 2)[1:]
        if len(parts) >= 1:
            metadata = yaml.safe_load(parts[0])
            body = parts[1] if len(parts) > 1 else ''
            return metadata or {}, body
    except Exception as e:
        logger.error(f"Error parsing YAML: {e}")
        return {}, content

def get_all_tasks() -> List[Dict[str, Any]]:
    """Get all tasks from the Tasks directory"""
    tasks = []
    if not TASKS_DIR.exists():
        return tasks
    
    for task_file in TASKS_DIR.glob('*.md'):
        try:
            with open(task_file, 'r') as f:
                content = f.read()
                metadata, body = parse_yaml_frontmatter(content)
                if metadata:
                    metadata['filename'] = task_file.name
                    metadata['body_content'] = body[:500] if body else ''
                    tasks.append(metadata)
        except Exception as e:
            logger.error(f"Error reading {task_file}: {e}")
    
    return tasks

def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two strings (0-1 score)"""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def extract_keywords(text: str) -> set:
    """Extract meaningful keywords from text"""
    # Remove common words and extract meaningful terms
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'from', 'up', 'out'}
    words = re.findall(r'\b\w+\b', text.lower())
    return {w for w in words if w not in stop_words and len(w) > 2}

def find_similar_tasks(item: str, existing_tasks: List[Dict[str, Any]], config: dict = DEDUP_CONFIG) -> List[Dict[str, Any]]:
    """Find tasks similar to the given item"""
    similar = []
    item_keywords = extract_keywords(item)
    
    for task in existing_tasks:
        # Skip completed tasks
        if task.get('status') == 'd':
            continue
            
        # Calculate title similarity
        title = task.get('title', '')
        title_similarity = calculate_similarity(item, title)
        
        # Calculate keyword overlap
        task_keywords = extract_keywords(title)
        if item_keywords and task_keywords:
            keyword_overlap = len(item_keywords & task_keywords) / len(item_keywords | task_keywords)
        else:
            keyword_overlap = 0
        
        # Combined score
        similarity_score = (title_similarity * 0.7) + (keyword_overlap * 0.3)
        
        # Check if it's a potential duplicate
        if similarity_score >= config['similarity_threshold']:
            similar.append({
                'title': title,
                'filename': task.get('filename', ''),
                'category': task.get('category', ''),
                'status': task.get('status', ''),
                'similarity_score': round(similarity_score, 2)
            })
    
    # Sort by similarity score
    similar.sort(key=lambda x: x['similarity_score'], reverse=True)
    return similar[:3]  # Return top 3 matches

def is_ambiguous(item: str) -> bool:
    """Check if an item is too vague or ambiguous"""
    vague_patterns = [
        r'^(fix|update|improve|check|review|look at|work on)\s+(the|a|an)?\s*\w+$',  # "fix bug", "update docs"
        r'^\w+\s+(stuff|thing|issue|problem)$',  # "database stuff", "API thing"
        r'^(follow up|reach out|contact|email)$',  # Missing who/what
        r'^(investigate|research|explore)\s*\w{0,20}$',  # Too broad
    ]
    
    item_lower = item.lower().strip()
    
    # Check if too short
    if len(item_lower.split()) <= 2:
        return True
    
    # Check vague patterns
    for pattern in vague_patterns:
        if re.match(pattern, item_lower):
            return True
    
    return False

def generate_clarification_questions(item: str) -> List[str]:
    """Generate clarification questions for ambiguous items"""
    questions = []
    item_lower = item.lower()
    
    # Technical ambiguity
    if any(word in item_lower for word in ['fix', 'bug', 'error', 'issue']):
        questions.append("Which specific bug or error? Can you provide more details or error messages?")
        questions.append("What component or feature is affected?")
    
    # Scope ambiguity
    if any(word in item_lower for word in ['update', 'improve', 'refactor']):
        questions.append("What specific aspects need updating/improvement?")
        questions.append("What's the success criteria for this task?")
    
    # Missing target
    if any(word in item_lower for word in ['email', 'contact', 'reach out', 'follow up']):
        questions.append("Who should be contacted?")
        questions.append("What's the purpose or goal of this outreach?")
    
    # Missing context
    if any(word in item_lower for word in ['research', 'investigate', 'explore']):
        questions.append("What specific questions need to be answered?")
        questions.append("What decisions will this research inform?")
    
    # Generic catch-all
    if not questions:
        questions.append("Can you provide more specific details about what needs to be done?")
        questions.append("What's the expected outcome or deliverable?")
    
    return questions

def guess_category(item: str) -> str:
    """Guess the category based on item text"""
    item_lower = item.lower()
    
    # Check for category indicators
    if any(word in item_lower for word in ['email', 'contact', 'reach out', 'follow up', 'meeting', 'call']):
        return 'outreach'
    elif any(word in item_lower for word in ['code', 'api', 'database', 'deploy', 'fix', 'bug', 'implement']):
        return 'technical'
    elif any(word in item_lower for word in ['research', 'study', 'learn', 'understand', 'investigate']):
        return 'research'
    elif any(word in item_lower for word in ['write', 'draft', 'document', 'spec', 'article', 'proposal']):
        return 'writing'
    elif any(word in item_lower for word in ['expense', 'invoice', 'schedule', 'calendar', 'organize']):
        return 'admin'
    elif any(word in item_lower for word in ['tweet', 'post', 'linkedin', 'social', 'marketing']):
        return 'outreach'
    else:
        return 'other'

def generate_task_content(item: str, category: str) -> str:
    """Generate rich task content based on item and category"""
    
    # Base structure that all tasks get
    base_content = f"""## Overview
{get_task_overview(item, category)}

## Next Actions
{get_next_actions(item, category)}

## Notes & Details
- Task created from backlog processing
- Category: {category}
"""
    
    # Add category-specific sections
    if category == 'outreach':
        base_content += """
## Draft Message
[Draft outreach message here based on context]

## Contact Details
- LinkedIn profile: [to be added]
- Email: [to be added]
"""
    elif category == 'writing':
        base_content += """
## Key Points
- [Main argument or thesis]
- [Supporting points]
- [Call to action]

## Target Audience
[Define who this is for]

## Resources
- [Related documents or references]
"""
    elif category == 'technical':
        base_content += """
## Technical Requirements
- [Specific technical details]
- [Dependencies or prerequisites]
- [Expected outcome]

## Implementation Notes
- [Technical approach]
- [Testing considerations]
"""
    elif category == 'research':
        base_content += """
## Research Questions
- [What are we trying to learn?]
- [Key hypotheses to test]

## Sources to Explore
- [Relevant resources]
- [People to consult]
"""
    return base_content

def get_task_overview(item: str, category: str) -> str:
    """Generate a contextual overview based on the task"""
    item_lower = item.lower()
    
    # Provide smarter overviews based on keywords
    if 'proposal' in item_lower:
        return f"Create and submit a comprehensive proposal for {item}. Research requirements, draft content, and prepare supporting materials."
    elif 'review' in item_lower:
        return f"Conduct thorough review of {item}. Provide feedback, suggestions, and actionable improvements."
    elif 'follow up' in item_lower or 'reach out' in item_lower:
        return f"Establish or continue communication regarding {item}. Ensure clear next steps and maintain relationship momentum."
    elif 'post' in item_lower or 'write' in item_lower:
        return f"Create compelling content for {item}. Focus on value delivery and audience engagement."
    elif 'implement' in item_lower or 'build' in item_lower:
        return f"Design and implement solution for {item}. Ensure functionality, testing, and documentation."
    else:
        return f"Complete {item} with focus on quality and timeliness."

def get_next_actions(item: str, category: str) -> str:
    """Generate smart next actions based on task type"""
    actions = []
    
    # Universal first steps
    actions.append("- [ ] Review related context and existing work")
    
    # Category-specific actions
    if category == 'outreach':
        actions.extend([
            "- [ ] Research contact's recent activity/interests",
            "- [ ] Draft personalized message",
            "- [ ] Schedule follow-up reminder"
        ])
    elif category == 'writing':
        actions.extend([
            "- [ ] Create outline with key points",
            "- [ ] Write first draft",
            "- [ ] Review and edit for clarity",
            "- [ ] Prepare for publication/submission"
        ])
    elif category == 'technical':
        actions.extend([
            "- [ ] Define technical requirements",
            "- [ ] Set up development environment",
            "- [ ] Implement core functionality",
            "- [ ] Test and validate solution"
        ])
    elif category == 'research':
        actions.extend([
            "- [ ] Define research questions",
            "- [ ] Gather relevant sources",
            "- [ ] Analyze and synthesize findings",
            "- [ ] Document insights and recommendations"
        ])
    else:
        actions.extend([
            "- [ ] Define specific requirements",
            "- [ ] Create action plan",
            "- [ ] Execute plan",
            "- [ ] Verify completion"
        ])
    
    return '\n'.join(actions)

def slugify(title: str) -> str:
    """Lowercase hyphenated slug for a title, or '' when nothing usable survives.

    Returning '' rather than a fallback lets callers reject a title like '!!!' up front.
    Silently naming it untitled-task.md made that name a junk drawer: the first such title
    won it, and every later one was refused with a confusing 'Task already exists'.
    """
    normalized = re.sub(r"[^\w\s-]", "", title).strip().lower()
    return re.sub(r"[-\s]+", "-", normalized).strip("-")

def to_slug_filename(title: str) -> str:
    """Convert a task title into a lowercase hyphenated filename."""
    return f"{slugify(title) or 'untitled-task'}.md"

def render_task_body(title: str, category: str, created_date: str, content: str = "") -> str:
    """Render task markdown using repository task template."""
    context_line = content.strip() if content and content.strip() else "Tie to goals and reference material."
    return (
        f"# {title}\n\n"
        "## Context\n"
        f"{context_line}\n\n"
        "## Next Actions\n"
        "- [ ] Step one\n"
        "- [ ] Step two\n\n"
        "## Progress Log\n"
        f"- {created_date}: Task created via MCP `create_task` ({category}).\n"
    )

def update_file_frontmatter(filepath: Path, updates: dict) -> bool:
    """Update YAML frontmatter in a file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        metadata, body = parse_yaml_frontmatter(content)
        metadata.update(updates)
        
        # Reconstruct file
        yaml_str = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
        # parse_yaml_frontmatter leaves the newlines that followed the closing --- inside
        # body, so appending our own separator to them added one blank line per update,
        # without limit. Strip theirs and write exactly one.
        new_content = f"---\n{yaml_str}---\n\n{body.lstrip(chr(10))}"
        
        with open(filepath, 'w') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        logger.error(f"Error updating {filepath}: {e}")
        return False

# Create the MCP server
app = Server("manager-ai-mcp")

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available tools"""
    return [
        types.Tool(
            name="list_tasks",
            description="List tasks with optional filters (category, priority, status)",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category (comma-separated)"},
                    "priority": {"type": "string", "description": "Filter by priority (comma-separated, e.g., P0,P1)"},
                    "status": {"type": "string", "description": "Filter by status (n,s,b,d)"},
                    "include_done": {"type": "boolean", "description": "Include completed tasks", "default": False}
                }
            }
        ),
        types.Tool(
            name="create_task",
            description="Create a new task",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "category": {"type": "string", "description": "Task category", "default": "other"},
                    "priority": {"type": "string", "description": "Priority (P0-P3)", "default": "P2"},
                    "estimated_time": {"type": "integer", "description": "Estimated time in minutes", "default": 30},
                    "content": {"type": "string", "description": "Task content/description"}
                },
                "required": ["title"]
            }
        ),
        types.Tool(
            name="update_task_status",
            description="Update task status (n=not started, s=started, b=blocked, d=done)",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_file": {"type": "string", "description": "Task filename"},
                    "status": {"type": "string", "description": "New status (n,s,b,d)"}
                },
                "required": ["task_file", "status"]
            }
        ),
        types.Tool(
            name="get_task_summary",
            description="Get summary statistics for all tasks",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="check_priority_limits",
            description="Check if priority limits are exceeded",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="get_system_status",
            description="Get comprehensive system status",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="process_backlog",
            description="Read and return backlog contents",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="clear_backlog",
            description="Clear the backlog after processing",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="prune_completed_tasks",
            description="Delete completed tasks older than specified days",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Days old", "default": 30}
                }
            }
        ),
        types.Tool(
            name="process_backlog_with_dedup",
            description="Process backlog items with duplicate detection and clarification",
            inputSchema={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of backlog items to process"
                    },
                    "auto_create": {
                        "type": "boolean",
                        "description": "Automatically create non-duplicate tasks",
                        "default": False
                    }
                },
                "required": ["items"]
            }
        ),
        # Session Eval Tools
        types.Tool(
            name="list_evals",
            description="List session evaluation files",
            inputSchema={
                "type": "object",
                "properties": {
                    "judgement": {"type": "string", "description": "Filter by judgement (pending,success,partial,failure)"},
                    "limit": {"type": "integer", "description": "Max evals to return", "default": 20}
                }
            }
        ),
        types.Tool(
            name="annotate_eval",
            description="Add judgement and notes to an eval",
            inputSchema={
                "type": "object",
                "properties": {
                    "eval_file": {"type": "string", "description": "Eval filename"},
                    "judgement": {"type": "string", "description": "Judgement (success,partial,failure)"},
                    "annotation": {"type": "string", "description": "Notes"}
                },
                "required": ["eval_file"]
            }
        ),
        types.Tool(
            name="get_eval_summary",
            description="Get summary of all evals",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls"""
    # `is None`, not truthiness: an explicit empty dict means the same as no arguments here,
    # but the required-field checks below are what actually report a missing value.
    if arguments is None:
        arguments = {}

    def _error(message: str) -> list[types.TextContent]:
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": message}, indent=2, cls=DateTimeEncoder),
        )]

    if name == "list_tasks":
        tasks = get_all_tasks()
        
        # Apply filters
        if arguments:
            if not arguments.get('include_done', False):
                tasks = [t for t in tasks if t.get('status') != 'd']
            
            if arguments.get('category'):
                categories = [c.strip() for c in arguments['category'].split(',')]
                tasks = [t for t in tasks if t.get('category') in categories]
            
            if arguments.get('priority'):
                priorities = [p.strip() for p in arguments['priority'].split(',')]
                tasks = [t for t in tasks if t.get('priority') in priorities]
            
            if arguments.get('status'):
                statuses = [s.strip() for s in arguments['status'].split(',')]
                tasks = [t for t in tasks if t.get('status') in statuses]
        else:
            # Default: exclude done tasks
            tasks = [t for t in tasks if t.get('status') != 'd']
        
        result = {
            "tasks": tasks,
            "count": len(tasks),
            "filters_applied": arguments or {}
        }
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]
    
    elif name == "create_task":
        title = str(arguments.get('title') or '').strip()
        if not title:
            return _error("'title' is required and must be non-empty")
        if not slugify(title):
            return _error(f"'title' has no characters usable in a filename: {title!r}")

        category = arguments.get('category', 'other')
        priority = arguments.get('priority', 'P2')
        content = arguments.get('content', '')
        created_date = datetime.now().strftime("%Y-%m-%d")
        if category not in VALID_CATEGORIES:
            category = "other"
        # An unvalidated priority reached the frontmatter verbatim, where check_priority_limits
        # counted it against no threshold and get_task_summary omitted it from every bucket.
        if priority not in VALID_PRIORITIES:
            priority = "P2"
        # A string here crashed get_task_summary's sum() with a TypeError.
        try:
            estimated_time = int(arguments.get('estimated_time', 30))
        except (TypeError, ValueError):
            estimated_time = 30

        # Create filename
        filename = to_slug_filename(title)
        filepath = TASKS_DIR / filename

        # Refusing is the whole fix. Overwriting reset an in-progress task to a blank
        # template while reporting success, and "already exists" is a normal outcome the
        # caller must be able to distinguish from a genuine write failure.
        if filepath.exists():
            result = {
                "success": False,
                "error": f"Task already exists: {filename}",
                "existing_file": filename,
                "hint": "Use update_task_status to change status, or pass a distinct title.",
            }
            return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]
        
        # Create task metadata
        metadata = {
            'title': title,
            'category': category,
            'priority': priority,
            'status': 'n',
            'created_date': created_date,
            'estimated_time': estimated_time
        }
        
        # Create file content
        yaml_str = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
        task_body = render_task_body(title=title, category=category, created_date=created_date, content=content)
        file_content = f"---\n{yaml_str}---\n\n{task_body}"
        
        try:
            with open(filepath, 'w') as f:
                f.write(file_content)
            
            result = {
                "success": True,
                "filename": filename,
                "message": f"Task '{title}' created successfully"
            }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]
    
    elif name == "update_task_status":
        task_file = str(arguments.get('task_file') or '').strip()
        status = str(arguments.get('status') or '').strip()
        if not task_file:
            return _error("'task_file' is required and must be non-empty")
        if not status:
            return _error("'status' is required and must be non-empty")
        
        if not task_file.endswith('.md'):
            task_file += '.md'
        
        filepath = TASKS_DIR / task_file
        if not filepath.exists():
            result = {
                "success": False,
                "error": f"Task file not found: {task_file}"
            }
        else:
            success = update_file_frontmatter(filepath, {'status': status})
            status_names = {'n': 'not started', 's': 'started', 'b': 'blocked', 'd': 'done'}
            result = {
                "success": success,
                "task_file": task_file,
                "new_status": status_names.get(status, status)
            }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]
    
    elif name == "get_task_summary":
        tasks = get_all_tasks()
        active_tasks = [t for t in tasks if t.get('status') != 'd']
        
        by_priority = Counter(t.get('priority', 'P2') for t in active_tasks)
        by_category = Counter(t.get('category', 'other') for t in active_tasks)
        by_status = Counter(t.get('status', 'n') for t in tasks)
        
        # Calculate time estimates
        time_by_priority = {}
        for priority in ['P0', 'P1', 'P2', 'P3']:
            priority_tasks = [t for t in active_tasks if t.get('priority') == priority]
            total_time = sum(t.get('estimated_time', 30) for t in priority_tasks)
            time_by_priority[priority] = {
                'total_minutes': total_time,
                'total_hours': round(total_time / 60, 1)
            }
        
        result = {
            "total_tasks": len(tasks),
            "active_tasks": len(active_tasks),
            "by_priority": dict(by_priority),
            "by_category": dict(by_category),
            "by_status": dict(by_status),
            "time_by_priority": time_by_priority
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]
    
    elif name == "check_priority_limits":
        tasks = [t for t in get_all_tasks() if t.get('status') != 'd']
        by_priority = Counter(t.get('priority', 'P2') for t in tasks)
        
        thresholds = {'P0': 3, 'P1': 5, 'P2': 10}
        alerts = []
        
        for priority, threshold in thresholds.items():
            count = by_priority.get(priority, 0)
            if count > threshold:
                alerts.append(f"{priority} has {count} tasks (limit: {threshold})")
        
        result = {
            "priority_counts": dict(by_priority),
            "alerts": alerts,
            "balanced": len(alerts) == 0
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]

    elif name == "get_system_status":
        all_tasks = get_all_tasks()
        active_tasks = [t for t in all_tasks if t.get('status') != 'd']

        # Direct subscripting took the whole tool down on one task file missing a field.
        # Defaults match get_task_summary above.
        priority_counts = Counter(task.get('priority', 'P2') for task in active_tasks)
        status_counts = Counter(task.get('status', 'n') for task in active_tasks)
        category_counts = Counter(task.get('category', 'other') for task in active_tasks)

        # Check backlog
        backlog_items = 0
        backlog_file = BASE_DIR / 'BACKLOG.md'
        if backlog_file.exists():
            with open(backlog_file, 'r') as f:
                content = f.read().strip()
                if content and content != '# Backlog':
                    backlog_items = len([l for l in content.split('\n') if l.strip().startswith('-')])

        # Time insights
        now = datetime.now()
        hour = now.hour
        day_name = now.strftime('%A')

        time_insights = []
        if 9 <= hour < 12:
            time_insights.append("Early day - ideal for outreach tasks")
        elif 14 <= hour < 17:
            time_insights.append("Afternoon - good for deep work")
        elif hour >= 17:
            time_insights.append("End of day - quick admin tasks")

        result = {
            "total_active_tasks": len(active_tasks),
            "priority_distribution": dict(priority_counts),
            "status_distribution": dict(status_counts),
            "category_distribution": dict(category_counts),
            "backlog_items": backlog_items,
            "time_insights": time_insights,
            "timestamp": now.isoformat()
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]
    
    elif name == "process_backlog":
        backlog_file = BASE_DIR / 'BACKLOG.md'
        
        if not backlog_file.exists():
            result = {
                "success": False,
                "error": "BACKLOG.md not found"
            }
        else:
            with open(backlog_file, 'r') as f:
                content = f.read().strip()
            
            if not content or content == '# Backlog':
                result = {
                    "success": True,
                    "content": None,
                    "message": "Backlog is already clear"
                }
            else:
                # Parse items
                lines = content.split('\n')
                items = []
                current_item = None
                
                for line in lines:
                    stripped = line.strip()
                    if not stripped.startswith('- '):
                        continue
                    # Measure indentation on the raw line; stripped has already lost it
                    indent = len(line) - len(line.lstrip())
                    if indent >= 2 and current_item is not None:
                        current_item['subitems'].append(stripped[2:])
                    else:
                        if current_item:
                            items.append(current_item)
                        current_item = {
                            'text': stripped[2:],
                            'subitems': []
                        }
                
                if current_item:
                    items.append(current_item)
                
                result = {
                    "success": True,
                    "content": content,
                    "parsed_items": items,
                    "count": len(items)
                }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]
    
    elif name == "clear_backlog":
        backlog_file = BASE_DIR / 'BACKLOG.md'
        
        try:
            with open(backlog_file, 'w') as f:
                f.write("# Backlog\n\n")
            
            result = {
                "success": True,
                "message": "Backlog cleared successfully"
            }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]
    
    elif name == "prune_completed_tasks":
        days = arguments.get('days', 30) if arguments else 30
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted = []
        
        for task_file in TASKS_DIR.glob('*.md'):
            try:
                mtime = datetime.fromtimestamp(task_file.stat().st_mtime)
                if mtime < cutoff_date:
                    with open(task_file, 'r') as f:
                        content = f.read()
                        metadata, _ = parse_yaml_frontmatter(content)
                        if metadata.get('status') == 'd':
                            task_file.unlink()
                            deleted.append(task_file.name)
            except Exception as e:
                logger.error(f"Error processing {task_file}: {e}")
        
        result = {
            "success": True,
            "deleted_count": len(deleted),
            "deleted_files": deleted,
            "message": f"Deleted {len(deleted)} tasks older than {days} days"
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]
    
    elif name == "process_backlog_with_dedup":
        items = arguments.get('items', [])
        auto_create = arguments.get('auto_create', False)
        
        if not items:
            return [types.TextContent(type="text", text=json.dumps({
                "error": "No items provided to process"
            }, indent=2, cls=DateTimeEncoder))]

        existing_tasks = get_all_tasks()

        result = {
            "new_tasks": [],
            "potential_duplicates": [],
            "needs_clarification": [],
            "auto_created": [],
            "skipped_existing": [],
            "summary": {}
        }
        
        for item in items:
            # Check for duplicates
            similar_tasks = find_similar_tasks(item, existing_tasks)
            
            if similar_tasks:
                result["potential_duplicates"].append({
                    "item": item,
                    "similar_tasks": similar_tasks,
                    "recommended_action": "merge" if similar_tasks[0]['similarity_score'] > 0.8 else "review"
                })
            elif is_ambiguous(item):
                result["needs_clarification"].append({
                    "item": item,
                    "questions": generate_clarification_questions(item),
                    "suggestions": [
                        "Add more specific details",
                        "Include success criteria",
                        "Specify scope or boundaries"
                    ]
                })
            else:
                # This is a new, clear task
                result["new_tasks"].append({
                    "item": item,
                    "suggested_category": guess_category(item),
                    "suggested_priority": "P2",  # Default priority
                    "ready_to_create": True
                })
                
                # Auto-create if requested
                if auto_create:
                    # Create the task file
                    if not slugify(item):
                        result["skipped_existing"].append(
                            f"<unusable title: {item!r}>")
                        continue
                    safe_filename = to_slug_filename(item)
                    task_file = TASKS_DIR / safe_filename
                    created_date = datetime.now().strftime("%Y-%m-%d")

                    # Same guard as create_task, reported rather than raised: this call
                    # processes a batch, so one collision must not fail the rest.
                    if task_file.exists():
                        result["skipped_existing"].append(safe_filename)
                        continue

                    metadata = {
                        "title": item,
                        "category": guess_category(item),
                        "priority": "P2",
                        "status": "n",
                        "created_date": created_date,
                        "estimated_time": 60
                    }
                    
                    yaml_str = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
                    content = f"---\n{yaml_str}---\n\n{render_task_body(item, metadata['category'], created_date)}"
                    
                    with open(task_file, 'w') as f:
                        f.write(content)
                    
                    result["auto_created"].append(safe_filename)
                    # Without this, existing_tasks stayed frozen at its pre-loop snapshot and
                    # two near-identical items in one batch were both created unflagged.
                    existing_tasks.append({**metadata, "filename": safe_filename, "body_content": ""})
        
        # Add summary
        result["summary"] = {
            "total_items": len(items),
            "new_tasks": len(result["new_tasks"]),
            "duplicates_found": len(result["potential_duplicates"]),
            "needs_clarification": len(result["needs_clarification"]),
            "auto_created": len(result["auto_created"]),
            "skipped_existing": len(result["skipped_existing"]),
            "recommendations": []
        }
        
        # Add recommendations
        if result["potential_duplicates"]:
            result["summary"]["recommendations"].append(
                f"Review {len(result['potential_duplicates'])} potential duplicates before creating tasks"
            )
        
        if result["needs_clarification"]:
            result["summary"]["recommendations"].append(
                f"Clarify {len(result['needs_clarification'])} ambiguous items for better task definition"
            )
        
        if result["new_tasks"] and not auto_create:
            result["summary"]["recommendations"].append(
                f"Ready to create {len(result['new_tasks'])} new tasks - use auto_create=true or create manually"
            )
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]

    elif name == "list_evals":
        limit = arguments.get('limit', 20) if arguments else 20
        judgement_filter = arguments.get('judgement') if arguments else None

        evals = []
        for eval_file in sorted(EVALS_DIR.glob('*.md'), reverse=True):
            if eval_file.name.startswith('_') or eval_file.name == 'README.md':
                continue
            try:
                content = eval_file.read_text()
                metadata, _ = parse_yaml_frontmatter(content)
                if judgement_filter and metadata.get('judgement') != judgement_filter:
                    continue
                timestamp = metadata.get('timestamp', '')
                if hasattr(timestamp, 'isoformat'):
                    timestamp = timestamp.isoformat()
                evals.append({
                    'filename': eval_file.name,
                    'session_id': metadata.get('session_id', ''),
                    'timestamp': str(timestamp),
                    'judgement': metadata.get('judgement', 'pending'),
                    'axial_codes': metadata.get('axial_codes', [])
                })
                if len(evals) >= limit:
                    break
            except Exception as e:
                logger.error(f"Error reading eval {eval_file}: {e}")

        result = {"evals": evals, "count": len(evals)}
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]

    # A generate_eval tool was advertised here and imported trace_parser and trace_to_eval,
    # neither of which exists anywhere in this repository, so every call returned
    # {"success": false, "error": "Trace parser not available"}. Removed rather than left
    # advertised; restoring it means shipping those two modules first.
    elif name == "annotate_eval":
        eval_file = str(arguments.get('eval_file') or '').strip()
        if not eval_file:
            return _error("'eval_file' is required and must be non-empty")
        if not eval_file.endswith('.md'):
            eval_file += '.md'

        filepath = EVALS_DIR / eval_file
        if not filepath.exists():
            result = {"success": False, "error": f"Eval not found: {eval_file}"}
        else:
            updates = {'reviewed': True}
            if arguments.get('judgement'):
                updates['judgement'] = arguments['judgement']
            if arguments.get('annotation'):
                updates['annotation'] = arguments['annotation']

            success = update_file_frontmatter(filepath, updates)
            result = {"success": success, "eval_file": eval_file, "updates": updates}

        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]

    elif name == "get_eval_summary":
        judgement_counts = Counter()
        total = 0

        for eval_file in EVALS_DIR.glob('*.md'):
            if eval_file.name.startswith('_') or eval_file.name == 'README.md':
                continue
            try:
                content = eval_file.read_text()
                metadata, _ = parse_yaml_frontmatter(content)
                total += 1
                judgement_counts[metadata.get('judgement', 'pending')] += 1
            except:
                pass

        result = {
            "total_evals": total,
            "by_judgement": dict(judgement_counts),
            "pending_review": judgement_counts.get('pending', 0)
        }
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, cls=DateTimeEncoder))]

    else:
        return [types.TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

async def main():
    """Main entry point for the MCP server"""
    logger.info(f"Starting Personal OS MCP Server")
    logger.info(f"Working directory: {BASE_DIR}")
    logger.info(f"Tasks directory: {TASKS_DIR}")
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="manager-ai-mcp",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
