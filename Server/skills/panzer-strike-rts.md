# Panzer Strike RTS — project conventions

## Faction + unit-class tags
- `Faction.Soviet`, `Faction.German`, `Faction.American`
- `UnitClass.Tank.Light` (T-70, M3 Stuart, Pz II)
- `UnitClass.Tank.Medium` (T-34, M4 Sherman, Pz IV)
- `UnitClass.Tank.Heavy` (IS-2, Tiger, Pershing)

Create more with `gameplay_tag_create("Tag.Path", "Comment")`.

## Tank C++ variants
Hand-coded subclasses live in `Source/PanzerStrikeUE/Pawns/TankVariants.cpp`. Planned migration: convert to a DataTable (`omni.datatable.*`) keyed by faction + class for designer-tunable stats.

## Spawn pattern
Tanks ground-snap on spawn via raycast + AABB-bottom alignment — see `PanzerStrikeGameMode::SpawnTankAt`.

## Map
Open-world with World Partition. ~64 LandscapeStreamingProxy cells under a single landscape root. Streaming makes `list_assets` slow without recursive scope.

## Heightmap workflow
`terrain_data(lat, lng, map_size_km)` — fetches Mapzen tiles (no API key). For Mapbox-quality use `import_heightmap_from_coords` after setting `MAPBOX_TOKEN`.
