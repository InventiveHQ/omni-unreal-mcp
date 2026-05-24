# Foliage — scatter and wind

Create `UFoliageType` assets, scatter instances across a landscape, and tame the wind animation on foliage materials. Replaces the older standalone `panzer-kill-foliage-wind` workflow and the hand-rolled `/scripts/` helpers (`check_foliage`, `disable_wpo_foliage`, `fix_wind`, `kill_wind`, `pin_foliage`, `tame_foliage_wind`, `tune_wind`).

## When to use

- Painting trees/grass/rocks at scale across a landscape
- Killing wind sway for a still-scene screenshot or recorded shot
- Clearing a region of foliage and re-scattering after density tweaks

## Tools

- `foliage_create_type(asset_path, static_mesh_path, density, radius, align_to_normal, random_yaw)` — wrap a `UStaticMesh` in a `UFoliageType_InstancedStaticMesh`
- `foliage_list_types(search_dir)` — inventory existing foliage types under a content path
- `foliage_scatter(foliage_type_path, bounds_min, bounds_max, instance_count, align_to_normal)` — random scatter in an XY box, line-traces down to the landscape surface
- `foliage_set_wind(foliage_type_path, wind_strength, wind_speed)` — override the mesh material's wind scalars
- `foliage_clear_instances(foliage_type_path)` — remove all instances of a type (empty path = wipe everything)

## Workflow

1. `foliage_create_type` to wrap each mesh you want to scatter.
2. `foliage_scatter` into a bounding box — `bounds_min[2]` is the trace-down start height, `bounds_max[2]` is the trace-down floor. Misses (no landscape under the candidate) are skipped, so planted count can be less than requested.
3. `foliage_set_wind(..., 0.0, 0.0)` for a still scene; non-zero values for animated sway.
4. `foliage_clear_instances` if you need to redo a region.

## Example — scatter 500 pines, then kill wind

```python
# 1. Create the foliage type
foliage_create_type(
    asset_path="/Game/Foliage/FT_PineTree",
    static_mesh_path="/Game/Meshes/Trees/SM_Pine_01",
    density=80.0,
    radius=350.0,
    align_to_normal=True,
    random_yaw=True,
)

# 2. Scatter 500 instances in a 2km x 2km box around the origin
foliage_scatter(
    foliage_type_path="/Game/Foliage/FT_PineTree",
    bounds_min=[-100000.0, -100000.0,  5000.0],   # x_min, y_min, trace start (high)
    bounds_max=[ 100000.0,  100000.0, -5000.0],   # x_max, y_max, trace end   (low)
    instance_count=500,
    align_to_normal=True,
)

# 3. Stop the swaying for a still render
foliage_set_wind(
    foliage_type_path="/Game/Foliage/FT_PineTree",
    wind_strength=0.0,
    wind_speed=0.0,
)
```

## Caveats

- **`foliage_set_wind` mutates the base material's scalar defaults**, not a per-foliage MIC. If the pine tree's material is shared with non-foliage assets (rocks, props, hero meshes), those will go still too. Inspect every material touched (`params_overridden` in the result) before committing the `.uasset` changes.
- The tool tries the common scalar names (`WindStrength`, `WindSpeed`, `WindWeight`, `WPOMultiplier`). If the material uses different names, nothing changes — check `params_overridden` in the response; an empty list means no scalars matched.
- `foliage_scatter` uses `TraceTypeQuery1` (Visibility). If the landscape's collision channel isn't on Visibility, traces miss and nothing plants — see the `panzer-fix-landscape-collision` skill.
- `foliage_clear_instances("")` wipes **all** foliage in the level. Pass a specific type path unless you really mean it.
- Instances are added to the current level's `AInstancedFoliageActor`. Save the level (`panzer-save-level`) after a scatter or clear.
