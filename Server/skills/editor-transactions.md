# Scoped Editor Transactions

Collapse a multi-step Python edit into a single editor Undo entry.

## When to use

- Any AI-driven flow that touches the level more than once (spawn batch, bulk property edit, multi-actor move)
- Without this, a script that spawns 10 actors creates 10 separate undo entries — designers hate it
- Whenever you want the change to show up in Edit > Undo with a meaningful name

## Mental model

Wraps your block in `unreal.ScopedEditorTransaction(description)`. The `description` string is exactly what appears in the editor's Undo menu, so make it human-readable.

## Tool

- `scoped_transaction(description, python_block)`

## Example — spawn a platoon as one undo step

```python
scoped_transaction(
    description="Spawn Soviet armor platoon",
    python_block=(
        "for i in range(5):\n"
        "    unreal.EditorLevelLibrary.spawn_actor_from_class(\n"
        "        unreal.StaticMeshActor, unreal.Vector(i*300, 0, 100), unreal.Rotator())"
    ),
)
```

One entry in the Undo menu: "Spawn Soviet armor platoon". Ctrl-Z removes all five tanks.

## Caveats

- **Indentation:** the wrapper indents your block by 4 spaces to sit inside a `with` block. Write the inner code as if it's at the top level — do not add your own leading indent.
- `unreal` is imported by the wrapper — use it directly inside `python_block`, no `import` needed.
- Not all editor operations participate in undo. Asset creation (`AssetTools.create_asset`, `EditorAssetLibrary.save_asset`) typically does not roll back via Ctrl-Z — use the asset/content-browser tools or accept that those steps are permanent.
- Level-actor operations (spawn, move, delete, property changes) do participate and are the main use case.
