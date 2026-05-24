"""
Omni SkeletalMesh Tools — socket and skeleton-asset operations.

Sockets are used to mount weapons, effects, attachment points on a tank
turret or soldier hand. Sockets live on USkeleton, not USkeletalMesh.

NOTE: USkeleton::Sockets is a protected UPROPERTY in C++ and is not writable
from Python, and USkeletalMeshSocket::SocketName is exposed read-only.
Adding/removing sockets requires either the editor UI or a small C++ binding
(planned Phase 4.1). Until that ships, the add/remove tools return
``manual_step_required`` instead of pretending to succeed.
"""

import logging
import textwrap
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP, Context

_MANUAL_SOCKET_STEP = (
    "USkeleton.Sockets is a protected UPROPERTY and SocketName is read-only "
    "in Python. Open the skeleton in the editor and add the socket manually, "
    "or wait for the Phase 4.1 C++ binding."
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
        return {
            "success": False,
            "manual_step_required": True,
            "reason": _MANUAL_SOCKET_STEP,
            "requested": {
                "skeleton": skeleton_path,
                "socket": socket_name,
                "bone": parent_bone,
            },
        }

    @mcp.tool()
    def skelmesh_list_sockets(ctx: Context, skeleton_path: str) -> Dict[str, Any]:
        """List sockets on a USkeleton with name + parent bone + offset.
        Currently blocked: USkeleton.Sockets is a protected UPROPERTY and isn't
        readable from Python. Returns manual_step_required until Phase 4.1.
        """
        return {
            "success": False,
            "manual_step_required": True,
            "reason": _MANUAL_SOCKET_STEP,
            "requested": {"skeleton": skeleton_path},
        }

    @mcp.tool()
    def skelmesh_remove_socket(ctx: Context, skeleton_path: str, socket_name: str) -> Dict[str, Any]:
        """Remove a socket by name from a USkeleton.
        Currently blocked: same reason as skelmesh_add_socket.
        """
        return {
            "success": False,
            "manual_step_required": True,
            "reason": _MANUAL_SOCKET_STEP,
            "requested": {"skeleton": skeleton_path, "socket": socket_name},
        }
