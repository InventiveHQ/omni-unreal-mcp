"""
Omni SkeletalMesh Tools — socket and skeleton-asset operations.

Phase 4.1: C++ handler ships in FUnrealMCPSkelMeshCommands. The Python
wrappers now route to omni.skelmesh.{add_socket,list_sockets,remove_socket}.
"""

import logging
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def _send(ctx: Context, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Send a command to the UE C++ bridge and return the unwrapped result."""
    from unreal_mcp_server import get_unreal_connection
    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "error": "Unreal Engine not connected"}
        response = unreal.send_command(name, params)
        return (response or {}).get("result", response or {"success": False, "error": "No response"})
    except Exception as e:
        logger.error(f"skelmesh tool failed: {e}")
        return {"success": False, "error": str(e)}


def register_omni_skelmesh_tools(mcp: FastMCP):
    """Register skeleton socket tools backed by FUnrealMCPSkelMeshCommands."""

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
        return _send(ctx, "omni.skelmesh.add_socket", {
            "skeleton_path": skeleton_path,
            "socket_name": socket_name,
            "parent_bone": parent_bone,
            "relative_location": list(relative_location),
            "relative_rotation": list(relative_rotation),
            "relative_scale": list(relative_scale),
        })

    @mcp.tool()
    def skelmesh_list_sockets(ctx: Context, skeleton_path: str) -> Dict[str, Any]:
        """List sockets on a USkeleton with name + parent bone + offset."""
        return _send(ctx, "omni.skelmesh.list_sockets", {"skeleton_path": skeleton_path})

    @mcp.tool()
    def skelmesh_remove_socket(ctx: Context, skeleton_path: str, socket_name: str) -> Dict[str, Any]:
        """Remove a socket by name from a USkeleton."""
        return _send(ctx, "omni.skelmesh.remove_socket", {
            "skeleton_path": skeleton_path,
            "socket_name": socket_name,
        })
