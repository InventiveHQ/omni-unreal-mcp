# User-Defined Structs + Enums

Create designer-editable enums and structs as content assets — no C++ recompile to add a value.

## When to use

- Ammo types (HE, AP, HEAT...), formation enums, morale states, unit roles
- Damage results, hit info, ability payloads — anything Blueprints need to pass around
- Any gameplay enum/struct a designer might want to extend without a programmer

## C++ vs user-defined

`UENUM` / `USTRUCT` in C++ require a code rebuild to add an entry or field. `UUserDefinedEnum` / `UUserDefinedStruct` live as `/Game/...` assets and edit live in the editor — pick these when iteration speed matters more than runtime polish.

## Tools

- `enum_create(asset_path, entries)` — create + optionally seed entries
- `enum_add_entry(asset_path, entry_name)` — append one entry later
- `struct_create(asset_path)` — create an empty struct
- `struct_add_variable(asset_path, var_name, var_type)` — append a field

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
