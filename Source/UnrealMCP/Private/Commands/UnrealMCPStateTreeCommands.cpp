// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#include "Commands/UnrealMCPStateTreeCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "MCPCore.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "AssetRegistry/AssetData.h"

#if WITH_EDITOR
#include "StateTree.h"
#include "StateTreeEditingSubsystem.h"
#include "StateTreeEditorData.h"
#include "StateTreeState.h"
#include "StateTreeFactory.h"
#include "AssetToolsModule.h"
#include "IAssetTools.h"
#include "Factories/Factory.h"
#endif

namespace
{
    bool SplitAssetPath(const FString& AssetPath, FString& OutPackagePath, FString& OutAssetName)
    {
        int32 LastSlash = INDEX_NONE;
        if (!AssetPath.FindLastChar(TEXT('/'), LastSlash))
        {
            return false;
        }
        OutPackagePath = AssetPath.Left(LastSlash);
        OutAssetName = AssetPath.Mid(LastSlash + 1);
        return !OutAssetName.IsEmpty();
    }
}

FUnrealMCPStateTreeCommands::FUnrealMCPStateTreeCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPStateTreeCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("omni.statetree.create_asset"))
    {
        return HandleCreateAsset(Params);
    }
    if (CommandType == TEXT("omni.statetree.list_assets"))
    {
        return HandleListAssets(Params);
    }
    if (CommandType == TEXT("omni.statetree.add_state"))
    {
        return HandleAddState(Params);
    }
    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown statetree command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FUnrealMCPStateTreeCommands::HandleCreateAsset(const TSharedPtr<FJsonObject>& Params)
{
#if !WITH_EDITOR
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("omni.statetree.create_asset requires editor build"));
#else
    FString AssetPath;
    if (!Params->TryGetStringField(TEXT("asset_path"), AssetPath) || AssetPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'asset_path' parameter"));
    }

    FString PackagePath, AssetName;
    if (!SplitAssetPath(AssetPath, PackagePath, AssetName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Bad asset_path (expected /Game/Folder/Name): %s"), *AssetPath));
    }

    // UStateTreeFactory::ConfigureProperties opens a modal schema-picker dialog
    // when StateTreeSchemaClass is null, which is fatal in headless MCP. Resolve
    // the schema class up front and call SetSchemaClass before CreateAsset.
    // Default schema lives in GameplayStateTreeModule (not StateTreeModule).
    FString SchemaPath = TEXT("/Script/GameplayStateTreeModule.StateTreeComponentSchema");
    Params->TryGetStringField(TEXT("schema_class"), SchemaPath);

    UClass* SchemaClass = FindObject<UClass>(nullptr, *SchemaPath);
    if (!SchemaClass)
    {
        SchemaClass = LoadObject<UClass>(nullptr, *SchemaPath);
    }
    if (!SchemaClass)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Schema class not found: %s"), *SchemaPath));
    }

    UStateTreeFactory* Factory = NewObject<UStateTreeFactory>(GetTransientPackage(), UStateTreeFactory::StaticClass());
    Factory->SetSchemaClass(SchemaClass);

    FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools"));
    IAssetTools& AssetTools = AssetToolsModule.Get();

    UObject* NewAsset = AssetTools.CreateAsset(AssetName, PackagePath, UStateTree::StaticClass(), Factory);
    if (!NewAsset)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Failed to create StateTree at %s"), *AssetPath));
    }

    UStateTree* StateTree = Cast<UStateTree>(NewAsset);
    if (!StateTree)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Created asset is not a UStateTree"));
    }

    StateTree->Modify();
    StateTree->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("asset_path"), AssetPath);
    Result->SetStringField(TEXT("class"), TEXT("StateTree"));
    return Result;
#endif // WITH_EDITOR
}

TSharedPtr<FJsonObject> FUnrealMCPStateTreeCommands::HandleListAssets(const TSharedPtr<FJsonObject>& Params)
{
    FString Path;
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty())
    {
        Path = TEXT("/Game");
    }

    FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
    IAssetRegistry& AssetRegistry = AssetRegistryModule.Get();

    FARFilter Filter;
    Filter.bRecursivePaths = true;
    Filter.PackagePaths.Add(*Path);
    Filter.ClassPaths.Add(FTopLevelAssetPath(TEXT("/Script/StateTreeModule"), TEXT("StateTree")));

    TArray<FAssetData> Assets;
    AssetRegistry.GetAssets(Filter, Assets);

    TArray<TSharedPtr<FJsonValue>> Arr;
    for (const FAssetData& Asset : Assets)
    {
        Arr.Add(MakeShared<FJsonValueString>(Asset.GetObjectPathString()));
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("path"), Path);
    Result->SetArrayField(TEXT("assets"), Arr);
    Result->SetNumberField(TEXT("count"), Arr.Num());
    return Result;
}

#if WITH_EDITOR
namespace
{
    // Depth-first walk over all states in a StateTree's editor data, looking
    // for one whose Name matches the requested parent name. Returns nullptr
    // if no match is found.
    UStateTreeState* FindStateByName(UStateTreeEditorData* EditorData, const FName& Target)
    {
        if (!EditorData) { return nullptr; }

        TArray<UStateTreeState*> Stack;
        for (UStateTreeState* SubTree : EditorData->SubTrees)
        {
            if (SubTree) { Stack.Add(SubTree); }
        }
        while (Stack.Num() > 0)
        {
            UStateTreeState* State = Stack.Pop(EAllowShrinking::No);
            if (!State) { continue; }
            if (State->Name == Target)
            {
                return State;
            }
            for (UStateTreeState* Child : State->Children)
            {
                if (Child) { Stack.Add(Child); }
            }
        }
        return nullptr;
    }
}
#endif

TSharedPtr<FJsonObject> FUnrealMCPStateTreeCommands::HandleAddState(const TSharedPtr<FJsonObject>& Params)
{
#if !WITH_EDITOR
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("omni.statetree.add_state requires editor build"));
#else
    FString AssetPath;
    if (!Params->TryGetStringField(TEXT("asset_path"), AssetPath) || AssetPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'asset_path' parameter"));
    }
    FString StateName;
    if (!Params->TryGetStringField(TEXT("state_name"), StateName) || StateName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'state_name' parameter"));
    }
    FString ParentState;
    Params->TryGetStringField(TEXT("parent_state"), ParentState);

    UStateTree* StateTree = LoadObject<UStateTree>(nullptr, *AssetPath);
    if (!StateTree)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("StateTree asset not found: %s"), *AssetPath));
    }

    UStateTreeEditorData* EditorData = Cast<UStateTreeEditorData>(StateTree->EditorData);
    if (!EditorData)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            TEXT("StateTree has no UStateTreeEditorData (was the asset created via the factory?)"));
    }

    EditorData->Modify();

    const FName NewStateName(*StateName);
    FString ParentResolved = TEXT("");
    if (ParentState.IsEmpty())
    {
        // Top-level state — add as a subtree.
        UStateTreeState& NewState = EditorData->AddSubTree(NewStateName);
        (void)NewState;
    }
    else
    {
        UStateTreeState* Parent = FindStateByName(EditorData, FName(*ParentState));
        if (!Parent)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("Parent state '%s' not found in %s"), *ParentState, *AssetPath));
        }
        Parent->Modify();
        UStateTreeState& NewState = Parent->AddChildState(NewStateName);
        (void)NewState;
        ParentResolved = ParentState;
    }

    StateTree->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("asset_path"), AssetPath);
    Result->SetStringField(TEXT("state_name"), StateName);
    Result->SetStringField(TEXT("parent_state"), ParentResolved);
    return Result;
#endif // WITH_EDITOR
}

// ============================================================================
// COMMAND REGISTRATION
// ============================================================================

void FUnrealMCPStateTreeCommands::RegisterCommands(FMCPCommandRegistry& Registry)
{
    Registry.RegisterCommand(TEXT("omni.statetree.create_asset"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.statetree.create_asset"), P); });
    Registry.RegisterCommand(TEXT("omni.statetree.list_assets"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.statetree.list_assets"), P); });
    Registry.RegisterCommand(TEXT("omni.statetree.add_state"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.statetree.add_state"), P); });
}
