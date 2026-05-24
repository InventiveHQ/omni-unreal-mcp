// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#include "Commands/UnrealMCPGameplayTagCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "MCPCore.h"

#include "GameplayTagsManager.h"
#include "GameplayTagsSettings.h"
#include "GameplayTagContainer.h"

#if WITH_EDITOR
#include "GameplayTagsEditorModule.h"
#endif

FUnrealMCPGameplayTagCommands::FUnrealMCPGameplayTagCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPGameplayTagCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("omni.gameplay_tag.create"))
    {
        return HandleCreate(Params);
    }
    if (CommandType == TEXT("omni.gameplay_tag.list"))
    {
        return HandleList(Params);
    }
    if (CommandType == TEXT("omni.gameplay_tag.query"))
    {
        return HandleQuery(Params);
    }
    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown gameplay_tag command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FUnrealMCPGameplayTagCommands::HandleCreate(const TSharedPtr<FJsonObject>& Params)
{
#if !WITH_EDITOR
    return FUnrealMCPCommonUtils::CreateErrorResponse(
        TEXT("omni.gameplay_tag.create requires editor build (writes to DefaultGameplayTags.ini)"));
#else
    FString Tag;
    if (!Params->TryGetStringField(TEXT("tag"), Tag) || Tag.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'tag' parameter"));
    }

    FString Comment;
    Params->TryGetStringField(TEXT("comment"), Comment);

    // If the tag already exists, return success without re-adding.
    UGameplayTagsManager& Manager = UGameplayTagsManager::Get();
    const FGameplayTag Existing = Manager.RequestGameplayTag(FName(*Tag), /*ErrorIfNotFound=*/false);
    if (Existing.IsValid())
    {
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetBoolField(TEXT("created"), false);
        Result->SetStringField(TEXT("tag"), Tag);
        Result->SetStringField(TEXT("note"), TEXT("Tag already exists"));
        return Result;
    }

    // Add the tag to the project's default tag INI. The editor module persists
    // the change to Config/Tags/DefaultGameplayTags.ini (or DefaultGameplayTags.ini)
    // and refreshes the runtime registry.
    IGameplayTagsEditorModule& EditorModule = IGameplayTagsEditorModule::Get();
    const FName TagSource = FName(TEXT("DefaultGameplayTags.ini"));
    const bool bAdded = EditorModule.AddNewGameplayTagToINI(Tag, Comment, TagSource);

    if (!bAdded)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Failed to add gameplay tag '%s'"), *Tag));
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetBoolField(TEXT("created"), true);
    Result->SetStringField(TEXT("tag"), Tag);
    if (!Comment.IsEmpty())
    {
        Result->SetStringField(TEXT("comment"), Comment);
    }
    return Result;
#endif // WITH_EDITOR
}

TSharedPtr<FJsonObject> FUnrealMCPGameplayTagCommands::HandleList(const TSharedPtr<FJsonObject>& Params)
{
    FString Prefix;
    Params->TryGetStringField(TEXT("prefix"), Prefix);

    UGameplayTagsManager& Manager = UGameplayTagsManager::Get();
    FGameplayTagContainer AllTags;
    Manager.RequestAllGameplayTags(AllTags, /*OnlyIncludeDictTags=*/false);

    TArray<TSharedPtr<FJsonValue>> TagArray;
    int32 Count = 0;
    for (const FGameplayTag& Tag : AllTags)
    {
        const FString TagString = Tag.ToString();
        if (Prefix.IsEmpty() || TagString.StartsWith(Prefix))
        {
            TagArray.Add(MakeShared<FJsonValueString>(TagString));
            ++Count;
        }
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetArrayField(TEXT("tags"), TagArray);
    Result->SetNumberField(TEXT("count"), Count);
    if (!Prefix.IsEmpty())
    {
        Result->SetStringField(TEXT("prefix"), Prefix);
    }
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPGameplayTagCommands::HandleQuery(const TSharedPtr<FJsonObject>& Params)
{
    FString Tag;
    if (!Params->TryGetStringField(TEXT("tag"), Tag) || Tag.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'tag' parameter"));
    }

    UGameplayTagsManager& Manager = UGameplayTagsManager::Get();
    const FGameplayTag Found = Manager.RequestGameplayTag(FName(*Tag), /*ErrorIfNotFound=*/false);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetBoolField(TEXT("exists"), Found.IsValid());
    Result->SetStringField(TEXT("tag"), Tag);

    if (Found.IsValid())
    {
        // Walk parent chain
        FGameplayTagContainer Parents = Manager.RequestGameplayTagParents(Found);
        TArray<TSharedPtr<FJsonValue>> ParentArray;
        for (const FGameplayTag& Parent : Parents)
        {
            if (Parent != Found)
            {
                ParentArray.Add(MakeShared<FJsonValueString>(Parent.ToString()));
            }
        }
        Result->SetArrayField(TEXT("parents"), ParentArray);
    }
    return Result;
}

// ============================================================================
// COMMAND REGISTRATION
// ============================================================================

void FUnrealMCPGameplayTagCommands::RegisterCommands(FMCPCommandRegistry& Registry)
{
    Registry.RegisterCommand(TEXT("omni.gameplay_tag.create"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.gameplay_tag.create"), P); });
    Registry.RegisterCommand(TEXT("omni.gameplay_tag.list"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.gameplay_tag.list"), P); });
    Registry.RegisterCommand(TEXT("omni.gameplay_tag.query"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.gameplay_tag.query"), P); });
}
