# omni-unreal-mcp roadmap

The goal is **broad, Python-first surface area** (target ~1000+ methods across
~30 service domains) in a single MIT-licensed plugin with no cloud dependency.
The base (`kks3800/Unreal_MCP`) covers 21 domains; this doc tracks what's still
missing and where we'll cobble it from.

## Coverage matrix

Status legend: ✅ Inherited from base · 🟡 Partial · ❌ Gap · 🆕 Cobbled in this repo

### Already covered (inherited from kks3800/Unreal_MCP base)

| Domain | Notes |
|---|---|
| ✅ Asset management | `asset_tools.py` + `UnrealMCPAssetCommands` |
| ✅ Blueprints (full) | base, graphs, multigraph, search, inspect, intelligence |
| ✅ Behavior Trees + Blackboards | `BT*Commands` covers asset, node, structure, runtime |
| ✅ EQS | `eqs_tools.py` |
| ✅ Editor | viewport-level editor ops |
| ✅ Input | base; unclear if legacy or Enhanced Input — needs audit |
| ✅ Materials | graph builder + tools |
| ✅ MetaSounds | metasound_tools |
| 🟡 Niagara | files exist but flagged "not functional yet" in upstream README |
| ✅ PCG | with property marshaler |
| ✅ Project Settings | project_tools |
| ✅ UMG (widgets) | umg_tools |

### Gaps to fill

Each gap lists the **closest MIT/Apache source** if one exists, or marks the
work as fresh-implementation.

| Domain | Priority | Source | Notes |
|---|---|---|---|
| 🆕 **StateTree** | done (Phase 2.3) | fresh impl | `FUnrealMCPStateTreeCommands` registers `omni.statetree.{create_asset,list_assets}`. Uses `UAssetTools::CreateAsset` with `UStateTreeFactory` (resolved dynamically). Asset-level only — deeper state-graph editing is Phase 3 work. **Needs editor build to verify.** |
| 🆕 **GameplayTags** | done (Phase 2.1) | fresh impl | C++ handler `FUnrealMCPGameplayTagCommands` registers `omni.gameplay_tag.{create,list,query}`. Uses `UGameplayTagsManager` + `IGameplayTagsEditorModule::AddNewGameplayTagToINI`. **Needs editor build to verify.** |
| 🆕 **DataTables** | done (Phase 2.2) | fresh impl | `FUnrealMCPDataTableCommands` registers `omni.datatable.{create,add_row,import_csv}`. Uses `UAssetTools::CreateAsset` + `UDataTableFactory` + `FDataTableEditorUtils::AddRow`. **Needs editor build to verify.** |
| ❌ **DataAssets** | medium | fresh impl | Often paired with DataTables. Not yet implemented. |
| ❌ **Enum/Struct creation** | high | fresh impl | Editor-driven creation of `UUserDefinedEnum` / `UUserDefinedStruct`. Not yet implemented. |
| ❌ **Landscape** | high | ChiR24/runreal | Dedicated landscape ops (heightmap import, material assignment, sections). Existing project has hand-rolled scripts; would replace. |
| ❌ **Foliage** | high | ChiR24/runreal | Foliage type creation, scatter, wind ops. |
| ❌ **Animation Blueprint** | medium | fresh impl | AnimBP node graph editing via `UAnimBlueprint` editor APIs. |
| ❌ **AnimSequence / AnimMontage / AnimEditing** | medium | fresh impl | Animation asset ops. |
| ❌ **Skeleton** | medium | fresh impl | Skeleton asset queries / socket creation. |
| ❌ **Sound Cues** | medium | fresh impl | Legacy audio asset support (MetaSound is the modern path). |
| ❌ **Splines** | medium | fresh impl | Spline component editing, useful for rivers/roads (current project has `place_river.py`). |
| 🆕 **Terrain Data (real-world heightmap)** | done (Phase 2.4) | fresh impl | Two-layer: Python (`omni_terrain_tools.py`) does geocoding (OSM Nominatim) + Mapbox Terrain-RGB fetching. C++ (`FUnrealMCPTerrainCommands`) imports the PNG onto a target Landscape via `ULandscapeEditorSubsystem::ImportHeightmapFromFile`. Commands: `omni.terrain.import_heightmap_png`, `omni.terrain.import_heightmap_from_coords`. **Needs editor build to verify.** |
| ❌ **Screenshots** | medium | runreal | Editor viewport capture for visual regression. |
| ❌ **Viewport control** | medium | runreal | Camera-in-editor positioning. |
| ❌ **UV Mapping** | low | fresh impl | UV channel inspection / editing. |
| ❌ **Runtime Virtual Textures** | low | fresh impl | |
| ❌ **PIE Testing** | medium | fresh impl | Programmatic Play-In-Editor start/stop, assertion hooks. |
| ❌ **Engine Settings** | low | fresh impl | Engine-level config (vs project). |
| ❌ **Editor Transactions** | medium | fresh impl | Wrap a block of ops in a single undo transaction. Important for clean editor history. |

### Panzer-Strike-specific composites (not in any upstream)

These are custom commands we'll build for this game:

| Command | Purpose |
|---|---|
| `panzer.spawn_platoon` | Spawn N tanks in formation (wedge / line / column) with team tag |
| `panzer.issue_move_order` | Send selected units to a world location |
| `panzer.import_eastern_front_terrain` | Geocode + heightmap for Kursk/Stalingrad/Bocage/etc. |

## Cobble sources we're authorized to use

See `NOTICE.md` for full attribution. Quick reference:

| Source | License | Use freely? |
|---|---|---|
| `kks3800/Unreal_MCP` | MIT | yes — base |
| `chongdashu/unreal-mcp` | (no LICENSE, inherited via kks3800) | only via the kks3800 fork's lineage |
| `ChiR24/Unreal_mcp` | MIT | yes — preserve copyright |
| `runreal/unreal-mcp` | MIT | yes — preserve copyright |
| `GenOrca/unreal-mcp` | Apache 2.0 | yes — with NOTICE attribution |
| `aadeshrao123/Unreal-MCP` | MPL 2.0 | **no direct copy** — reimplement independently |
| `kvick-games/UnrealMCP` | (no LICENSE) | **no** — all rights reserved |

## Working order

Phase 1 (shipped): scaffold, attribution, roadmap, 5 Python tool stubs.
Phase 1.5 (shipped): vendor-neutral scrub, `Claude/` → `agents/` rename, `DYNAMIC_MODE=1` default.
Phase 2.1 (shipped): GameplayTag C++ handler + duplicate cleanup.
Phase 2.2 (shipped): DataTable C++ handler (RTS tank stats).
Phase 2.3 (shipped): StateTree C++ handler (RTS unit AI — asset-level).
Phase 2.4 (shipped): Terrain heightmap C++ handler (Python fetches Mapbox, C++ imports onto landscape).
Phase 3 (next): DataAssets, Enum/Struct creation, Landscape paint/spline ops, Foliage dedicated handler.
Phase 4: Animation suite + Sound Cues + UV mapping + PIE testing + Screenshots.
Phase 5: StateTree deep editing (states, transitions, tasks beyond asset creation).
Phase 6: Panzer-Strike composites (platoon spawning, move orders, faction setup).
Phase 7: depth pass on Niagara (currently broken in base).
