// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#pragma once

#include "CoreMinimal.h"
#include "Json.h"

class FMCPCommandRegistry;

/**
 * Handler class for GameplayTag-related MCP commands.
 *
 * Wraps UGameplayTagsManager / GameplayTagsEditor APIs to let an AI assistant
 * create, list, and query the project's hierarchical FGameplayTag table.
 *
 * Command names registered (omni-namespaced):
 *   omni.gameplay_tag.create
 *   omni.gameplay_tag.list
 *   omni.gameplay_tag.query
 */
class UNREALMCP_API FUnrealMCPGameplayTagCommands
{
public:
    FUnrealMCPGameplayTagCommands();

    /** Top-level dispatcher used when this handler owns the command. */
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

    /** Register all GameplayTag commands with the central registry. */
    void RegisterCommands(FMCPCommandRegistry& Registry);

private:
    TSharedPtr<FJsonObject> HandleCreate(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleList(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleQuery(const TSharedPtr<FJsonObject>& Params);
};
