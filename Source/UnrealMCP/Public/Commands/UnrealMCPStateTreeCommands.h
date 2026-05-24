// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#pragma once

#include "CoreMinimal.h"
#include "Json.h"

class FMCPCommandRegistry;

/**
 * Handler class for StateTree-related MCP commands.
 *
 * StateTree is UE 5.x's modern behavior framework (complements Behavior Trees,
 * which are already supported by the base via UnrealMCPBT*Commands). This
 * handler exposes asset-level operations; deeper state-graph editing is
 * planned but not in this revision.
 *
 * Command names registered (omni-namespaced):
 *   omni.statetree.create_asset  — create a new UStateTree asset
 *   omni.statetree.list_assets   — enumerate StateTree assets in /Game
 *   omni.statetree.add_state     — add a state node (top-level or under a parent)
 */
class UNREALMCP_API FUnrealMCPStateTreeCommands
{
public:
    FUnrealMCPStateTreeCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);
    void RegisterCommands(FMCPCommandRegistry& Registry);

private:
    TSharedPtr<FJsonObject> HandleCreateAsset(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleListAssets(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddState(const TSharedPtr<FJsonObject>& Params);
};
