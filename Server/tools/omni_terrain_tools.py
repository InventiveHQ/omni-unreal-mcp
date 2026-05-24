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
import ssl
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def _ssl_ctx() -> ssl.SSLContext:
    """macOS Python venvs don't trust the system keychain — point urllib at
    certifi's CA bundle when available, fall back to default otherwise."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


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
            with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx()) as resp:
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

    @mcp.tool()
    def terrain_data(
        ctx: Context,
        lat: float,
        lng: float,
        map_size_km: float = 8.0,
        zoom: int = 12,
        output_path: str = "",
    ) -> Dict[str, Any]:
        """Fetch a real-world heightmap PNG with NO API KEY required.

        Uses Mapzen / AWS-hosted Terrain Tiles (publicly available, no auth):
            s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png

        Terrarium encoding: elev_m = (R*256 + G + B/256) - 32768

        Args:
            lat, lng:     Center coordinates.
            map_size_km:  World size of the area (km). Tactical RTS default 8 km.
            zoom:         Tile zoom level (z=12 → ~10m/px at equator). Higher
                          zoom = more detail but more tiles fetched.
            output_path:  Where to save the assembled PNG. Empty = system temp.

        Returns:
            { success, png_path, elevation_range_m, source }
        """
        import urllib.request, math, tempfile, struct, zlib, io
        try:
            # Lat/lng → tile coords (slippy map / WebMercator)
            def deg2tile(la, lo, z):
                rad = math.radians(la)
                n = 2.0 ** z
                xt = (lo + 180.0) / 360.0 * n
                yt = (1.0 - math.asinh(math.tan(rad)) / math.pi) / 2.0 * n
                return xt, yt

            # Approximate degrees per km at this latitude
            deg_per_km_lat = 1.0 / 111.0
            deg_per_km_lng = 1.0 / (111.0 * math.cos(math.radians(lat)))
            half_lat = (map_size_km / 2.0) * deg_per_km_lat
            half_lng = (map_size_km / 2.0) * deg_per_km_lng

            x_min, y_max = deg2tile(lat - half_lat, lng - half_lng, zoom)
            x_max, y_min = deg2tile(lat + half_lat, lng + half_lng, zoom)
            tx0, tx1 = int(math.floor(x_min)), int(math.ceil(x_max))
            ty0, ty1 = int(math.floor(y_min)), int(math.ceil(y_max))

            TILE_PX = 256
            cols, rows = (tx1 - tx0), (ty1 - ty0)
            if cols <= 0 or rows <= 0:
                return {"success": False, "error": "Zero-tile bounding box; widen map_size_km or zoom"}
            if cols * rows > 64:
                return {"success": False,
                        "error": f"Would fetch {cols*rows} tiles — refusing. Lower zoom or shrink map_size_km."}

            # Assemble an RGB canvas (no alpha) of all tiles
            canvas_w, canvas_h = cols * TILE_PX, rows * TILE_PX
            # Use a flat bytearray, row-major, 3 bytes per pixel
            canvas = bytearray(canvas_w * canvas_h * 3)
            min_elev, max_elev = float("inf"), float("-inf")

            for cx in range(cols):
                for cy in range(rows):
                    tx, ty = tx0 + cx, ty0 + cy
                    url = (f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/"
                           f"{zoom}/{tx}/{ty}.png")
                    req = urllib.request.Request(url, headers={"User-Agent": "omni-unreal-mcp/0.1"})
                    with urllib.request.urlopen(req, timeout=20, context=_ssl_ctx()) as resp:
                        png_bytes = resp.read()

                    # Decode PNG (zlib + minimal IDAT walk). To avoid PIL dep,
                    # parse the PNG ourselves — terrarium tiles are 8-bit RGB(A).
                    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
                        return {"success": False, "error": f"Bad PNG header from tile {tx}/{ty}"}
                    idat = bytearray()
                    width = height = bit_depth = color_type = 0
                    p = 8
                    while p < len(png_bytes):
                        length = int.from_bytes(png_bytes[p:p+4], "big")
                        ctype = png_bytes[p+4:p+8]
                        data = png_bytes[p+8:p+8+length]
                        p += 8 + length + 4
                        if ctype == b"IHDR":
                            width = int.from_bytes(data[0:4], "big")
                            height = int.from_bytes(data[4:8], "big")
                            bit_depth = data[8]
                            color_type = data[9]
                        elif ctype == b"IDAT":
                            idat += data
                        elif ctype == b"IEND":
                            break
                    if bit_depth != 8 or color_type not in (2, 6):  # RGB or RGBA
                        return {"success": False,
                                "error": f"Tile encoding not 8-bit RGB/RGBA ({color_type}/{bit_depth})"}
                    bpp = 3 if color_type == 2 else 4
                    raw = zlib.decompress(bytes(idat))
                    # Defilter scanlines
                    stride = width * bpp
                    pixels = bytearray(stride * height)
                    prev_row = bytearray(stride)
                    src = 0
                    for row in range(height):
                        filt = raw[src]; src += 1
                        line = bytearray(raw[src:src+stride]); src += stride
                        out = bytearray(stride)
                        for i in range(stride):
                            a = out[i-bpp] if i >= bpp else 0
                            b = prev_row[i]
                            c = prev_row[i-bpp] if i >= bpp else 0
                            x = line[i]
                            if filt == 0: out[i] = x
                            elif filt == 1: out[i] = (x + a) & 0xff
                            elif filt == 2: out[i] = (x + b) & 0xff
                            elif filt == 3: out[i] = (x + ((a + b) >> 1)) & 0xff
                            elif filt == 4:
                                pa = abs(b - c); pb = abs(a - c); pc = abs(a + b - 2 * c)
                                if pa <= pb and pa <= pc: pred = a
                                elif pb <= pc: pred = b
                                else: pred = c
                                out[i] = (x + pred) & 0xff
                            else:
                                return {"success": False, "error": f"Unknown filter {filt}"}
                        pixels[row*stride:(row+1)*stride] = out
                        prev_row = out

                    # Blit RGB into canvas + track elevation
                    for ry in range(TILE_PX):
                        for rx in range(TILE_PX):
                            si = (ry * width + rx) * bpp
                            r, g, b = pixels[si], pixels[si+1], pixels[si+2]
                            elev = (r * 256.0 + g + b / 256.0) - 32768.0
                            if elev < min_elev: min_elev = elev
                            if elev > max_elev: max_elev = elev
                            di = ((cy * TILE_PX + ry) * canvas_w + (cx * TILE_PX + rx)) * 3
                            canvas[di] = r; canvas[di+1] = g; canvas[di+2] = b

            # Write canvas as a single PNG
            if not output_path:
                output_path = tempfile.mktemp(suffix="_terrain.png")

            def _u32(v): return v.to_bytes(4, "big")
            def _chunk(tag, data):
                crc = zlib.crc32(tag + data) & 0xffffffff
                return _u32(len(data)) + tag + data + _u32(crc)
            png = bytearray(b"\x89PNG\r\n\x1a\n")
            png += _chunk(b"IHDR",
                _u32(canvas_w) + _u32(canvas_h) + bytes([8, 2, 0, 0, 0]))
            # Build raw scanlines with filter byte 0
            stride = canvas_w * 3
            raw = bytearray()
            for r in range(canvas_h):
                raw.append(0)
                raw += canvas[r*stride:(r+1)*stride]
            png += _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            png += _chunk(b"IEND", b"")
            with open(output_path, "wb") as f:
                f.write(png)

            return {
                "success": True,
                "png_path": output_path,
                "elevation_range_m": [min_elev, max_elev],
                "size_px": [canvas_w, canvas_h],
                "tiles_fetched": cols * rows,
                "zoom": zoom,
                "source": "Mapzen Terrain Tiles (AWS Open Data, no API key)",
            }
        except Exception as e:
            logger.error(f"terrain_data failed: {e}")
            return {"success": False, "error": str(e)}
