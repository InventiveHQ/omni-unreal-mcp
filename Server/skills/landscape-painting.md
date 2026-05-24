# Landscape Painting

Set up paint layers on a Landscape — assign the material, create per-layer `LandscapeLayerInfoObject` assets, and seed a uniform fill. Replaces the hand-rolled `scripts/apply_grass_material.py`.

## When to use

- Standing up a fresh landscape for terrain painting (grass / dirt / snow / mud)
- Swapping the landscape material on an existing terrain
- Doing the initial "fill the whole landscape with grass" pass before designers paint variations

## Tools

- `landscape_list_layers()` — inspect the current landscape material + bound layer infos
- `landscape_assign_material(material_path)` — set the landscape's material slot
- `landscape_create_layer_info(asset_path, is_weight_blended=True)` — create one `ULandscapeLayerInfoObject` per material layer
- `landscape_paint_uniform(layer_info_path, weight=1.0)` — bind the layer info to the landscape so designers can paint it

## Canonical workflow

1. `landscape_assign_material("/Game/Landscape/M_EasternFront")`
2. For each material layer parameter, create a layer info:
   ```
   landscape_create_layer_info("/Game/Landscape/LI_Grass")
   landscape_create_layer_info("/Game/Landscape/LI_Dirt")
   landscape_create_layer_info("/Game/Landscape/LI_Snow")
   ```
3. Seed the base layer:
   ```
   landscape_paint_uniform("/Game/Landscape/LI_Grass", weight=1.0)
   ```
4. Hand off to a designer — they use the editor's **Landscape > Paint** tool to brush dirt/snow over the grass base.

## Caveats

- `landscape_paint_uniform` currently **binds the layer info to the landscape** — actual per-vertex weight painting via Python is limited. For real painting, use the editor's Landscape Paint tool or `BlueprintLandscape` APIs via `execute_python_code`.
- All four tools operate on the **first `ALandscape` actor** in the level. Multi-landscape worlds (rare) need a custom Python script to disambiguate.
- The layer info `asset_path` should live next to the material so `M_EasternFront` and `LI_Grass` stay together for migration.