# SoundCue Creation

Wrap a `USoundWave` in a `USoundCue` so it can be played with attenuation, volume control, and spatialization.

## When to use

- Battle SFX, gunshots, impacts, ambient layers — anything that needs more than a raw wave
- You want a one-shot WavePlayer with attenuation/volume, not a full audio graph

## SoundCue vs MetaSound

MetaSound is the modern Unreal audio system (richer DSP, sample-accurate). SoundCue is the older, simpler path — pick it when you just need a WavePlayer wrapper and don't need MetaSound's graph features. Existing Panzer Strike audio is SoundCue-based, so stay consistent unless migrating.

## Tools

- `soundcue_create(asset_path, sound_wave_path, volume_multiplier)` — create a cue, optionally pre-wired to a wave
- `soundcue_set_wave(soundcue_path, sound_wave_path)` — swap the source wave on an existing cue

## Example — Tiger cannon SFX

```python
# Assume /Game/Audio/Tiger_Cannon_Fire is an imported USoundWave
soundcue_create(
    asset_path="/Game/Audio/SC_Tiger_Cannon",
    sound_wave_path="/Game/Audio/Tiger_Cannon_Fire",
    volume_multiplier=1.0,
)

# Later, swap to a punchier recording without recreating the cue
soundcue_set_wave(
    soundcue_path="/Game/Audio/SC_Tiger_Cannon",
    sound_wave_path="/Game/Audio/Tiger_Cannon_Fire_v2",
)
```

## Caveats

- `soundcue_create` only wires a single `SoundNodeWavePlayer` as the root. For multi-node graphs (Random, Mixer, Modulator, Attenuation) drop to `execute_python_code` and call `sc.construct_sound_node(...)` per node, then assign children manually.
- The source path must point to a `USoundWave` — passing another SoundCue or MetaSound will fail the `isinstance` check and return an error.
- Attenuation settings, sound class, and concurrency are not set by this tool — set them in the editor or via `set_editor_property` in a custom Python block.
