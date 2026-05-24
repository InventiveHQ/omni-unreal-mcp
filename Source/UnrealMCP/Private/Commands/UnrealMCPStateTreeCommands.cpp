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

// ============================================================================
// COMMAND REGISTRATION
// ============================================================================

void FUnrealMCPStateTreeCommands::RegisterCommands(FMCPCommandRegistry& Registry)
{
    Registry.RegisterCommand(TEXT("omni.statetree.create_asset"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.statetree.create_asset"), P); });
    Registry.RegisterCommand(TEXT("omni.statetree.list_assets"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.statetree.list_assets"), P); });
}
