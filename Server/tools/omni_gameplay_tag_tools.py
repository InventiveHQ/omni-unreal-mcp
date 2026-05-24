"""
Omni Gameplay Tag Tools — create, list, and query GameplayTags.

ATTRIBUTION:
- Fresh implementation. Wraps Unreal's documented `GameplayTagsManager` and
  `UDataTable`-based tag tables. No code copied from other MCP projects.

C++ HANDLER REQUIRED (Phase 2):
- HandleGameplayTagCreate -> UGameplayTagsManager::Get().AddNativeGameplayTag or
                             ini-based tag addition via GameplayTagsSettings
- HandleGameplayTagList   -> UGameplayTagsManager::Get().RequestAllGameplayTags
- HandleGameplayTagQuery  -> UGameplayTagsManager::Get().RequestGameplayTag

Why this matters for Panzer Strike:
- RTS team/faction identity ("Faction.Soviet", "Faction.German")
- Unit class taxonomy ("Unit.Tank.Heavy", "Unit.Tank.Medium")
- Targeting filters ("Targetable.Friendly" vs "Targetable.Hostile")
"""

import logging
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_omni_gameplay_tag_tools(mcp: FastMCP):
    """Register GameplayTag tools with the MCP server."""

    @mcp.tool()
    def gameplay_tag_create(
        ctx: Context,
        tag: str,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new GameplayTag in the project's tag table.

        Args:
            tag:     Hierarchical tag name, e.g. "Faction.Soviet" or
                     "Unit.Tank.Heavy". Dots imply hierarchy.
            comment: Optional editor-visible comment / description.

        UE API: UGameplayTagsManager::AddTagToGameplayTagsList (editor-time)
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}
            response = unreal.send_command(
                "omni.gameplay_tag.create",
                {"tag": tag, "comment": comment or ""},
            )
            return (response or {}).get("result", response or {"success": False, "error": "No response"})
        except Exception as e:
            logger.error(f"gameplay_tag_create failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def gameplay_tag_list(ctx: Context, prefix: Optional[str] = None) -> Dict[str, Any]:
        """List all GameplayTags known to the project, optionally filtered.

        Args:
            prefix: Optional hierarchical prefix filter, e.g. "Faction." to
                    list only faction tags.

        Returns:
            { "tags": List[str], "count": int }

        UE API: UGameplayTagsManager::RequestAllGameplayTags + filter
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}
            response = unreal.send_command(
                "omni.gameplay_tag.list",
                {"prefix": prefix or ""},
            )
            return (response or {}).get("result", response or {"success": False, "error": "No response"})
        except Exception as e:
            logger.error(f"gameplay_tag_list failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def gameplay_tag_query(ctx: Context, tag: str) -> Dict[str, Any]:
        """Check whether a tag exists and return its metadata.

        Returns:
            { "exists": bool, "parents": List[str], "comment": str }

        UE API: UGameplayTagsManager::RequestGameplayTag(name, ErrorIfNotFound=false)
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}
            response = unreal.send_command(
                "omni.gameplay_tag.query",
                {"tag": tag},
            )
            return (response or {}).get("result", response or {"success": False, "error": "No response"})
        except Exception as e:
            logger.error(f"gameplay_tag_query failed: {e}")
            return {"success": False, "error": str(e)}
