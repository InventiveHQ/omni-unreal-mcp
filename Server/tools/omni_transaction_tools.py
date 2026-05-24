"""
Omni Editor Transaction Tools — wrap a script in a single undo transaction.

Important when an AI-driven flow makes many edits in sequence: without a
transaction, the user has to undo each step individually. With one, the
whole block collapses to a single Ctrl-Z.
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
        logger.error(f"transaction tool failed: {e}")
        return {"success": False, "error": str(e)}


def register_omni_transaction_tools(mcp: FastMCP):
    """Register editor transaction tools."""

    @mcp.tool()
    def scoped_transaction(
        ctx: Context,
        description: str,
        python_block: str,
    ) -> Dict[str, Any]:
        """Run a Python block wrapped in a single named editor transaction.
        The whole block collapses to one undo step in the editor's history.

        Args:
            description: Human-readable label shown in the Undo menu.
            python_block: The Python code to run inside the transaction.
                          Use ``unreal`` directly; the wrapper imports it.

        Example:
            scoped_transaction(
                "Spawn tank platoon",
                "for i in range(5): "
                "  unreal.EditorLevelLibrary.spawn_actor_from_class("
                "    unreal.StaticMeshActor, unreal.Vector(i*300, 0, 100), unreal.Rotator())"
            )
        """
        # Indent the user's block by 4 spaces so it sits inside the with-block.
        indented = "\n".join("    " + line for line in python_block.splitlines())
        script = textwrap.dedent(f'''
            import unreal, json
            description = {description!r}
            try:
                with unreal.ScopedEditorTransaction(description):
{indented}
                print(json.dumps({{"success": True, "transaction": description}}))
            except Exception as e:
                print(json.dumps({{"success": False, "error": str(e)}}))
        ''').lstrip()
        return _run_python(ctx, script)
