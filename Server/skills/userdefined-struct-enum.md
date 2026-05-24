# User-Defined Structs + Enums

Create designer-editable enums and structs as content assets — no C++ recompile to add a value.

## When to use

- Ammo types (HE, AP, HEAT...), formation enums, morale states, unit roles
- Damage results, hit info, ability payloads — anything Blueprints need to pass around
- Any gameplay enum/struct a designer might want to extend without a programmer

## C++ vs user-defined

`UENUM` / `USTRUCT` in C++ require a code rebuild to add an entry or field. `UUserDefinedEnum` / `UUserDefinedStruct` live as `/Game/...` assets and edit live in the editor — pick these when iteration speed matters more than runtime polish.

## Status — content seeding is currently a manual step

`StructureEditorUtils` and `EnumEditorUtils` (the C++ helpers that mutate
struct fields / enum entries) are editor-only and not bound to Python in
UE 5.x. Until a Phase 4.1 C++ binding lands:

- `enum_create()` works for creating the empty asset; if you pass `entries`,
  the response includes `manual_step_required: true` and `pending_entries`
  listing what you wanted seeded — paste those into the editor.
- `struct_create()` works for creating the empty asset.
- `enum_add_entry()` / `struct_add_variable()` return `manual_step_required`
  with the requested name in the response, so the AI can prompt the
  designer to add it in the editor.

## Tools

- `enum_create(asset_path, entries)` — creates the asset; seeding returns manual_step_required
- `enum_add_entry(asset_path, entry_name)` — manual_step_required for now
- `struct_create(asset_path)` — creates the asset
- `struct_add_variable(asset_path, var_name, var_type)` — manual_step_required for now

`var_type` accepts: `bool`, `int`, `float`, `double`, `string`, `name`, `text`, `vector`, `rotator`, `transform`.

## Example — ammo enum + damage result struct

```python
# Enum, seeded in one shot
enum_create(
    asset_path="/Game/Combat/E_AmmoType",
    entries=["HE", "AP", "HVAP", "HEAT", "Smoke"],
)

# Add a round we forgot
enum_add_entry("/Game/Combat/E_AmmoType", "APCR")

# Struct, then fields one at a time
struct_create("/Game/Combat/S_DamageResult")
struct_add_variable("/Game/Combat/S_DamageResult", "Damage",     "float")
struct_add_variable("/Game/Combat/S_DamageResult", "Penetrated", "bool")
struct_add_variable("/Game/Combat/S_DamageResult", "HitBone",    "name")
```

## Caveats

- For class refs or nested structs, `var_type` must be the full asset path (e.g. `/Game/Combat/S_DamageResult.S_DamageResult`), not a short name.
- Renaming entries on a `UUserDefinedEnum` after Blueprints reference it can break those references — prefer add-only changes.
- Assets are saved with `only_if_is_dirty=False` so the file always lands on disk.
