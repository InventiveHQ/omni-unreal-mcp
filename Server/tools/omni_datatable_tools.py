"""
Omni DataTable Tools — create DataTables and add rows.

ATTRIBUTION:
- Fresh implementation. Wraps Unreal's documented `UDataTable`,
  `UUserDefinedStruct`, and `EditorAssetLibrary` APIs. No code copied from
  other MCP projects.

C++ HANDLER REQUIRED (Phase 2):
- HandleDataTableCreate    -> UEditorAssetLibrary::CreateAsset with
                              UDataTable class + RowStruct property
- HandleDataTableAddRow    -> UDataTable::AddRow / UDataTableFunctionLibrary
- HandleDataTableImportCSV -> UDataTableFactory::ImportFromCSV

Why this matters for Panzer Strike:
- Tank stat sheet (armor, gun, range, speed, crew) lives best in a DataTable
  driven by a struct. Avoids hand-coding variants in C++ (current state).
- Same pattern for ammo types, formations, AI personality, mission objectives.
"""

import logging
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_omni_datatable_tools(mcp: FastMCP):
    """Register DataTable tools with the MCP server."""

    @mcp.tool()
    def datatable_create(
        ctx: Context,
        asset_path: str,
        row_struct_path: str,
    ) -> Dict[str, Any]:
        """Create a new empty DataTable asset with the given row struct.

        Args:
            asset_path:      e.g. "/Game/Data/DT_TankStats"
            row_struct_path: Path to a UUserDefinedStruct (or native struct
                             registered with the asset system) that defines
                             the row schema. e.g. "/Game/Data/S_TankStats" or
                             "/Script/PanzerStrikeUE.TankStatsRow".

        Returns:
            { "success": bool, "asset_path": str }
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}
            response = unreal.send_command(
                "omni.datatable.create",
                {"asset_path": asset_path, "row_struct_path": row_struct_path},
            )
            return (response or {}).get("result", response or {"success": False, "error": "No response"})
        except Exception as e:
            logger.error(f"datatable_create failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def datatable_add_row(
        ctx: Context,
        asset_path: str,
        row_name: str,
        row_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add a row to an existing DataTable.

        Args:
            asset_path: DataTable asset path.
            row_name:   Unique row identifier (FName-safe string).
            row_data:   Field-name -> value dict matching the row struct.

        Example (Panzer Strike tank stats):
            datatable_add_row(
                "/Game/Data/DT_TankStats",
                "T34_85",
                {"Armor": 90, "GunMM": 85, "RangeMeters": 800, "SpeedKph": 53, "Crew": 5}
            )
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}
            response = unreal.send_command(
                "omni.datatable.add_row",
                {"asset_path": asset_path, "row_name": row_name, "row_data": row_data},
            )
            return (response or {}).get("result", response or {"success": False, "error": "No response"})
        except Exception as e:
            logger.error(f"datatable_add_row failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def datatable_import_csv(
        ctx: Context,
        asset_path: str,
        csv_path: str,
        row_struct_path: str,
    ) -> Dict[str, Any]:
        """Import a DataTable from a CSV file.

        UE API: UDataTableFactory + UDataTable::CreateTableFromCSVString
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}
            response = unreal.send_command(
                "omni.datatable.import_csv",
                {"asset_path": asset_path, "csv_path": csv_path, "row_struct_path": row_struct_path},
            )
            return (response or {}).get("result", response or {"success": False, "error": "No response"})
        except Exception as e:
            logger.error(f"datatable_import_csv failed: {e}")
            return {"success": False, "error": str(e)}
