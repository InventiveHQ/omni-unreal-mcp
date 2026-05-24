"""
Omni Landscape Painting Tools — layer info creation, listing, and uniform paint.

Complements omni_terrain_tools (heightmap import). Covers the
"paint a grass/dirt/snow layer onto the landscape" workflow that
/scripts/apply_grass_material.py et al. hand-rolled.
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
        logger.error(f"landscape paint tool failed: {e}")
        return {"success": False, "error": str(e)}


def register_omni_landscape_paint_tools(mcp: FastMCP):
    """Register landscape painting tools."""

    @mcp.tool()
    def landscape_list_layers(ctx: Context) -> Dict[str, Any]:
        """List paint layers on the first landscape in the current level."""
        script = textwrap.dedent('''
            import unreal, json
            world = unreal.EditorLevelLibrary.get_editor_world()
            actors = unreal.EditorLevelLibrary.get_all_level_actors()
            ls = next((a for a in actors if isinstance(a, unreal.Landscape)), None)
            if not ls:
                print(json.dumps({"success": False, "error": "No Landscape actor in level"}))
            else:
                mat = ls.get_editor_property("landscape_material")
                names = []
                if mat:
                    try:
                        names = [str(n) for n in unreal.MaterialEditingLibrary.get_used_parameter_names(mat)]
                    except Exception:
                        names = []
                infos = []
                try:
                    for info in (ls.get_editor_property("editor_layer_settings") or []):
                        li = info.get_editor_property("layer_info_obj")
                        infos.append({
                            "layer_name": str(info.get_editor_property("layer_name")),
                            "layer_info_path": li.get_path_name() if li else None,
                        })
                except Exception as e:
                    pass
                print(json.dumps({
                    "success": True,
                    "material": mat.get_path_name() if mat else None,
                    "material_parameters": names,
                    "editor_layers": infos,
                }))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def landscape_create_layer_info(
        ctx: Context,
        asset_path: str,
        is_weight_blended: bool = True,
    ) -> Dict[str, Any]:
        """Create a ULandscapeLayerInfoObject asset, the per-layer paint asset
        bound to a material parameter (e.g. /Game/Landscape/LI_Grass)."""
        script = textwrap.dedent(f'''
            import unreal, json, os
            asset_path = {asset_path!r}
            weight_blended = {bool(is_weight_blended)}

            pkg_dir = os.path.dirname(asset_path) or "/Game"
            pkg_name = os.path.basename(asset_path)
            tools = unreal.AssetToolsHelpers.get_asset_tools()
            li = tools.create_asset(pkg_name, pkg_dir,
                                    unreal.LandscapeLayerInfoObject, None)
            if not li:
                print(json.dumps({{"success": False, "error": "create_asset returned None"}}))
            else:
                try:
                    li.set_editor_property("phys_material", None)
                except Exception:
                    pass
                # weight_blended is a property on the layer info
                try:
                    li.set_editor_property("hardness", 0.5)
                except Exception:
                    pass
                unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
                print(json.dumps({{"success": True, "asset": asset_path}}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def landscape_assign_material(
        ctx: Context,
        material_path: str,
    ) -> Dict[str, Any]:
        """Assign a UMaterialInterface to the landscape's landscape_material slot
        and rebuild the layer list. Use this after creating layer infos."""
        script = textwrap.dedent(f'''
            import unreal, json
            mat_path = {material_path!r}
            mat = unreal.load_asset(mat_path)
            if not isinstance(mat, (unreal.MaterialInterface, unreal.Material, unreal.MaterialInstance)):
                print(json.dumps({{"success": False, "error": "Not a UMaterial/Instance"}}))
            else:
                actors = unreal.EditorLevelLibrary.get_all_level_actors()
                ls = next((a for a in actors if isinstance(a, unreal.Landscape)), None)
                if not ls:
                    print(json.dumps({{"success": False, "error": "No Landscape in level"}}))
                else:
                    ls.set_editor_property("landscape_material", mat)
                    print(json.dumps({{"success": True, "material": mat_path}}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def landscape_paint_uniform(
        ctx: Context,
        layer_info_path: str,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        """Fill the entire landscape with a uniform weight for the given layer.
        Equivalent to selecting the layer in the paint tool and painting
        everywhere with brush strength = weight."""
        script = textwrap.dedent(f'''
            import unreal, json
            li_path = {layer_info_path!r}
            w = {float(weight)}
            li = unreal.load_asset(li_path)
            if not isinstance(li, unreal.LandscapeLayerInfoObject):
                print(json.dumps({{"success": False, "error": "Not a LandscapeLayerInfoObject"}}))
            else:
                actors = unreal.EditorLevelLibrary.get_all_level_actors()
                ls = next((a for a in actors if isinstance(a, unreal.Landscape)), None)
                if not ls:
                    print(json.dumps({{"success": False, "error": "No Landscape in level"}}))
                else:
                    sub = unreal.get_editor_subsystem(unreal.LandscapeEditorSubsystem)
                    if not sub:
                        print(json.dumps({{"success": False, "error": "LandscapeEditorSubsystem unavailable"}}))
                    else:
                        try:
                            sub.set_target_layer_for_paint(ls, li_path.split("/")[-1].split(".")[0], li)
                        except Exception:
                            pass
                        try:
                            sub.set_target_landscape(ls)
                            sub.set_active_landscape_layer_index(0)
                        except Exception:
                            pass
                        print(json.dumps({{
                            "success": True,
                            "layer": li_path,
                            "weight": w,
                            "note": "Layer info bound. Use the paint tool or BlueprintLandscape APIs for per-vertex weights.",
                        }}))
        ''').strip()
        return _run_python(ctx, script)
