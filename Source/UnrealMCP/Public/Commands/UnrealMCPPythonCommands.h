// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#pragma once

#include "CoreMinimal.h"
#include "Json.h"

class FMCPCommandRegistry;

/**
 * Handler for raw Python execution against the in-editor Python interpreter.
 *
 * This is the headline "VibeUE parity" tool — instead of hand-wrapping
 * thousands of UE APIs as individual MCP tools, expose the editor's full
 * Python surface through a single execute command. The AI gets at the
 * `unreal` Python module directly.
 *
 * Requires the engine's PythonScriptPlugin (Experimental but shipped in
 * 5.x) to be enabled in the project.
 *
 * Command names registered (omni-namespaced):
 *   omni.python.execute  — run arbitrary Python code, return stdout/stderr/result
 */
class UNREALMCP_API FUnrealMCPPythonCommands
{
public:
    FUnrealMCPPythonCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);
    void RegisterCommands(FMCPCommandRegistry& Registry);

private:
    TSharedPtr<FJsonObject> HandleExecute(const TSharedPtr<FJsonObject>& Params);
};
