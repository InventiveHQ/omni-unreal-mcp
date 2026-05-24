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
| 🆕 **DataAssets** | done (Phase 4) | fresh impl | `omni_dataasset_tools.py` — `dataasset_create`, `dataasset_set_property`. Python-pure via `unreal.AssetTools.create_asset` + `UDataAssetFactory`. |
| 🆕 **Enum/Struct creation** | done (Phase 4 + Phase 4.1) | fresh impl | `omni_struct_enum_tools.py` + `FUnrealMCPStructEnumCommands`. Creation runs from Python via `unreal.AssetTools.create_asset`. Content seeding (struct vars, enum entries) routes to C++ commands `omni.struct.add_variable`, `omni.enum.add_entry`, `omni.enum.add_entries` that drive `FStructureEditorUtils` / `FEnumEditorUtils`. |
| 🆕 **Landscape painting** | done (Phase 4) | fresh impl | `omni_landscape_paint_tools.py` — `landscape_list_layers`, `landscape_create_layer_info`, `landscape_assign_material`, `landscape_paint_uniform`. Complements the Phase 2.4 heightmap import. |
| 🆕 **Foliage** | done (Phase 4) | fresh impl | `omni_foliage_tools.py` — `foliage_create_type`, `foliage_scatter`, `foliage_set_wind`, `foliage_list_types`, `foliage_clear_instances`. Replaces 7 of the hand-rolled `/scripts/` workarounds. |
| 🆕 **Animation Blueprint** | done (Phase 4 — minimal) | fresh impl | `omni_animbp_tools.py` — `animbp_create`, `animbp_list_for_skeleton`. AnimGraph node-editing deferred to Phase 5. |
| ❌ **AnimSequence / AnimMontage / AnimEditing** | medium | fresh impl | Animation asset ops. |
| 🆕 **Skeleton** | done (Phase 4 + Phase 4.1) | fresh impl | `omni_skelmesh_tools.py` + `FUnrealMCPSkelMeshCommands`. C++ handler mutates `USkeleton::Sockets` directly (Python's read-only `USkeletalMeshSocket.SocketName` UPROPERTY blocked the pure-Python path). Commands: `omni.skelmesh.{add_socket,list_sockets,remove_socket}`. |
| 🆕 **Sound Cues** | done (Phase 4) | fresh impl | `omni_soundcue_tools.py` — `soundcue_create`, `soundcue_set_wave`. Python-pure via `USoundCueFactoryNew`. |
| 🆕 **Splines** | done (Phase 4) | fresh impl | `omni_spline_tools.py` — `spline_create`, `spline_add_point`, `spline_get_info`. Spawns Actor with USplineComponent root, suitable for roads/rivers. |
| 🆕 **Terrain Data (real-world heightmap)** | done (Phase 2.4) | fresh impl | Two-layer: Python (`omni_terrain_tools.py`) does geocoding (OSM Nominatim) + Mapbox Terrain-RGB fetching. C++ (`FUnrealMCPTerrainCommands`) imports the PNG onto a target Landscape via `ULandscapeEditorSubsystem::ImportHeightmapFromFile`. Commands: `omni.terrain.import_heightmap_png`, `omni.terrain.import_heightmap_from_coords`. **Needs editor build to verify.** |
| ❌ **Screenshots** | medium | runreal | Editor viewport capture for visual regression. |
| ❌ **Viewport control** | medium | runreal | Camera-in-editor positioning. |
| ❌ **UV Mapping** | low | fresh impl | UV channel inspection / editing. |
| ❌ **Runtime Virtual Textures** | low | fresh impl | |
| ❌ **PIE Testing** | medium | fresh impl | Programmatic Play-In-Editor start/stop, assertion hooks. |
| ❌ **Engine Settings** | low | fresh impl | Engine-level config (vs project). |
| 🆕 **Editor Transactions** | done (Phase 4) | fresh impl | `omni_transaction_tools.py` — `scoped_transaction(description, python_block)`. Wraps a Python block in a single `unreal.ScopedEditorTransaction`. |

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
Phase 3 (shipped): Lazy-loading meta-tools — `execute_python_code` + 9 others (discovery, asset mgmt, logs, terrain data, research, skills, statetree state-add).
Phase 4 (shipped): 9 domain gap fillers — DataAssets, Enum/Struct, Landscape paint, Foliage, Animation Blueprint (minimal), Skeleton sockets, Sound Cues, Splines, Editor Transactions. Mostly Python-pure via `omni.python.execute`.
Phase 4.1 (shipped): C++ bindings for the two Phase-4 gaps that hit UE 5.x Python limits:
  - `FUnrealMCPSkelMeshCommands` → `omni.skelmesh.{add,list,remove}_socket` — mutates `USkeleton::Sockets` directly.
  - `FUnrealMCPStructEnumCommands` → `omni.struct.add_variable`, `omni.enum.add_entry`, `omni.enum.add_entries` — calls `FStructureEditorUtils::AddVariable`/`RenameVariable` and `FEnumEditorUtils::AddNewEnumeratorForUserDefinedEnum`/`SetEnumeratorDisplayName`.
  Built clean on UE 5.7 macOS arm64 (PanzerStrikeUEEditor target, Development). Python wrappers updated to send the new commands instead of returning `manual_step_required`.
Phase 5 (future): AnimGraph node editing, AnimMontage/Sequence asset ops, Viewport camera control, Screenshots, UV Mapping, RVTs, PIE testing harness.
Phase 4: Animation suite + Sound Cues + UV mapping + PIE testing + Screenshots.
Phase 5: StateTree deep editing (states, transitions, tasks beyond asset creation).
Phase 6: Panzer-Strike composites (platoon spawning, move orders, faction setup).
Phase 7: depth pass on Niagara (currently broken in base).
