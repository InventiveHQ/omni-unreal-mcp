"""
Omni AnimationBlueprint Tools — create AnimBP assets and inspect them.

The AnimGraph node API is specialized and large; we ship the creation +
listing surface so the AI can stand up an AnimBP per character. Node-graph
editing (state machines, blend spaces) is the deeper Phase 5 work — for
now, designers can open the AnimBP in the editor and wire it visually.
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
        logger.error(f"animbp tool failed: {e}")
        return {"success": False, "error": str(e)}


def register_omni_animbp_tools(mcp: FastMCP):
    """Register Animation Blueprint creation + inspection tools."""

    @mcp.tool()
    def animbp_create(
        ctx: Context,
        asset_path: str,
        skeleton_path: str,
        parent_class_path: str = "/Script/Engine.AnimInstance",
    ) -> Dict[str, Any]:
        """Create a UAnimBlueprint for a given skeleton, optionally with a
        custom parent UAnimInstance class.

        Args:
            asset_path: Where to save (e.g. /Game/Tank/ABP_Tiger).
            skeleton_path: USkeleton path the AnimBP will animate.
            parent_class_path: Parent UAnimInstance class. Default = UAnimInstance.
        """
        script = textwrap.dedent(f'''
            import unreal, json, os
            asset_path = {asset_path!r}
            skel_path = {skeleton_path!r}
            parent_class_path = {parent_class_path!r}

            skel = unreal.load_asset(skel_path)
            if not isinstance(skel, unreal.Skeleton):
                print(json.dumps({{"success": False, "error": "skeleton_path not a USkeleton"}}))
            else:
                parent = unreal.load_class(None, parent_class_path) or unreal.AnimInstance
                pkg_dir = os.path.dirname(asset_path) or "/Game"
                pkg_name = os.path.basename(asset_path)
                tools = unreal.AssetToolsHelpers.get_asset_tools()
                fac = unreal.AnimBlueprintFactory()
                fac.set_editor_property("target_skeleton", skel)
                try:
                    fac.set_editor_property("parent_class", parent)
                except Exception:
                    pass
                abp = tools.create_asset(pkg_name, pkg_dir, unreal.AnimBlueprint, fac)
                if not abp:
                    print(json.dumps({{"success": False, "error": "create_asset returned None"}}))
                else:
                    unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
                    print(json.dumps({{
                        "success": True,
                        "asset": asset_path,
                        "skeleton": skel_path,
                        "parent_class": parent_class_path,
                    }}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def animbp_list_for_skeleton(ctx: Context, skeleton_path: str) -> Dict[str, Any]:
        """List all AnimBlueprints targeting a specific USkeleton."""
        script = textwrap.dedent(f'''
            import unreal, json
            skel_path = {skeleton_path!r}
            reg = unreal.AssetRegistryHelpers.get_asset_registry()
            assets = reg.get_assets_by_class("AnimBlueprint", search_sub_classes=True)
            out = []
            for a in assets:
                obj = a.get_asset()
                tgt = obj.get_editor_property("target_skeleton") if obj else None
                if tgt and tgt.get_path_name() == skel_path:
                    out.append(str(a.package_name))
            print(json.dumps({{"success": True, "count": len(out), "anim_blueprints": out}}))
        ''').strip()
        return _run_python(ctx, script)
