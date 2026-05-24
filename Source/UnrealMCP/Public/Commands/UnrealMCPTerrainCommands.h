// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#pragma once

#include "CoreMinimal.h"
#include "Json.h"

class FMCPCommandRegistry;

/**
 * Handler class for Terrain / Landscape-related MCP commands.
 *
 * The Python side (Server/tools/omni_terrain_tools.py) handles geocoding and
 * Mapbox Terrain-RGB fetching. This C++ handler takes a heightmap PNG on
 * disk and imports it onto a named Landscape actor in the active level.
 *
 * Command names registered:
 *   omni.terrain.import_heightmap_from_coords  — Python-side fetches the
 *       heightmap from Mapbox, writes the PNG, then sends the path here to
 *       drive the editor import.
 *   omni.terrain.import_heightmap_png          — Direct: take a PNG path
 *       and a landscape actor, do the import.
 */
class UNREALMCP_API FUnrealMCPTerrainCommands
{
public:
    FUnrealMCPTerrainCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);
    void RegisterCommands(FMCPCommandRegistry& Registry);

private:
    /** PNG path + landscape actor label -> apply heights to that landscape. */
    TSharedPtr<FJsonObject> HandleImportHeightmapPNG(const TSharedPtr<FJsonObject>& Params);

    /** Same, but Python pre-validates the heightmap is in the expected format. */
    TSharedPtr<FJsonObject> HandleImportHeightmapFromCoords(const TSharedPtr<FJsonObject>& Params);
};
