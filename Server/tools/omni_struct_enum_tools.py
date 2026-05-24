"""
Omni Struct + Enum Tools — UUserDefinedStruct / UUserDefinedEnum creation.

Editor-only assets. Use for game-config types (ammo, formation, morale state)
that designers should be able to edit without recompiling C++.
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
        script = textwrap.dedent(f'''
            import unreal, json
            asset_path = {asset_path!r}
            var_name = {var_name!r}
            var_type = {var_type!r}

            s = unreal.load_asset(asset_path)
            if not isinstance(s, unreal.UserDefinedStruct):
                print(json.dumps({{"success": False, "error": "Not a UserDefinedStruct"}}))
            else:
                pin_type_map = {{
                    "bool": (unreal.EdGraphPinType(), "bool"),
                    "int": (unreal.EdGraphPinType(), "int"),
                    "float": (unreal.EdGraphPinType(), "real"),
                    "double": (unreal.EdGraphPinType(), "real"),
                    "string": (unreal.EdGraphPinType(), "string"),
                    "name": (unreal.EdGraphPinType(), "name"),
                    "text": (unreal.EdGraphPinType(), "text"),
                    "vector": (unreal.EdGraphPinType(), "struct"),
                    "rotator": (unreal.EdGraphPinType(), "struct"),
                    "transform": (unreal.EdGraphPinType(), "struct"),
                }}
                pin_type, category = pin_type_map.get(var_type, (unreal.EdGraphPinType(), "real"))
                pin_type.pin_category = category
                try:
                    unreal.StructureEditorUtils.add_variable(s, pin_type, var_name)
                    unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
                    print(json.dumps({{"success": True, "asset": asset_path, "variable": var_name, "type": var_type}}))
                except Exception as e:
                    print(json.dumps({{"success": False, "error": str(e)}}))
        ''').strip()
        return _run_python(ctx, script)

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
            entries = {seeds!r}

            pkg_dir = os.path.dirname(asset_path) or "/Game"
            pkg_name = os.path.basename(asset_path)
            tools = unreal.AssetToolsHelpers.get_asset_tools()
            e = tools.create_asset(pkg_name, pkg_dir,
                                   unreal.UserDefinedEnum, unreal.EnumFactory())
            if not e:
                print(json.dumps({{"success": False, "error": "create_asset returned None"}}))
            else:
                added = 0
                for name in entries:
                    try:
                        unreal.EnumEditorUtils.add_enumerator_for_user_defined_enum(e, name)
                        added += 1
                    except Exception:
                        pass
                unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
                print(json.dumps({{"success": True, "asset": asset_path, "entries_added": added}}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def enum_add_entry(
        ctx: Context,
        asset_path: str,
        entry_name: str,
    ) -> Dict[str, Any]:
        """Add a single entry to an existing UUserDefinedEnum."""
        script = textwrap.dedent(f'''
            import unreal, json
            asset_path = {asset_path!r}
            entry = {entry_name!r}
            e = unreal.load_asset(asset_path)
            if not isinstance(e, unreal.UserDefinedEnum):
                print(json.dumps({{"success": False, "error": "Not a UserDefinedEnum"}}))
            else:
                try:
                    unreal.EnumEditorUtils.add_enumerator_for_user_defined_enum(e, entry)
                    unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
                    print(json.dumps({{"success": True, "asset": asset_path, "entry": entry}}))
                except Exception as ex:
                    print(json.dumps({{"success": False, "error": str(ex)}}))
        ''').strip()
        return _run_python(ctx, script)
