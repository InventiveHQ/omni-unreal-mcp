"""
Omni Skills Tool — lazy-loaded markdown skill packs.

Pure-Python. Reads from Plugins/UnrealMCP/Server/skills/ (created on demand).
Each skill is a single .md file or a directory with skill.md + sub-docs.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def _skills_dir() -> Path:
    """Server/skills/, sibling to the tools/ directory."""
    return Path(__file__).resolve().parent.parent / "skills"


def _list_skills() -> List[Dict[str, Any]]:
    base = _skills_dir()
    if not base.exists():
        return []
    entries: List[Dict[str, Any]] = []
    for p in sorted(base.iterdir()):
        if p.is_file() and p.suffix == ".md":
            entries.append({"name": p.stem, "type": "file"})
        elif p.is_dir() and (p / "skill.md").exists():
            sub_docs = sorted(s.stem for s in p.glob("*.md") if s.name != "skill.md")
            entries.append({"name": p.name, "type": "dir", "available_sections": sub_docs})
    return entries


def _load_skill(skill_name: str) -> Optional[Dict[str, Any]]:
    base = _skills_dir()
    # Sub-doc syntax: "skill/section"
    if "/" in skill_name:
        parent, section = skill_name.split("/", 1)
        candidate = base / parent / f"{section}.md"
        if candidate.exists():
            return {"name": skill_name, "content": candidate.read_text(errors="replace")}
        return None
    flat = base / f"{skill_name}.md"
    if flat.exists():
        return {"name": skill_name, "content": flat.read_text(errors="replace")}
    nested = base / skill_name / "skill.md"
    if nested.exists():
        sub_docs = sorted(s.stem for s in (base / skill_name).glob("*.md") if s.name != "skill.md")
        return {"name": skill_name, "content": nested.read_text(errors="replace"), "available_sections": sub_docs}
    return None


def register_omni_skills_tools(mcp: FastMCP):
    """Register manage_skills."""

    @mcp.tool()
    def manage_skills(
        ctx: Context,
        action: str = "list",
        skill_name: str = "",
        skill_names: Optional[List[str]] = None,
        query: str = "",
    ) -> Dict[str, Any]:
        """Lazy-load domain-specific knowledge as markdown skill packs.

        Actions:
            list    — list all available skills
            suggest — rank skills by relevance to `query` (substring match)
            load    — load `skill_name` (or `skill_names` for batch loading)

        Sub-doc syntax: pass "skill/section" (e.g. "blueprints/build-graph").
        """
        try:
            a = action.lower()
            if a == "list":
                skills = _list_skills()
                return {"success": True, "skills": skills, "count": len(skills),
                        "skills_dir": str(_skills_dir())}

            if a == "suggest":
                if not query:
                    return {"success": False, "error": "suggest requires 'query'"}
                q = query.lower()
                skills = _list_skills()
                ranked = [s for s in skills if q in s["name"].lower()]
                return {"success": True, "query": query, "skills": ranked, "count": len(ranked)}

            if a == "load":
                names = list(skill_names or [])
                if skill_name:
                    names.insert(0, skill_name)
                if not names:
                    return {"success": False, "error": "load requires 'skill_name' or 'skill_names'"}
                loaded, missing = [], []
                for n in names:
                    s = _load_skill(n)
                    if s:
                        loaded.append(s)
                    else:
                        missing.append(n)
                return {"success": True, "loaded": loaded, "missing": missing,
                        "loaded_count": len(loaded)}

            return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"manage_skills failed: {e}")
            return {"success": False, "error": str(e)}
