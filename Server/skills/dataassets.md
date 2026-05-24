# DataAssets

Create and populate instances of `UDataAsset` subclasses — the "structured config object" pattern. Use when config has nested objects, soft references, or you want a designer-friendly inspector per item.

## DataAsset vs DataTable

- **DataTable** (`omni.datatable.*`): tabular, one row per item, flat fields. Best for stat sheets, tuning passes, CSV/JSON import.
- **DataAsset** (this skill): one asset per item, can hold complex graphs and references. Best for unit configs, ability definitions, level metadata.

## Tools

- `dataasset_create(asset_path, dataasset_class_path)`
- `dataasset_set_property(asset_path, property_name, value_json)`

## Workflow

1. Define a `UDataAsset` subclass in C++ or as a Blueprint (e.g. `BP_TankConfig` with `FrontArmor`, `AmmoCapacity`, `TurretMesh` fields).
2. Create an instance of it:
   ```
   dataasset_create(
       asset_path="/Game/Units/DA_TigerI",
       dataasset_class_path="/Game/Units/BP_TankConfig.BP_TankConfig_C",
   )
   ```
3. Populate each field — `value_json` is a JSON-encoded value:
   ```
   dataasset_set_property("/Game/Units/DA_TigerI", "FrontArmor", "100.0")
   dataasset_set_property("/Game/Units/DA_TigerI", "AmmoCapacity", "92")
   dataasset_set_property("/Game/Units/DA_TigerI", "CrewNames",
                          '["Commander", "Gunner", "Driver", "Loader", "Radio"]')
   ```

## Class path conventions

- C++ class: `/Script/PanzerStrikeUE.TankConfigDataAsset`
- Blueprint class: `/Game/Units/BP_TankConfig.BP_TankConfig_C` (note the trailing `_C`)

## Caveats

- `value_json` supports **primitives and lists of primitives** (string, number, bool). For nested `USTRUCT` properties or `TSubclassOf` references, fall back to `execute_python_code` — Python's `set_editor_property` handles structs more reliably than round-tripping through JSON.
- `dataasset_create` fails silently if the class path is wrong; verify with `get_asset_info` first.
- Created assets are saved immediately (`only_if_is_dirty=False`) — no extra `save_directory` call needed.