"""
Omni DataAsset Tools — create and inspect UDataAsset / UPrimaryDataAsset.

Pairs with omni_datatable_tools — DataAssets are the right choice when
config is structured (nested objects, references) rather than tabular.
"""

import logging
import textwrap
from typing import Dict, Any
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
        logger.error(f"dataasset tool failed: {e}")
        return {"success": False, "error": str(e)}


def register_omni_dataasset_tools(mcp: FastMCP):
    """Register DataAsset creation and property-set tools."""

    @mcp.tool()
    def dataasset_create(
        ctx: Context,
        asset_path: str,
        dataasset_class_path: str,
    ) -> Dict[str, Any]:
        """Create a UDataAsset instance of the given class.

        Args:
            asset_path: Where to save (e.g. /Game/Units/DA_Tiger).
            dataasset_class_path: Class path of a UDataAsset subclass
                (e.g. /Game/Units/BP_TankDataAsset.BP_TankDataAsset_C).
        """
        script = textwrap.dedent(f'''
            import unreal, json, os
            asset_path = {asset_path!r}
            cls_path = {dataasset_class_path!r}

            cls = unreal.load_class(None, cls_path)
            if not cls:
                # Fallback: try as object then static_class
                obj = unreal.load_asset(cls_path)
                cls = obj.get_class() if obj else None
            if not cls:
                print(json.dumps({{"success": False, "error": f"Class not found: {{cls_path}}"}}))
            else:
                pkg_dir = os.path.dirname(asset_path) or "/Game"
                pkg_name = os.path.basename(asset_path)
                tools = unreal.AssetToolsHelpers.get_asset_tools()
                fac = unreal.DataAssetFactory()
                try:
                    fac.set_editor_property("data_asset_class", cls)
                except Exception:
                    pass
                da = tools.create_asset(pkg_name, pkg_dir, cls, fac)
                if not da:
                    print(json.dumps({{"success": False, "error": "create_asset returned None"}}))
                else:
                    unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
                    print(json.dumps({{"success": True, "asset": asset_path, "class": cls_path}}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def dataasset_set_property(
        ctx: Context,
        asset_path: str,
        property_name: str,
        value_json: str,
    ) -> Dict[str, Any]:
        """Set a property on a UDataAsset. value_json is a JSON-encoded primitive
        or list (string, number, bool, list of primitives). For nested struct
        properties, use the DataTable tools instead — they're row-oriented."""
        script = textwrap.dedent(f'''
            import unreal, json
            asset_path = {asset_path!r}
            prop = {property_name!r}
            raw = {value_json!r}

            try:
                value = json.loads(raw)
            except Exception as e:
                print(json.dumps({{"success": False, "error": f"value_json invalid: {{e}}"}}))
            else:
                da = unreal.load_asset(asset_path)
                if not da:
                    print(json.dumps({{"success": False, "error": "Asset not found"}}))
                else:
                    try:
                        da.set_editor_property(prop, value)
                        unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
                        print(json.dumps({{"success": True, "asset": asset_path, "property": prop}}))
                    except Exception as e:
                        print(json.dumps({{"success": False, "error": str(e)}}))
        ''').strip()
        return _run_python(ctx, script)
