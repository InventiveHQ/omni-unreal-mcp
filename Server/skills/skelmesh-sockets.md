# Skeletal mesh sockets

Add named attachment points on a `USkeleton` for mounting weapons, VFX, or IK targets. Sockets are the standard way to pin a tank muzzle flash, antenna, hand-held prop, or attachment effect to a specific bone with a relative offset.

## When to use

- Mounting a Niagara muzzle flash at the gun barrel of a tank
- Adding hand-grip sockets on an infantry skeleton
- Defining antenna or aerial attachment points on a vehicle
- Marking IK targets (foot placement, look-at points)

## Important — skeleton, not mesh

Sockets live on the `USkeleton` asset, not the `USkeletalMesh`. Pass the skeleton path (e.g. `/Game/Tanks/Tiger/SK_Tiger_Skeleton`), not the mesh path. A socket added to a skeleton is available on every skeletal mesh that shares it.

## Status — manual step currently required

`USkeleton.Sockets` is a protected UPROPERTY and `USkeletalMeshSocket.SocketName`
is exposed read-only in UE 5.x Python. The MCP tools below will return
`{"success": false, "manual_step_required": true}` until a Phase 4.1 C++
binding lands. Until then, open the skeleton in the editor (Skeleton tab →
right-click bone → Add Socket) and use the example below as a record of intent.

## Tools

- `skelmesh_add_socket(skeleton_path, socket_name, parent_bone, relative_location, relative_rotation, relative_scale)` — blocked, returns manual_step_required
- `skelmesh_list_sockets(skeleton_path)` — blocked, returns manual_step_required
- `skelmesh_remove_socket(skeleton_path, socket_name)` — blocked, returns manual_step_required

## Workflow

1. `skelmesh_list_sockets` to see what's already defined and avoid name collisions.
2. `skelmesh_add_socket` with the parent bone and bone-local TRS.
3. `skelmesh_list_sockets` again to verify the socket landed.
4. In a Blueprint, attach the prop/VFX to the socket via `AttachToComponent` with the socket name.

## Example — Tiger I muzzle flash

```python
# What sockets exist already?
skelmesh_list_sockets("/Game/Tanks/Tiger/SK_Tiger_Skeleton")

# Add a Muzzle socket at the gun barrel bone, 320cm forward
skelmesh_add_socket(
    skeleton_path="/Game/Tanks/Tiger/SK_Tiger_Skeleton",
    socket_name="Muzzle",
    parent_bone="Gun_Barrel",
    relative_location=[320.0, 0.0, 0.0],
    relative_rotation=[0.0, 0.0, 0.0],
    relative_scale=[1.0, 1.0, 1.0],
)

# Verify
skelmesh_list_sockets("/Game/Tanks/Tiger/SK_Tiger_Skeleton")
```

Then in the tank Blueprint, on Fire:

```cpp
UNiagaraFunctionLibrary::SpawnSystemAttached(
    MuzzleFlashFX, SkeletalMeshComp, TEXT("Muzzle"),
    FVector::ZeroVector, FRotator::ZeroRotator,
    EAttachLocation::SnapToTarget, true);
```

## Caveats

- The skeleton `.uasset` is saved on every `add`/`remove`. Review and commit those file changes — they touch shared content.
- Socket names are case-sensitive and must be unique on the skeleton.
- Bone names must match the skeleton's bone hierarchy exactly. Inspect with `unreal.SkeletalMesh.get_skeleton().get_reference_pose()` or in the Skeleton Editor.
- `relative_rotation` is `[pitch, yaw, roll]` (Unreal `FRotator` order), not `[roll, pitch, yaw]`.
