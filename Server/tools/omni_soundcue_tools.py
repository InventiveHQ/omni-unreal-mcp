"""
Omni SoundCue Tools — legacy USoundCue asset creation.

MetaSound is the modern path; SoundCue is still common in older projects
and for simple wave-player needs (battle SFX, gunshots, impacts).
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
        logger.error(f"soundcue tool failed: {e}")
        return {"success": False, "error": str(e)}


def register_omni_soundcue_tools(mcp: FastMCP):
    """Register SoundCue creation tools."""

    @mcp.tool()
    def soundcue_create(
        ctx: Context,
        asset_path: str,
        sound_wave_path: str = "",
        volume_multiplier: float = 1.0,
    ) -> Dict[str, Any]:
        """Create a USoundCue, optionally wired to a USoundWave.

        Args:
            asset_path: Where to save (e.g. /Game/Audio/SC_Cannon).
            sound_wave_path: Optional USoundWave to use as the source.
            volume_multiplier: Default volume.
        """
        script = textwrap.dedent(f'''
            import unreal, json, os
            asset_path = {asset_path!r}
            wave_path = {sound_wave_path!r}
            vol = {float(volume_multiplier)}

            pkg_dir = os.path.dirname(asset_path) or "/Game"
            pkg_name = os.path.basename(asset_path)
            tools = unreal.AssetToolsHelpers.get_asset_tools()
            sc = tools.create_asset(pkg_name, pkg_dir,
                                    unreal.SoundCue, unreal.SoundCueFactoryNew())
            if not sc:
                print(json.dumps({{"success": False, "error": "create_asset returned None"}}))
            else:
                sc.set_editor_property("volume_multiplier", vol)
                if wave_path:
                    wave = unreal.load_asset(wave_path)
                    if isinstance(wave, unreal.SoundWave):
                        try:
                            wp_node = sc.construct_sound_node(unreal.SoundNodeWavePlayer)
                            wp_node.set_editor_property("sound_wave", wave)
                            sc.first_node = wp_node
                        except Exception as e:
                            print(json.dumps({{"success": False, "error": f"node wiring failed: {{e}}"}}))
                            raise SystemExit
                unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
                print(json.dumps({{
                    "success": True,
                    "asset": asset_path,
                    "wave": wave_path or None,
                }}))
        ''').strip()
        return _run_python(ctx, script)

    @mcp.tool()
    def soundcue_set_wave(
        ctx: Context,
        soundcue_path: str,
        sound_wave_path: str,
    ) -> Dict[str, Any]:
        """Replace (or set) the WavePlayer node's source wave on an existing SoundCue."""
        script = textwrap.dedent(f'''
            import unreal, json
            sc_path = {soundcue_path!r}
            wave_path = {sound_wave_path!r}
            sc = unreal.load_asset(sc_path)
            wave = unreal.load_asset(wave_path)
            if not isinstance(sc, unreal.SoundCue):
                print(json.dumps({{"success": False, "error": "Not a USoundCue"}}))
            elif not isinstance(wave, unreal.SoundWave):
                print(json.dumps({{"success": False, "error": "Not a USoundWave"}}))
            else:
                root = sc.first_node
                if isinstance(root, unreal.SoundNodeWavePlayer):
                    root.set_editor_property("sound_wave", wave)
                else:
                    wp_node = sc.construct_sound_node(unreal.SoundNodeWavePlayer)
                    wp_node.set_editor_property("sound_wave", wave)
                    sc.first_node = wp_node
                unreal.EditorAssetLibrary.save_asset(sc_path, only_if_is_dirty=False)
                print(json.dumps({{"success": True, "soundcue": sc_path, "wave": wave_path}}))
        ''').strip()
        return _run_python(ctx, script)
