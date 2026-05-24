"""
Omni Asset Management Tool — single entry point for search/open/save/move/...

Multiplexes over existing C++ asset commands (rename_asset, move_asset,
save_asset, save_directory, duplicate_asset, list_assets) so the AI has
one tool instead of seven.
"""

import logging
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_omni_asset_mgmt_tools(mcp: FastMCP):
    """Register manage_asset."""

    @mcp.tool()
    def manage_asset(
        ctx: Context,
        action: str,
        asset_path: str = "",
        source_path: str = "",
        destination_path: str = "",
        search_term: str = "",
        asset_type: str = "",
        directory_path: str = "/Game",
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """Unified asset workflow tool.

        Actions:
            search     — list_assets in directory_path filtered by search_term and asset_type
            open       — open the asset in its editor (for blueprints, materials, etc.)
            save       — save a single asset to disk
            save_all   — save every dirty asset
            move       — move/rename, preserving references (use this for renames)
            duplicate  — copy to a new path (creates a second identity)
            delete     — delete the asset

        Args (per-action):
            search:    search_term, asset_type, directory_path, recursive
            open/save/delete: asset_path
            move/duplicate:   source_path, destination_path
            save_all:  (no args)

        IMPORTANT: prefer `move` over duplicate+delete when the intent is rename.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}

            def send(cmd: str, params: Dict[str, Any]) -> Dict[str, Any]:
                response = unreal.send_command(cmd, params)
                return (response or {}).get("result", response or {"success": False, "error": "No response"})

            a = action.lower()
            if a == "search":
                return send("list_assets", {
                    "directory_path": directory_path,
                    "recursive": recursive,
                    "asset_class": asset_type,
                    "name_pattern": f"*{search_term}*" if search_term else "",
                })
            if a == "open":
                if not asset_path:
                    return {"success": False, "error": "open requires asset_path"}
                return send("open_blueprint", {"name": asset_path})
            if a == "save":
                if not asset_path:
                    return {"success": False, "error": "save requires asset_path"}
                return send("save_asset", {"asset_path": asset_path})
            if a == "save_all":
                return send("save_directory", {"directory_path": "/Game", "recursive": True})
            if a == "move":
                if not source_path or not destination_path:
                    return {"success": False, "error": "move requires source_path and destination_path"}
                return send("move_asset", {"source_path": source_path, "destination_path": destination_path})
            if a == "duplicate":
                if not source_path or not destination_path:
                    return {"success": False, "error": "duplicate requires source_path and destination_path"}
                return send("duplicate_asset", {"source_path": source_path, "destination_path": destination_path})
            if a == "delete":
                if not asset_path:
                    return {"success": False, "error": "delete requires asset_path"}
                # No dedicated C++ delete handler; route via execute_python_code
                # using unreal.EditorAssetLibrary.delete_asset (Python API).
                code = (
                    "import unreal, json\n"
                    f"ok = unreal.EditorAssetLibrary.delete_asset({asset_path!r})\n"
                    f"print(json.dumps({{'deleted': bool(ok), 'asset_path': {asset_path!r}}}))\n"
                )
                return send("omni.python.execute",
                            {"code": code, "mode": "ExecuteFile"})
            return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"manage_asset failed: {e}")
            return {"success": False, "error": str(e)}
