"""
Omni Viewport Tools — editor viewport screenshots and camera control.

PORT ATTRIBUTION:
- `take_screenshot` adapted from runreal/unreal-mcp (MIT License) —
  https://github.com/runreal/unreal-mcp/blob/main/server/editor/scripts/ue_take_screenshot.py
  Original uses unreal.AutomationLibrary.take_high_res_screenshot via Python
  Remote Execution. Reimplemented here to dispatch through the omni-unreal-mcp
  TCP bridge.
- `move_camera` adapted from runreal/unreal-mcp (MIT License) —
  https://github.com/runreal/unreal-mcp/blob/main/server/editor/scripts/ue_move_camera.py

C++ HANDLER REQUIRED (Phase 2):
- HandleTakeScreenshot       -> UAutomationBlueprintFunctionLibrary::TakeHighResScreenshot
- HandleMoveEditorCamera     -> UEditorLevelLibrary::SetLevelViewportCameraInfo
"""

import logging
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_omni_viewport_tools(mcp: FastMCP):
    """Register viewport / screenshot tools with the MCP server."""

    @mcp.tool()
    def take_screenshot(
        ctx: Context,
        width: int = 1920,
        height: int = 1080,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Capture a high-resolution screenshot of the active editor viewport.

        Args:
            width:       Pixel width. Default 1920.
            height:      Pixel height. Default 1080.
            output_path: Optional absolute path for the PNG. If omitted, the
                         editor writes to its default screenshot directory.

        Returns:
            { "success": bool, "path": str, "error": str (optional) }

        UE API: unreal.AutomationLibrary.take_high_res_screenshot(w, h, path)
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}

            response = unreal.send_command(
                "omni.viewport.take_screenshot",
                {"width": width, "height": height, "output_path": output_path or ""},
            )

            if not response:
                return {"success": False, "error": "No response from Unreal"}

            if "result" in response:
                return response["result"]
            return response
        except Exception as e:
            logger.error(f"take_screenshot failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def move_editor_camera(
        ctx: Context,
        location: Dict[str, float],
        rotation: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Position the active editor viewport camera.

        Args:
            location: {"x": float, "y": float, "z": float} world location.
            rotation: Optional {"pitch": float, "yaw": float, "roll": float}.

        UE API: unreal.EditorLevelLibrary.set_level_viewport_camera_info(loc, rot)
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}

            response = unreal.send_command(
                "omni.viewport.move_camera",
                {"location": location, "rotation": rotation or {"pitch": 0, "yaw": 0, "roll": 0}},
            )
            if not response:
                return {"success": False, "error": "No response from Unreal"}
            return response.get("result", response)
        except Exception as e:
            logger.error(f"move_editor_camera failed: {e}")
            return {"success": False, "error": str(e)}
