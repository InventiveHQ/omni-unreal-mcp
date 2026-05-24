"""
Omni Foliage Tools — foliage type creation, scatter, and wind control.

Replaces hand-rolled /scripts/ workarounds (check_foliage, disable_wpo_foliage,
fix_wind, kill_wind, pin_foliage, tame_foliage_wind, tune_wind).
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
        logger.error(f"foliage tool failed: {e}")
        return {"success": False, "error": str(e)}


def register_omni_foliage_tools(mcp: FastMCP):
    """Register foliage type, scatter, and wind tools."""

    @mcp.tool()
    def foliage_create_type(
        ctx: Context,
        asset_path: str,
        static_mesh_path: str,
        density: float = 100.0,
        radius: float = 200.0,
        align_to_normal: bool = True,
        random_yaw: bool = True,
    ) -> Dict[str, Any]:
        """Create a UFoliageType_InstancedStaticMesh asset that wraps a mesh.

        Args:
            asset_path: Where to save the foliage type (e.g. /Game/Foliage/FT_Pine).
            static_mesh_path: The mesh this type instances.
            density: Painted density (instances per 1000sq cm).
            radius: Minimum spacing radius between instances.
            align_to_normal: Rotate each instance to match the surface normal.
            random_yaw: Randomize yaw per instance.
        """
        script = textwrap.dedent(f'''
            import unreal, json, os
            asset_path = {asset_path!r}
            mesh_path = {static_mesh_path!r}
            density = {float(density)}
            radius = {float(radius)}
            align_normal = {bool(align_to_normal)}
            random_yaw = {bool(random_yaw)}

            mesh = unreal.load_asset(mesh_path)
            if not isinstance(mesh, unreal.StaticMesh):
                print(json.dumps({{"success": False, "error": "static_mesh_path is not a UStaticMesh"}}))
            else:
                pkg_dir = os.path.dirname(asset_path).replace("/Game", "/Game") or "/Game"
                pkg_name = os.path.basename(asset_path)
                tools = unreal.AssetToolsHelpers.get_asset_tools()
                ft = tools.create_asset(pkg_name, pkg_dir,
                                        unreal.FoliageType_InstancedStaticMesh,
                                        unreal.FoliageType_InstancedStaticMeshFactory())
                ft.set_editor_property("mesh", mesh)
                ft.set_editor_property("density", density)
                ft.set_editor_property("radius", radius)
                ft.set_editor_property("align_to_normal", align_normal)
                ft.set_editor_property("random_yaw", random_yaw)
                unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
                print(json.dumps({{"success": True, "asset": asset_path, "mesh": mesh_path}}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def foliage_list_types(ctx: Context, search_dir: str = "/Game") -> Dict[str, Any]:
        """List all UFoliageType assets in a content directory."""
        script = textwrap.dedent(f'''
            import unreal, json
            search_dir = {search_dir!r}
            reg = unreal.AssetRegistryHelpers.get_asset_registry()
            assets = reg.get_assets_by_path(search_dir, recursive=True)
            out = []
            for a in assets:
                cls = str(a.asset_class_path.asset_name) if hasattr(a, "asset_class_path") else str(a.asset_class)
                if "FoliageType" in cls:
                    out.append({{"path": str(a.package_name), "class": cls}})
            print(json.dumps({{"success": True, "count": len(out), "types": out}}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def foliage_set_wind(
        ctx: Context,
        foliage_type_path: str,
        wind_strength: float = 0.0,
        wind_speed: float = 0.0,
    ) -> Dict[str, Any]:
        """Tame or kill wind on a foliage type by overriding its mesh material's
        wind scalar parameters. Targets the common params (WindStrength, WindSpeed,
        and a few WPO knobs). Use 0.0/0.0 for the still-scene preset.

        Note: actual parameter names depend on the source material. We try the
        common conventions (WindStrength, WindSpeed, WindWeight, WPOMultiplier).
        """
        script = textwrap.dedent(f'''
            import unreal, json
            ft_path = {foliage_type_path!r}
            wind_strength = {float(wind_strength)}
            wind_speed = {float(wind_speed)}

            ft = unreal.load_asset(ft_path)
            mesh = ft.get_editor_property("mesh") if ft else None
            if not mesh:
                print(json.dumps({{"success": False, "error": "FoliageType has no mesh"}}))
            else:
                touched = []
                materials = mesh.get_editor_property("static_materials") or []
                for slot in materials:
                    mat = slot.material_interface
                    if not mat: continue
                    target = mat
                    if isinstance(mat, unreal.MaterialInstance):
                        target = mat
                    for pname, pval in [("WindStrength", wind_strength),
                                        ("WindSpeed", wind_speed),
                                        ("WindWeight", wind_strength),
                                        ("WPOMultiplier", wind_strength)]:
                        try:
                            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                                target, pname, pval
                            )
                            touched.append(pname)
                        except Exception:
                            pass
                if touched:
                    for slot in materials:
                        if slot.material_interface:
                            unreal.EditorAssetLibrary.save_asset(slot.material_interface.get_path_name(),
                                                                  only_if_is_dirty=False)
                print(json.dumps({{
                    "success": True,
                    "foliage_type": ft_path,
                    "params_overridden": touched,
                    "strength": wind_strength,
                    "speed": wind_speed,
                }}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def foliage_scatter(
        ctx: Context,
        foliage_type_path: str,
        bounds_min: List[float],
        bounds_max: List[float],
        instance_count: int = 100,
        align_to_normal: bool = True,
    ) -> Dict[str, Any]:
        """Scatter instances of a foliage type randomly within an XY-bounding box.
        Each candidate position is traced down to find the landscape surface;
        misses are skipped (so the actual planted count may be < instance_count).

        Args:
            foliage_type_path: A UFoliageType asset.
            bounds_min: [x_min, y_min, z_top] — z_top is the trace-down start height.
            bounds_max: [x_max, y_max, z_bottom] — z_bottom is the trace-down end height.
            instance_count: How many candidate positions to attempt.
            align_to_normal: Orient each instance to the surface normal.
        """
        script = textwrap.dedent(f'''
            import unreal, json, random
            ft_path = {foliage_type_path!r}
            bmin = {list(bounds_min)!r}
            bmax = {list(bounds_max)!r}
            count = {int(instance_count)}
            align_normal = {bool(align_to_normal)}

            ft = unreal.load_asset(ft_path)
            if not ft:
                print(json.dumps({{"success": False, "error": "FoliageType not found"}}))
            else:
                world = unreal.EditorLevelLibrary.get_editor_world()
                iv = unreal.InstancedFoliageActor.get_instanced_foliage_actor_for_current_level(world)
                planted = 0
                for _ in range(count):
                    x = random.uniform(bmin[0], bmax[0])
                    y = random.uniform(bmin[1], bmax[1])
                    start = unreal.Vector(x, y, bmin[2])
                    end = unreal.Vector(x, y, bmax[2])
                    hit = unreal.SystemLibrary.line_trace_single(
                        world, start, end,
                        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                        False, [], unreal.DrawDebugTrace.NONE, True
                    )
                    if hit:
                        loc = hit.to_tuple()[4] if isinstance(hit, tuple) else hit
                        try:
                            t = unreal.Transform(unreal.Vector(x, y, getattr(loc, 'z', bmin[2])),
                                                 unreal.Rotator(0, random.uniform(0, 360), 0),
                                                 unreal.Vector(1, 1, 1))
                            iv.add_instance(ft, t)
                            planted += 1
                        except Exception:
                            pass
                print(json.dumps({{"success": True, "planted": planted, "attempted": count}}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def foliage_clear_instances(
        ctx: Context,
        foliage_type_path: str = "",
    ) -> Dict[str, Any]:
        """Clear all instances of a foliage type from the current level. Empty
        type path clears ALL foliage in the level (use with care)."""
        script = textwrap.dedent(f'''
            import unreal, json
            ft_path = {foliage_type_path!r}
            world = unreal.EditorLevelLibrary.get_editor_world()
            iv = unreal.InstancedFoliageActor.get_instanced_foliage_actor_for_current_level(world)
            if not iv:
                print(json.dumps({{"success": True, "removed": 0, "note": "No foliage actor in level"}}))
            else:
                removed = 0
                if ft_path:
                    ft = unreal.load_asset(ft_path)
                    if ft and iv.contains_instances_of_type(ft):
                        before = iv.get_instance_count(ft)
                        iv.remove_all_instances(ft)
                        removed = before
                else:
                    for ft in list(iv.get_foliage_types_in_level()):
                        before = iv.get_instance_count(ft)
                        iv.remove_all_instances(ft)
                        removed += before
                print(json.dumps({{"success": True, "removed": removed}}))
        ''').strip()
        return _run_python(ctx, script)
