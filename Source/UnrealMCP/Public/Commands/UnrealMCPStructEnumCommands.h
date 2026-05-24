// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#pragma once

#include "CoreMinimal.h"
#include "Json.h"

class FMCPCommandRegistry;

/**
 * UUserDefinedStruct + UUserDefinedEnum editing commands.
 * StructureEditorUtils / EnumEditorUtils are editor-only C++ helpers not
 * bound to Python in UE 5.x — this handler exposes them via the MCP bridge.
 *
 * Commands:
 *   omni.struct.add_variable
 *   omni.enum.add_entry
 *   omni.enum.add_entries
 */
class UNREALMCP_API FUnrealMCPStructEnumCommands
{
public:
    FUnrealMCPStructEnumCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);
    void RegisterCommands(FMCPCommandRegistry& Registry);

private:
    TSharedPtr<FJsonObject> HandleStructAddVariable(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleEnumAddEntry(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleEnumAddEntries(const TSharedPtr<FJsonObject>& Params);
};
