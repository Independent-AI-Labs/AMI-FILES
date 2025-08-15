"""Git tool definitions for filesystem MCP server."""

from typing import Any


def get_git_tools() -> list[dict[str, Any]]:
    """Get all git-related tool definitions.

    Returns:
        List of git tool definitions
    """
    return [
        {
            "name": "git_stage",
            "description": "Stage files for commit (git add)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File paths to stage (relative to root). Use ['.'] to stage all.",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force add ignored files",
                        "default": False,
                    },
                    "update": {
                        "type": "boolean",
                        "description": "Only update tracked files",
                        "default": False,
                    },
                },
                "required": ["paths"],
            },
        },
        {
            "name": "git_unstage",
            "description": "Unstage files from staging area (git reset HEAD)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File paths to unstage. Empty array unstages all.",
                    },
                },
                "required": ["paths"],
            },
        },
        {
            "name": "git_commit",
            "description": "Create a commit with staged changes",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message",
                    },
                    "amend": {
                        "type": "boolean",
                        "description": "Amend the last commit",
                        "default": False,
                    },
                    "allow_empty": {
                        "type": "boolean",
                        "description": "Allow empty commits",
                        "default": False,
                    },
                    "author": {
                        "type": "string",
                        "description": "Override author (format: 'Name <email>')",
                    },
                },
                "required": ["message"],
            },
        },
        {
            "name": "git_diff",
            "description": "Show differences between files",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific paths to diff. Empty for all changes.",
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "Show staged changes (--cached)",
                        "default": False,
                    },
                    "name_only": {
                        "type": "boolean",
                        "description": "Show only file names",
                        "default": False,
                    },
                    "stat": {
                        "type": "boolean",
                        "description": "Show diffstat instead of patch",
                        "default": False,
                    },
                    "commit": {
                        "type": "string",
                        "description": "Show diff for specific commit",
                    },
                },
            },
        },
        {
            "name": "git_history",
            "description": "Show commit history (git log)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of commits to show",
                        "default": 20,
                    },
                    "oneline": {
                        "type": "boolean",
                        "description": "Show in compact format",
                        "default": True,
                    },
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Show history for specific paths",
                    },
                    "author": {
                        "type": "string",
                        "description": "Filter by author",
                    },
                    "since": {
                        "type": "string",
                        "description": "Show commits since date (e.g., '2 weeks ago')",
                    },
                    "until": {
                        "type": "string",
                        "description": "Show commits until date",
                    },
                    "grep": {
                        "type": "string",
                        "description": "Filter commits by message pattern",
                    },
                },
            },
        },
        {
            "name": "git_restore",
            "description": "Restore working tree files",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File paths to restore",
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "Restore from staging area",
                        "default": False,
                    },
                    "source": {
                        "type": "string",
                        "description": "Restore from specific commit/branch",
                    },
                },
                "required": ["paths"],
            },
        },
        {
            "name": "git_fetch",
            "description": "Fetch updates from remote repository",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "remote": {
                        "type": "string",
                        "description": "Remote name",
                        "default": "origin",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Specific branch to fetch",
                    },
                    "all": {
                        "type": "boolean",
                        "description": "Fetch all remotes",
                        "default": False,
                    },
                    "prune": {
                        "type": "boolean",
                        "description": "Prune deleted remote branches",
                        "default": False,
                    },
                    "tags": {
                        "type": "boolean",
                        "description": "Fetch tags",
                        "default": True,
                    },
                },
            },
        },
        {
            "name": "git_pull",
            "description": "Pull changes from remote repository",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "remote": {
                        "type": "string",
                        "description": "Remote name",
                        "default": "origin",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch to pull from",
                    },
                    "rebase": {
                        "type": "boolean",
                        "description": "Use rebase instead of merge",
                        "default": False,
                    },
                    "ff_only": {
                        "type": "boolean",
                        "description": "Only fast-forward merge",
                        "default": False,
                    },
                    "strategy": {
                        "type": "string",
                        "description": "Merge strategy (e.g., 'ours', 'theirs')",
                    },
                },
            },
        },
        {
            "name": "git_merge_abort",
            "description": "Abort an ongoing merge operation",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "git_push",
            "description": "Push commits to remote repository",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "remote": {
                        "type": "string",
                        "description": "Remote name",
                        "default": "origin",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch to push",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force push (use with caution)",
                        "default": False,
                    },
                    "set_upstream": {
                        "type": "boolean",
                        "description": "Set upstream tracking branch",
                        "default": False,
                    },
                    "tags": {
                        "type": "boolean",
                        "description": "Push tags",
                        "default": False,
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Dry run (show what would be pushed)",
                        "default": False,
                    },
                },
            },
        },
    ]
