"""
Omni SkeletalMesh Tools — socket and skeleton-asset operations.

Sockets are used to mount weapons, effects, attachment points on a tank
turret or soldier hand. Sockets live on USkeleton, not USkeletalMesh.
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
        logger.error(f"skelmesh tool failed: {e}")
        return {"success": False, "error": str(e)}


def register_omni_skelmesh_tools(mcp: FastMCP):
    """Register skeleton/skeletal-mesh socket tools."""

    @mcp.tool()
    def skelmesh_add_socket(
        ctx: Context,
        skeleton_path: str,
        socket_name: str,
        parent_bone: str,
        relative_location: List[float] = [0.0, 0.0, 0.0],
        relative_rotation: List[float] = [0.0, 0.0, 0.0],
        relative_scale: List[float] = [1.0, 1.0, 1.0],
    ) -> Dict[str, Any]:
        """Add a named socket on a USkeleton at a given parent bone with relative TRS.

        Args:
            skeleton_path: Content path to the USkeleton (e.g. /Game/Tank/Tiger_Skeleton).
            socket_name: New socket name (must be unique on the skeleton).
            parent_bone: Bone the socket attaches to.
            relative_location: [x,y,z] offset in bone-local space.
            relative_rotation: [pitch,yaw,roll] in bone-local space.
            relative_scale: [x,y,z] scale.
        """
        script = textwrap.dedent(f'''
            import unreal, json
            skeleton_path = {skeleton_path!r}
            socket_name = {socket_name!r}
            parent_bone = {parent_bone!r}
            loc = {list(relative_location)!r}
            rot = {list(relative_rotation)!r}
            scl = {list(relative_scale)!r}

            skel = unreal.load_asset(skeleton_path)
            if not isinstance(skel, unreal.Skeleton):
                print(json.dumps({{"success": False, "error": "Not a USkeleton"}}))
            else:
                socket = unreal.SkeletalMeshSocket(skel)
                socket.socket_name = socket_name
                socket.bone_name = parent_bone
                socket.relative_location = unreal.Vector(*loc)
                socket.relative_rotation = unreal.Rotator(*rot)
                socket.relative_scale = unreal.Vector(*scl)
                sockets = list(skel.sockets) if skel.sockets else []
                sockets.append(socket)
                skel.sockets = sockets
                unreal.EditorAssetLibrary.save_asset(skeleton_path, only_if_is_dirty=False)
                print(json.dumps({{
                    "success": True,
                    "socket": socket_name,
                    "bone": parent_bone,
                    "skeleton": skeleton_path,
                }}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def skelmesh_list_sockets(ctx: Context, skeleton_path: str) -> Dict[str, Any]:
        """List sockets on a USkeleton with name + parent bone + offset."""
        script = textwrap.dedent(f'''
            import unreal, json
            skeleton_path = {skeleton_path!r}
            skel = unreal.load_asset(skeleton_path)
            if not isinstance(skel, unreal.Skeleton):
                print(json.dumps({{"success": False, "error": "Not a USkeleton"}}))
            else:
                out = []
                for s in (skel.sockets or []):
                    loc = s.relative_location
                    out.append({{
                        "name": str(s.socket_name),
                        "bone": str(s.bone_name),
                        "location": [loc.x, loc.y, loc.z],
                    }})
                print(json.dumps({{"success": True, "count": len(out), "sockets": out}}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def skelmesh_remove_socket(ctx: Context, skeleton_path: str, socket_name: str) -> Dict[str, Any]:
        """Remove a socket by name from a USkeleton."""
        script = textwrap.dedent(f'''
            import unreal, json
            skeleton_path = {skeleton_path!r}
            socket_name = {socket_name!r}
            skel = unreal.load_asset(skeleton_path)
            if not isinstance(skel, unreal.Skeleton):
                print(json.dumps({{"success": False, "error": "Not a USkeleton"}}))
            else:
                before = len(skel.sockets or [])
                skel.sockets = [s for s in (skel.sockets or []) if str(s.socket_name) != socket_name]
                after = len(skel.sockets or [])
                unreal.EditorAssetLibrary.save_asset(skeleton_path, only_if_is_dirty=False)
                print(json.dumps({{
                    "success": True,
                    "removed": before - after,
                    "remaining": after,
                }}))
        ''').strip()
        return _run_python(ctx, script)
