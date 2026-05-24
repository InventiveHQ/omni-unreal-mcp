# NOTICE & Attribution

`omni-unreal-mcp` is built by cobbling together the best parts of multiple
open-source Unreal Engine MCP projects, with the goal of one unified plugin
that covers the full surface area you'd expect (Blueprints, materials,
StateTree, Niagara, UMG, MetaSounds, PCG, Behavior Trees, EQS, terrain,
animation, audio, gameplay tags, data tables, and more).

## Direct source projects

The following projects contributed code that lives in this repo. Their
copyright notices are preserved where we kept their files; this NOTICE
records the lineage.

### Base codebase

- **[kks3800/Unreal_MCP](https://github.com/kks3800/Unreal_MCP)** — MIT License
  - Provides the initial plugin structure, TCP command bridge, and the
    majority of command implementations (Blueprints, Behavior Trees, EQS,
    Niagara, MetaSounds, PCG, Materials, UMG, Input, Project, Editor).
  - kks3800/Unreal_MCP is itself derived from chongdashu/unreal-mcp; we
    inherit that lineage.

- **[chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp)** —
  Original MIT (per upstream README badge and kks3800's NOTICE).
  - Original architecture and earliest command implementations.

### Code we have ported in or referenced

When we copy command implementations from other projects, the source file
keeps its original copyright notice and is listed here.

#### Phase 1 ports (Server/tools/omni_*.py)

- **`omni_viewport_tools.py`** — `take_screenshot` and `move_editor_camera`
  adapted from [runreal/unreal-mcp](https://github.com/runreal/unreal-mcp)
  (MIT). Original used Python Remote Execution; reimplemented here against
  our TCP bridge architecture. Specifically inspired by:
  - `server/editor/scripts/ue_take_screenshot.py`
  - `server/editor/scripts/ue_move_camera.py`

- **`omni_gameplay_tag_tools.py`** — Fresh implementation against
  `UGameplayTagsManager` API. No code copied.

- **`omni_datatable_tools.py`** — Fresh implementation against `UDataTable`
  / `UDataTableFactory` APIs. No code copied.

- **`omni_statetree_tools.py`** — Fresh implementation against `UStateTree`
  / `UStateTreeEditorData` APIs. No code copied.

- **`omni_terrain_tools.py`** — Fresh implementation against public
  Nominatim (OSM) and Mapbox Terrain-RGB APIs. Inspired by VibeUE's
  `terrain_data` workflow concept, but written independently. No code
  copied.

### Projects we have looked at but NOT copied from

Listed for transparency; the surfaces these projects expose may inspire our
own re-implementations (against the public Unreal Engine Python/C++ API,
which is not itself copyrighted).

- **[aadeshrao123/Unreal-MCP](https://github.com/aadeshrao123/Unreal-MCP)** —
  MPL 2.0. We have intentionally not copied code from this project to keep
  the repo cleanly MIT. Any overlap in command coverage (StateTree,
  DataTables, etc.) is independently implemented against UE's documented
  APIs.

- **[kvick-games/UnrealMCP](https://github.com/kvick-games/UnrealMCP)** — No
  LICENSE file in the repo, so all-rights-reserved by default; cannot use.

- **[ChiR24/Unreal_mcp](https://github.com/ChiR24/Unreal_mcp)** — MIT.
  Compatible base; not yet ported from, but allowed.

- **[runreal/unreal-mcp](https://github.com/runreal/unreal-mcp)** — MIT.
  Different architecture (Python Remote Execution rather than C++ plugin
  bridge). Compatible source for ideas; ports would require translation.

- **[GenOrca/unreal-mcp](https://github.com/GenOrca/unreal-mcp)** — Apache
  2.0. Compatible with MIT consumption with attribution.

## Skills / knowledge layer

- **[kevinpbuckley/unreal-engine-skills](https://github.com/kevinpbuckley/unreal-engine-skills)** —
  Used as a reference for correct UE 5.7 C++ patterns. Knowledge — not code
  — informs how we implement commands. Not vendored into this repo.

- **[kevinpbuckley/VibeUE](https://github.com/kevinpbuckley/VibeUE)** —
  Aspirational reference for the full surface area we want to cover (1030
  methods across 30 services). Not copied from; ours is an independent MIT
  implementation.

## Patches and improvements

Bug fixes, command additions, and refactors are tracked in git history. New
files written from scratch by Inventive HQ contributors are © 2026 Inventive
HQ under the MIT License (see `LICENSE`).
