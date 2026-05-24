# Splines — roads, rivers, paths

Spawn an actor with a `USplineComponent` root and edit its points from MCP. Use for road centerlines, river paths, AI patrol routes, or any curve a designer would otherwise sketch by hand in the editor.

## When to use

- Laying out a road or river through a landscape
- Defining an AI patrol or supply-convoy route
- Authoring a curve as data (length, world points) for gameplay code to sample

## Tools

- `spline_create(actor_name, location, points, closed_loop)` — spawn the actor + spline, optionally seeded with world points
- `spline_add_point(actor_name, world_point, update)` — append one point to an existing spline
- `spline_get_info(actor_name)` — inspect point count, world points, length, closed flag

## Workflow

1. `spline_create` with a handful of seed points (the rough shape).
2. `spline_add_point` for each additional bend.
3. `spline_get_info` to confirm count, length, and the resolved world points.

## Example — 5-segment river

```python
spline_create(
    actor_name="River_Volga_North",
    location=[0, 0, 0],
    points=[
        [0,      0,    100],
        [2000,   500,  100],
        [4500,   200,   90],
        [7000,  -800,   80],
        [9500, -1200,   70],
    ],
    closed_loop=False,
)

# Extend it later
spline_add_point("River_Volga_North", [12000, -2000, 60], update=True)

spline_get_info("River_Volga_North")
# → {"point_count": 6, "length": ..., "points": [...]}
```

## Caveats

- `spline_create` spawns a generic `AActor` with a `USplineComponent` root — there is no visible mesh. To render a road/river, a designer wires a `USplineMeshComponent` (or a PCG graph keyed off the spline) inside the editor. These tools intentionally stop at the spline data.
- Points are added in **world** space; the actor's `location` is just the origin transform.
- Curve interpolation is the default (`add_spline_world_point`'s standard behavior). Change tangent types in the editor if you need linear/constant segments.
