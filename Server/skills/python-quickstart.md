# Python Quickstart

Run any code in the editor's Python interpreter via `execute_python_code`. The `unreal` module gives reflection access to nearly every UE API.

## Essentials

```python
import unreal

# Engine + project info
print(unreal.SystemLibrary.get_engine_version())
print(unreal.Paths.project_dir())

# Editor subsystems (preferred over deprecated globals)
les  = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
aes  = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
```

## Common patterns

**Load an asset:**
```python
bp = unreal.EditorAssetLibrary.load_asset("/Game/Blueprints/BP_Player")
```

**Spawn at location:**
```python
loc = unreal.Vector(0, 0, 200)
rot = unreal.Rotator(0, 0, 0)
actor = acts.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
```

**Save dirty assets:**
```python
unreal.EditorAssetLibrary.save_directory("/Game/", recursive=True, only_if_is_dirty=True)
```

## Discovery from inside the editor

- `dir(unreal)` — all symbols
- `help(unreal.LevelEditorSubsystem)` — class help
- Use `discover_python_module / discover_python_class / discover_python_function` MCP tools for filtered, structured output.
