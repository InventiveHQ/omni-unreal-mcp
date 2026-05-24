"""
Omni Struct + Enum Tools — UUserDefinedStruct / UUserDefinedEnum creation.

Editor-only assets. Use for game-config types (ammo, formation, morale state)
that designers should be able to edit without recompiling C++.

NOTE: Asset *creation* works from Python (empty struct, empty enum). Seeding
contents (struct variables, enum entries) requires StructureEditorUtils /
EnumEditorUtils, which are not bound to Python in UE 5.x. Until a Phase 4.1
C++ binding lands, struct_add_variable / enum_add_entry / the seeded-entries
branch of enum_create return ``manual_step_required`` instead of pretending
to succeed.
"""

import logging
import textwrap
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP, Context

_MANUAL_EDITOR_UTILS_STEP = (
    "StructureEditorUtils / EnumEditorUtils are editor-only C++ helpers not "
    "bound to Python in UE 5.x. Open the asset in the editor to add variables/"
    "entries, or wait for the Phase 4.1 C++ binding."
)

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
            var_name: New variable name.
            var_type: One of: bool, int, float, double, string, name, text,
                      vector, rotator, transform. For class refs / structs,
                      pass the full path (e.g. /Game/Foo/SomeAsset.SomeAsset).
        """
        return {
            "success": False,
            "manual_step_required": True,
            "reason": _MANUAL_EDITOR_UTILS_STEP,
            "requested": {"asset": asset_path, "variable": var_name, "type": var_type},
        }

    @mcp.tool()
    def enum_create(
        ctx: Context,
        asset_path: str,
        entries: List[str] = None,
    ) -> Dict[str, Any]:
        """Create a UUserDefinedEnum, optionally seeded with entry names.

        Args:
            asset_path: Enum asset path (e.g. /Game/Combat/E_AmmoType).
            entries: Optional initial entry names (e.g. ["HE", "AP", "HVAP", "HEAT"]).
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
            result["entries_added"] = 0
            result["manual_step_required"] = True
            result["reason"] = _MANUAL_EDITOR_UTILS_STEP
            result["pending_entries"] = list(seeds)
        return result

    @mcp.tool()
    def enum_add_entry(
        ctx: Context,
        asset_path: str,
        entry_name: str,
    ) -> Dict[str, Any]:
        """Add a single entry to an existing UUserDefinedEnum.
        Currently blocked — see module docstring.
        """
        return {
            "success": False,
            "manual_step_required": True,
            "reason": _MANUAL_EDITOR_UTILS_STEP,
            "requested": {"asset": asset_path, "entry": entry_name},
        }
