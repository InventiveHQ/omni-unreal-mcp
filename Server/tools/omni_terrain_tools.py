"""
Omni Terrain Tools — real-world heightmap import and geocoding.

ATTRIBUTION:
- Fresh implementation. Inspired by VibeUE's `terrain_data` workflow but
  written from scratch against public APIs (OpenStreetMap Nominatim for
  geocoding, Mapbox Terrain-RGB for elevation). No code copied.
- The set of API calls used (Nominatim, Mapbox) is public and not
  copyrighted; only specific code expression is.

C++ HANDLER REQUIRED (Phase 2):
- HandleTerrainImportHeightmap -> ULandscapeEditorObject + ALandscape::Import
  Pipeline: server-side fetches heightmap PNG, writes to disk, then plugin
  imports it onto a Landscape actor.

Why this matters for Panzer Strike:
- Eastern Front locations (Kursk, Stalingrad, Prokhorovka, Bocage) can be
  imported as accurate terrain from real GPS coordinates.
- Replaces hand-rolled `scripts/restore_heightmap.py` and friends in the
  current Panzer Strike project.

Note: requires MAPBOX_TOKEN env var for elevation tiles. Geocoding via OSM
Nominatim is keyless (subject to their usage policy: 1 req/sec, identify
your User-Agent).
"""

import logging
import os
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_omni_terrain_tools(mcp: FastMCP):
    """Register terrain / geocoding tools with the MCP server."""

    @mcp.tool()
    def geocode_place(ctx: Context, query: str) -> Dict[str, Any]:
        """Convert a place name to (lat, lng) using OpenStreetMap Nominatim.

        Args:
            query: Free-form place name, e.g. "Prokhorovka, Russia" or
                   "Bocage, Normandy, France".

        Returns:
            { "success": bool, "lat": float, "lng": float, "display_name": str }

        Note: Nominatim usage policy requires a unique User-Agent and rate
        limit of 1 req/sec. Don't batch.
        """
        try:
            import urllib.request
            import urllib.parse
            import json

            url = (
                "https://nominatim.openstreetmap.org/search?"
                + urllib.parse.urlencode({"q": query, "format": "json", "limit": 1})
            )
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "omni-unreal-mcp/0.1 (https://github.com/InventiveHQ/omni-unreal-mcp)"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            if not data:
                return {"success": False, "error": "No results"}
            top = data[0]
            return {
                "success": True,
                "lat": float(top["lat"]),
                "lng": float(top["lon"]),
                "display_name": top.get("display_name", ""),
            }
        except Exception as e:
            logger.error(f"geocode_place failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def import_heightmap_from_coords(
        ctx: Context,
        lat: float,
        lng: float,
        landscape_actor: str,
        map_size_km: float = 8.0,
        resolution: int = 1009,
    ) -> Dict[str, Any]:
        """Fetch a real-world heightmap for the given GPS center and import it
        onto an existing Landscape actor.

        Args:
            lat, lng:        Center GPS coordinates.
            landscape_actor: Editor name/label of the target landscape.
            map_size_km:     World size of the area (km). 8 km is typical for
                             a tactical RTS map.
            resolution:      Heightmap pixel resolution (NxN). Must match the
                             landscape's quad resolution (e.g. 1009 for a
                             63x63-quad landscape).

        Returns:
            { "success": bool, "heightmap_path": str, "elevation_range_m": [min, max] }

        Requires MAPBOX_TOKEN env var.
        """
        token = os.environ.get("MAPBOX_TOKEN")
        if not token:
            return {
                "success": False,
                "error": "MAPBOX_TOKEN env var not set. Required for Mapbox Terrain-RGB tiles.",
            }
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}
            response = unreal.send_command(
                "omni.terrain.import_heightmap_from_coords",
                {
                    "lat": lat,
                    "lng": lng,
                    "landscape_actor": landscape_actor,
                    "map_size_km": map_size_km,
                    "resolution": resolution,
                    "mapbox_token": token,
                },
            )
            return (response or {}).get("result", response or {"success": False, "error": "No response"})
        except Exception as e:
            logger.error(f"import_heightmap_from_coords failed: {e}")
            return {"success": False, "error": str(e)}
