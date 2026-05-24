"""
Omni StateTree Tools — modern UE AI behavior (UE 5.x StateTree).

ATTRIBUTION:
- Fresh implementation. Wraps the documented `UStateTree` editor APIs. No
  code copied from other MCP projects.
- StateTree is UE's newer behavior framework (complements / partially replaces
  Behavior Trees). The base plugin already supports Behavior Trees; this fills
  the modern-AI gap.

C++ HANDLER REQUIRED (Phase 2):
- HandleStateTreeCreateAsset -> UAssetTools::CreateAsset with UStateTree class
- HandleStateTreeAddState    -> UStateTreeEditorData::AddState
- HandleStateTreeAddTask     -> UStateTreeEditorData attached tasks

Why this matters for Panzer Strike:
- RTS unit AI: idle -> seek -> engage -> retreat states with transitions
  driven by tags ("Targetable.Hostile" in range, ammo low, etc.).
- StateTree composes better than BT for unit-level decision logic.
- Pair with `omni_gameplay_tag_tools` for tag-driven transitions.
"""

import logging
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_omni_statetree_tools(mcp: FastMCP):
    """Register StateTree tools with the MCP server."""

    @mcp.tool()
    def statetree_create_asset(
        ctx: Context,
        asset_path: str,
        schema_class: str = "/Script/StateTreeModule.StateTreeComponentSchema",
    ) -> Dict[str, Any]:
        """Create a new empty StateTree asset.

        Args:
            asset_path:   e.g. "/Game/AI/ST_TankUnit"
            schema_class: Object path of the StateTree schema class. The
                          default is the component schema used for actor-
                          attached StateTreeComponents.

        UE API: UAssetTools::CreateAsset(name, path, UStateTree::StaticClass(), Factory)
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}
            response = unreal.send_command(
                "omni.statetree.create_asset",
                {"asset_path": asset_path, "schema_class": schema_class},
            )
            return (response or {}).get("result", response or {"success": False, "error": "No response"})
        except Exception as e:
            logger.error(f"statetree_create_asset failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def statetree_add_state(
        ctx: Context,
        asset_path: str,
        state_name: str,
        parent_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a state node to a StateTree, optionally under a parent.

        Args:
            asset_path:   StateTree asset path.
            state_name:   New state name (e.g. "Idle", "Engage").
            parent_state: Parent state name; None means top-level.

        UE API: UStateTreeEditorData::AddState
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}
            response = unreal.send_command(
                "omni.statetree.add_state",
                {
                    "asset_path": asset_path,
                    "state_name": state_name,
                    "parent_state": parent_state or "",
                },
            )
            return (response or {}).get("result", response or {"success": False, "error": "No response"})
        except Exception as e:
            logger.error(f"statetree_add_state failed: {e}")
            return {"success": False, "error": str(e)}
