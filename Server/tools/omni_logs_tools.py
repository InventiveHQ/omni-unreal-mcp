"""
Omni Logs Tool — read and filter Unreal Engine log files.

Pure-Python — no C++ handler required. Walks {project}/Saved/Logs/.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def _project_root() -> Path:
    """Locate the project root by walking up from this file."""
    here = Path(__file__).resolve()
    # tools/ -> Server/ -> UnrealMCP/ -> Plugins/ -> PROJECT/
    for parent in here.parents:
        if (parent / "PanzerStrikeUE.uproject").exists():
            return parent
        if any(parent.glob("*.uproject")):
            return parent
    # Fallback: assume 4-up
    return here.parents[4]


def _logs_dir() -> Path:
    return _project_root() / "Saved" / "Logs"


def _resolve_log(name_or_alias: str) -> Optional[Path]:
    """Map common aliases to actual log file paths."""
    logs = _logs_dir()
    if not logs.exists():
        return None
    aliases = {
        "main": "PanzerStrikeUE.log",
        "system": "PanzerStrikeUE.log",
        "project": "PanzerStrikeUE.log",
    }
    candidate = aliases.get(name_or_alias.lower(), name_or_alias)
    p = logs / candidate
    if p.exists():
        return p
    # Try with .log appended
    p2 = logs / f"{candidate}.log"
    if p2.exists():
        return p2
    return None


def register_omni_logs_tools(mcp: FastMCP):
    """Register read_logs."""

    @mcp.tool()
    def read_logs(
        ctx: Context,
        action: str = "list",
        file: str = "main",
        offset: int = 0,
        limit: int = 2000,
        lines: int = 50,
        pattern: str = "",
        context_lines: int = 0,
        max_matches: int = 100,
        case_sensitive: bool = False,
        last_line: int = 0,
    ) -> Dict[str, Any]:
        """Read and filter UE log files in {project}/Saved/Logs/.

        Actions:
            list      — list available log files
            info      — file size, line count, mtime
            read      — paginated content (offset + limit lines)
            tail      — last N lines
            head      — first N lines
            filter    — regex match with optional context lines
            errors    — convenience: filter for ERROR-ish lines
            warnings  — convenience: filter for WARNING-ish lines
            since     — content after last_line (poll for new entries)

        file: "main" / "system" / "project" alias the project log, otherwise
              the filename in Saved/Logs.
        """
        logs = _logs_dir()

        if action == "list":
            if not logs.exists():
                return {"success": False, "error": f"No logs dir at {logs}"}
            files = []
            for p in sorted(logs.glob("*.log")):
                try:
                    files.append({"file": p.name, "size_bytes": p.stat().st_size})
                except OSError:
                    pass
            return {"success": True, "logs_dir": str(logs), "files": files, "count": len(files)}

        path = _resolve_log(file)
        if not path:
            return {"success": False, "error": f"Log not found: {file} (under {logs})"}

        try:
            text = path.read_text(errors="replace")
        except OSError as e:
            return {"success": False, "error": f"Could not read {path}: {e}"}
        all_lines = text.splitlines()
        total = len(all_lines)

        if action == "info":
            st = path.stat()
            return {
                "success": True, "file": path.name, "path": str(path),
                "size_bytes": st.st_size, "line_count": total, "mtime": st.st_mtime,
            }

        if action == "read":
            chunk = all_lines[offset : offset + limit]
            return {
                "success": True, "file": path.name, "offset": offset,
                "lines_returned": len(chunk), "total_lines": total,
                "content": "\n".join(chunk),
                "next_offset": offset + len(chunk) if offset + len(chunk) < total else None,
            }

        if action == "tail":
            chunk = all_lines[-lines:] if lines > 0 else []
            return {"success": True, "file": path.name, "lines": len(chunk), "content": "\n".join(chunk)}

        if action == "head":
            chunk = all_lines[:lines] if lines > 0 else []
            return {"success": True, "file": path.name, "lines": len(chunk), "content": "\n".join(chunk)}

        if action in ("filter", "errors", "warnings"):
            if action == "errors":
                pattern = pattern or r"\b(Error|ERROR|Fatal|FATAL|Exception|Traceback)\b"
            elif action == "warnings":
                pattern = pattern or r"\b(Warning|WARN)\b"
            if not pattern:
                return {"success": False, "error": "filter action requires 'pattern'"}
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                rx = re.compile(pattern, flags)
            except re.error as e:
                return {"success": False, "error": f"Bad regex: {e}"}

            matches: List[Dict[str, Any]] = []
            for i, line in enumerate(all_lines):
                if rx.search(line):
                    block_start = max(0, i - context_lines)
                    block_end = min(total, i + context_lines + 1)
                    matches.append({
                        "line_no": i + 1,
                        "match": line,
                        "context": all_lines[block_start:block_end] if context_lines else [],
                    })
                    if len(matches) >= max_matches:
                        break
            return {
                "success": True, "file": path.name, "pattern": pattern,
                "matches": matches, "match_count": len(matches),
                "truncated": len(matches) >= max_matches,
            }

        if action == "since":
            if last_line < 0 or last_line >= total:
                return {"success": True, "file": path.name, "new_lines": 0, "total": total, "content": ""}
            chunk = all_lines[last_line:]
            return {
                "success": True, "file": path.name, "from_line": last_line,
                "new_lines": len(chunk), "total": total,
                "content": "\n".join(chunk),
            }

        return {"success": False, "error": f"Unknown action: {action}"}
