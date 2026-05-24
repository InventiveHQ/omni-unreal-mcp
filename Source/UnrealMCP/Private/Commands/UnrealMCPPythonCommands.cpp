// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#include "Commands/UnrealMCPPythonCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "MCPCore.h"

#if WITH_EDITOR
#include "IPythonScriptPlugin.h"
#include "PythonScriptTypes.h"
#endif

FUnrealMCPPythonCommands::FUnrealMCPPythonCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPPythonCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("omni.python.execute"))
    {
        return HandleExecute(Params);
    }
    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown python command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FUnrealMCPPythonCommands::HandleExecute(const TSharedPtr<FJsonObject>& Params)
{
#if !WITH_EDITOR
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("omni.python.execute requires an editor build"));
#else
    FString Code;
    if (!Params->TryGetStringField(TEXT("code"), Code))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'code' parameter"));
    }

    IPythonScriptPlugin* Python = IPythonScriptPlugin::Get();
    if (!Python)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            TEXT("PythonScriptPlugin module not loaded. Enable the Python Script Plugin in the project."));
    }
    if (!Python->IsPythonAvailable() || !Python->IsPythonInitialized())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            TEXT("Python is not initialized. Open the editor with Python support enabled."));
    }

    // Default to ExecuteFile so multi-statement scripts work. Callers can
    // opt into EvaluateStatement to get a return value for a single expression.
    EPythonCommandExecutionMode Mode = EPythonCommandExecutionMode::ExecuteFile;
    FString ModeString;
    if (Params->TryGetStringField(TEXT("mode"), ModeString))
    {
        LexFromString(Mode, *ModeString);
    }

    FPythonCommandEx Cmd;
    Cmd.Command = Code;
    Cmd.ExecutionMode = Mode;
    Cmd.FileExecutionScope = EPythonFileExecutionScope::Private;
    // Unattended: suppress modal dialogs (essential in headless MCP).
    Cmd.Flags = EPythonCommandFlags::Unattended;

    const bool bSuccess = Python->ExecPythonCommandEx(Cmd);

    // Gather captured log output into stdout/stderr-style buckets.
    FString Stdout, Stderr;
    for (const FPythonLogOutputEntry& Entry : Cmd.LogOutput)
    {
        switch (Entry.Type)
        {
        case EPythonLogOutputType::Error:
        case EPythonLogOutputType::Warning:
            if (!Stderr.IsEmpty()) { Stderr += TEXT("\n"); }
            Stderr += Entry.Output;
            break;
        case EPythonLogOutputType::Info:
        default:
            if (!Stdout.IsEmpty()) { Stdout += TEXT("\n"); }
            Stdout += Entry.Output;
            break;
        }
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), bSuccess);
    Result->SetStringField(TEXT("stdout"), Stdout);
    Result->SetStringField(TEXT("stderr"), Stderr);
    Result->SetStringField(TEXT("result"), Cmd.CommandResult);
    Result->SetStringField(TEXT("mode"), LexToString(Mode));
    return Result;
#endif // WITH_EDITOR
}

// ============================================================================
// COMMAND REGISTRATION
// ============================================================================

void FUnrealMCPPythonCommands::RegisterCommands(FMCPCommandRegistry& Registry)
{
    Registry.RegisterCommand(TEXT("omni.python.execute"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.python.execute"), P); });
}
