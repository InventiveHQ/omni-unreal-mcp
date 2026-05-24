"""
Omni Spline Tools — spline component creation and editing.

Pure-Python via the editor's interpreter. Drives ASplineActor-style actors
spawned with a USplineComponent root, suitable for roads, rivers, paths.
"""

import logging
import textwrap
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def _run_python(ctx: Context, script: str) -> Dict[str, Any]:
    """Send a Python snippet to UE's editor interpreter via omni.python.execute."""
    from unreal_mcp_server import get_unreal_connection
    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "error": "Unreal Engine not connected"}
        response = unreal.send_command("omni.python.execute", {"code": script, "mode": "ExecuteFile"})
        return (response or {}).get("result", response or {"success": False, "error": "No response"})
    except Exception as e:
        logger.error(f"spline tool failed: {e}")
        return {"success": False, "error": str(e)}


def register_omni_spline_tools(mcp: FastMCP):
    """Register spline creation and editing tools with the MCP server."""

    @mcp.tool()
    def spline_create(
        ctx: Context,
        actor_name: str,
        location: List[float] = [0.0, 0.0, 0.0],
        points: List[List[float]] = None,
        closed_loop: bool = False,
    ) -> Dict[str, Any]:
        """Spawn an empty actor with a USplineComponent root, optionally seeded with points.

        Args:
            actor_name: Unique label for the new actor in the level.
            location: World location of the actor's origin.
            points: Optional list of [x,y,z] world points to seed the spline with.
                    Each point becomes a Curve-interpolated key.
            closed_loop: Whether to close the spline into a loop.
        """
        pts_literal = points or []
        script = textwrap.dedent(f'''
            import unreal, json
            actor_name = {actor_name!r}
            location = {list(location)!r}
            points = {pts_literal!r}
            closed = {bool(closed_loop)}

            actor_subsys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            spawned = actor_subsys.spawn_actor_from_class(
                unreal.StaticMeshActor, unreal.Vector(*location), unreal.Rotator(0, 0, 0)
            )
            spawned.set_actor_label(actor_name)

            # AddComponentByClass is the only Python-reachable way to attach a new
            # component to a live actor (add_instance_component isn't exposed).
            spline = spawned.call_method(
                'AddComponentByClass',
                args=(unreal.SplineComponent.static_class(),
                      False, unreal.Transform(), False)
            )
            spline.set_closed_loop(closed)
            spline.clear_spline_points(False)
            for p in points:
                spline.add_spline_point(unreal.Vector(*p), unreal.SplineCoordinateSpace.WORLD)
            spline.update_spline()

            print(json.dumps({{
                "success": True,
                "actor": actor_name,
                "point_count": spline.get_number_of_spline_points(),
                "closed": closed,
            }}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def spline_add_point(
        ctx: Context,
        actor_name: str,
        world_point: List[float],
        update: bool = True,
    ) -> Dict[str, Any]:
        """Append a world-space point to the spline on a previously-created actor."""
        script = textwrap.dedent(f'''
            import unreal, json
            actor_name = {actor_name!r}
            world_point = {list(world_point)!r}
            update = {bool(update)}

            actor_subsys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actors = actor_subsys.get_all_level_actors()
            target = next((a for a in actors if a.get_actor_label() == actor_name), None)
            if not target:
                print(json.dumps({{"success": False, "error": f"Actor {{actor_name!r}} not found"}}))
            else:
                spline = target.get_component_by_class(unreal.SplineComponent)
                if not spline:
                    print(json.dumps({{"success": False, "error": "Actor has no SplineComponent"}}))
                else:
                    spline.add_spline_point(unreal.Vector(*world_point), unreal.SplineCoordinateSpace.WORLD)
                    if update:
                        spline.update_spline()
                    print(json.dumps({{
                        "success": True,
                        "actor": actor_name,
                        "point_count": spline.get_number_of_spline_points(),
                    }}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def spline_get_info(ctx: Context, actor_name: str) -> Dict[str, Any]:
        """Return the spline's points, tangents, and length for a previously-created actor."""
        script = textwrap.dedent(f'''
            import unreal, json
            actor_name = {actor_name!r}

            actor_subsys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actors = actor_subsys.get_all_level_actors()
            target = next((a for a in actors if a.get_actor_label() == actor_name), None)
            if not target:
                print(json.dumps({{"success": False, "error": "Actor not found"}}))
            else:
                spline = target.get_component_by_class(unreal.SplineComponent)
                if not spline:
                    print(json.dumps({{"success": False, "error": "No SplineComponent"}}))
                else:
                    n = spline.get_number_of_spline_points()
                    pts = []
                    for i in range(n):
                        loc = spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
                        pts.append([loc.x, loc.y, loc.z])
                    print(json.dumps({{
                        "success": True,
                        "actor": actor_name,
                        "point_count": n,
                        "points": pts,
                        "length": spline.get_spline_length(),
                        "closed": spline.is_closed_loop(),
                    }}))
        ''').strip()
        return _run_python(ctx, script)
