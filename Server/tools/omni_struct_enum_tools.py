"""
Omni Struct + Enum Tools — UUserDefinedStruct / UUserDefinedEnum creation
and content seeding.

Asset creation (empty struct, empty enum) runs from Python via
unreal.AssetTools.create_asset. Content seeding (adding variables to a
struct, adding entries to an enum) routes to C++
(FUnrealMCPStructEnumCommands) because StructureEditorUtils /
EnumEditorUtils aren't bound to Python in UE 5.x.
"""

import logging
import textwrap
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def _run_python(ctx: Context, script: str) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "error": "Unreal Engine not connected"}
        response = unreal.send_command("omni.python.execute", {"code": script, "mode": "ExecuteFile"})
        return (response or {}).get("result", response or {"success": False, "error": "No response"})
    except Exception as e:
        logger.error(f"struct/enum tool failed: {e}")
        return {"success": False, "error": str(e)}


def _send(ctx: Context, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "error": "Unreal Engine not connected"}
        response = unreal.send_command(name, params)
        return (response or {}).get("result", response or {"success": False, "error": "No response"})
    except Exception as e:
        logger.error(f"struct/enum command failed: {e}")
        return {"success": False, "error": str(e)}


def register_omni_struct_enum_tools(mcp: FastMCP):
    """Register UUserDefinedStruct + UUserDefinedEnum tools."""

    @mcp.tool()
    def struct_create(
        ctx: Context,
        asset_path: str,
    ) -> Dict[str, Any]:
        """Create an empty UUserDefinedStruct at the content path."""
        script = textwrap.dedent(f'''
            import unreal, json, os
            asset_path = {asset_path!r}
            pkg_dir = os.path.dirname(asset_path) or "/Game"
            pkg_name = os.path.basename(asset_path)
            tools = unreal.AssetToolsHelpers.get_asset_tools()
            s = tools.create_asset(pkg_name, pkg_dir,
                                   unreal.UserDefinedStruct, unreal.StructureFactory())
            if not s:
                print(json.dumps({{"success": False, "error": "create_asset returned None"}}))
            else:
                unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
                print(json.dumps({{"success": True, "asset": asset_path}}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def struct_add_variable(
        ctx: Context,
        asset_path: str,
        var_name: str,
        var_type: str = "float",
    ) -> Dict[str, Any]:
        """Add a variable to a UUserDefinedStruct.

        Args:
            asset_path: Struct asset path.
            var_name: New variable name (becomes the friendly display name).
            var_type: One of: bool, int, int64, float, double, string, name, text,
                      vector, rotator, transform. For enum/struct refs, pass the
                      full asset path (e.g. /Game/Combat/E_AmmoType.E_AmmoType).
        """
        return _send(ctx, "omni.struct.add_variable", {
            "asset_path": asset_path,
            "var_name": var_name,
            "var_type": var_type,
        })

    @mcp.tool()
    def enum_create(
        ctx: Context,
        asset_path: str,
        entries: List[str] = None,
    ) -> Dict[str, Any]:
        """Create a UUserDefinedEnum, optionally seeded with entry names.

        Args:
            asset_path: Enum asset path (e.g. /Game/Combat/E_AmmoType).
            entries: Optional initial entry display names (e.g. ["HE", "AP"]).
        """
        seeds = entries or []
        script = textwrap.dedent(f'''
            import unreal, json, os
            asset_path = {asset_path!r}

            pkg_dir = os.path.dirname(asset_path) or "/Game"
            pkg_name = os.path.basename(asset_path)
            tools = unreal.AssetToolsHelpers.get_asset_tools()
            e = tools.create_asset(pkg_name, pkg_dir,
                                   unreal.UserDefinedEnum, unreal.EnumFactory())
            if not e:
                print(json.dumps({{"success": False, "error": "create_asset returned None"}}))
            else:
                unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
                print(json.dumps({{"success": True, "asset": asset_path}}))
        ''').strip()
        result = _run_python(ctx, script)
        if seeds and result.get("success"):
            seed_result = _send(ctx, "omni.enum.add_entries", {
                "asset_path": asset_path,
                "entries": list(seeds),
            })
            result["entries_added"] = len(seed_result.get("added", []))
            result["entries_skipped"] = seed_result.get("skipped", [])
        return result

    @mcp.tool()
    def enum_add_entry(
        ctx: Context,
        asset_path: str,
        entry_name: str,
    ) -> Dict[str, Any]:
        """Add a single entry to an existing UUserDefinedEnum."""
        return _send(ctx, "omni.enum.add_entry", {
            "asset_path": asset_path,
            "entry_name": entry_name,
        })
