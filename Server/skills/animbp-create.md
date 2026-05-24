# Animation Blueprint — create & discover

Stand up a new `UAnimBlueprint` for a freshly-imported skeletal mesh (tank, soldier, helicopter) so a designer can wire the AnimGraph in the editor.

## When to use

- A new skeletal mesh just landed and needs an AnimBP bound to its skeleton
- Auditing which AnimBPs already target a given skeleton (avoid duplicates)
- Bootstrapping a per-unit AnimBP that inherits from a C++ `UAnimInstance` subclass

## Tools

- `animbp_create(asset_path, skeleton_path, parent_class_path="/Script/Engine.AnimInstance")`
- `animbp_list_for_skeleton(skeleton_path)`

## Workflow

1. Confirm the skeleton exists: `load_asset("/Game/Tank/SK_TigerI_Skeleton")`
2. Create the AnimBP bound to it:
   ```
   animbp_create(
       asset_path="/Game/Tank/ABP_TigerI",
       skeleton_path="/Game/Tank/SK_TigerI_Skeleton",
   )
   ```
3. Open the asset in the editor and author the AnimGraph (state machine, blend spaces, etc.) visually.
4. Verify everything bound to that skeleton:
   ```
   animbp_list_for_skeleton("/Game/Tank/SK_TigerI_Skeleton")
   ```

## Inheriting from a custom AnimInstance

If you have a C++ `UTankAnimInstance` that pre-computes speed, turret yaw, etc.:

```
animbp_create(
    asset_path="/Game/Tank/ABP_TigerI",
    skeleton_path="/Game/Tank/SK_TigerI_Skeleton",
    parent_class_path="/Script/PanzerStrikeUE.TankAnimInstance",
)
```

## Caveats

- **Creation + discovery only.** AnimGraph node editing (state machines, blend spaces, transitions) is **not** exposed via MCP yet — that's Phase 5 work. Designers wire the graph visually in the AnimBP editor.
- `parent_class_path` default `/Script/Engine.AnimInstance` produces a "blank" AnimBP. Always pass a project-specific subclass when one exists so the AnimGraph can read C++ properties.
- `asset_path` must not already exist — `create_asset` returns `None` on collision.