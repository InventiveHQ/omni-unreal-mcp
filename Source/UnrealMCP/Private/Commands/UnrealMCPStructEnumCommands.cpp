// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#include "Commands/UnrealMCPStructEnumCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "MCPCore.h"

#include "Engine/UserDefinedStruct.h"
#include "Engine/UserDefinedEnum.h"
#include "EditorAssetLibrary.h"
#include "EdGraphSchema_K2.h"

#if WITH_EDITOR
#include "Kismet2/StructureEditorUtils.h"
#include "Kismet2/EnumEditorUtils.h"
#include "UserDefinedStructure/UserDefinedStructEditorData.h"  // FStructVariableDescription full def
#endif

FUnrealMCPStructEnumCommands::FUnrealMCPStructEnumCommands() {}

namespace
{
    /** Map a string type name to an FEdGraphPinType usable by FStructureEditorUtils::AddVariable. */
    bool BuildPinType(const FString& TypeName, FEdGraphPinType& OutType, FString& OutError)
    {
        const FString T = TypeName.ToLower();
        if (T == TEXT("bool")) { OutType.PinCategory = UEdGraphSchema_K2::PC_Boolean; return true; }
        if (T == TEXT("int") || T == TEXT("int32"))
        {
            OutType.PinCategory = UEdGraphSchema_K2::PC_Int; return true;
        }
        if (T == TEXT("int64"))
        {
            OutType.PinCategory = UEdGraphSchema_K2::PC_Int64; return true;
        }
        if (T == TEXT("float"))
        {
            OutType.PinCategory = UEdGraphSchema_K2::PC_Real;
            OutType.PinSubCategory = UEdGraphSchema_K2::PC_Float;
            return true;
        }
        if (T == TEXT("double") || T == TEXT("real"))
        {
            OutType.PinCategory = UEdGraphSchema_K2::PC_Real;
            OutType.PinSubCategory = UEdGraphSchema_K2::PC_Double;
            return true;
        }
        if (T == TEXT("string")) { OutType.PinCategory = UEdGraphSchema_K2::PC_String; return true; }
        if (T == TEXT("name"))   { OutType.PinCategory = UEdGraphSchema_K2::PC_Name;   return true; }
        if (T == TEXT("text"))   { OutType.PinCategory = UEdGraphSchema_K2::PC_Text;   return true; }
        if (T == TEXT("vector"))
        {
            OutType.PinCategory = UEdGraphSchema_K2::PC_Struct;
            OutType.PinSubCategoryObject = TBaseStructure<FVector>::Get();
            return true;
        }
        if (T == TEXT("rotator"))
        {
            OutType.PinCategory = UEdGraphSchema_K2::PC_Struct;
            OutType.PinSubCategoryObject = TBaseStructure<FRotator>::Get();
            return true;
        }
        if (T == TEXT("transform"))
        {
            OutType.PinCategory = UEdGraphSchema_K2::PC_Struct;
            OutType.PinSubCategoryObject = TBaseStructure<FTransform>::Get();
            return true;
        }
        // Asset-path: treat as struct or enum reference based on the loaded class.
        if (TypeName.StartsWith(TEXT("/")))
        {
            UObject* Obj = UEditorAssetLibrary::LoadAsset(TypeName);
            if (UUserDefinedStruct* AsStruct = Cast<UUserDefinedStruct>(Obj))
            {
                OutType.PinCategory = UEdGraphSchema_K2::PC_Struct;
                OutType.PinSubCategoryObject = AsStruct;
                return true;
            }
            if (UUserDefinedEnum* AsEnum = Cast<UUserDefinedEnum>(Obj))
            {
                OutType.PinCategory = UEdGraphSchema_K2::PC_Byte;
                OutType.PinSubCategoryObject = AsEnum;
                return true;
            }
            OutError = FString::Printf(TEXT("Asset path '%s' didn't resolve to a struct or enum"), *TypeName);
            return false;
        }
        OutError = FString::Printf(TEXT("Unknown var_type '%s'"), *TypeName);
        return false;
    }
}

TSharedPtr<FJsonObject> FUnrealMCPStructEnumCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("omni.struct.add_variable")) return HandleStructAddVariable(Params);
    if (CommandType == TEXT("omni.enum.add_entry"))      return HandleEnumAddEntry(Params);
    if (CommandType == TEXT("omni.enum.add_entries"))    return HandleEnumAddEntries(Params);
    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown struct/enum command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FUnrealMCPStructEnumCommands::HandleStructAddVariable(const TSharedPtr<FJsonObject>& Params)
{
#if !WITH_EDITOR
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Editor-only command"));
#else
    FString AssetPath, VarName, VarType;
    if (!Params->TryGetStringField(TEXT("asset_path"), AssetPath))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'asset_path'"));
    if (!Params->TryGetStringField(TEXT("var_name"), VarName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'var_name'"));
    if (!Params->TryGetStringField(TEXT("var_type"), VarType))
        VarType = TEXT("float");

    UUserDefinedStruct* Struct = Cast<UUserDefinedStruct>(UEditorAssetLibrary::LoadAsset(AssetPath));
    if (!Struct)
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Not a UUserDefinedStruct: %s"), *AssetPath));

    FEdGraphPinType PinType;
    FString Err;
    if (!BuildPinType(VarType, PinType, Err))
        return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    // Snapshot existing variable GUIDs so we can identify the one AddVariable creates.
    TSet<FGuid> Before;
    for (const FStructVariableDescription& V : FStructureEditorUtils::GetVarDesc(Struct))
        Before.Add(V.VarGuid);

    if (!FStructureEditorUtils::AddVariable(Struct, PinType))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("AddVariable returned false"));

    FGuid NewGuid;
    for (const FStructVariableDescription& V : FStructureEditorUtils::GetVarDesc(Struct))
    {
        if (!Before.Contains(V.VarGuid)) { NewGuid = V.VarGuid; break; }
    }

    bool bRenamed = false;
    if (NewGuid.IsValid())
        bRenamed = FStructureEditorUtils::RenameVariable(Struct, NewGuid, VarName);

    UEditorAssetLibrary::SaveLoadedAsset(Struct, false);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("asset"), AssetPath);
    Result->SetStringField(TEXT("variable"), VarName);
    Result->SetStringField(TEXT("type"), VarType);
    Result->SetBoolField(TEXT("renamed"), bRenamed);
    return Result;
#endif
}

TSharedPtr<FJsonObject> FUnrealMCPStructEnumCommands::HandleEnumAddEntry(const TSharedPtr<FJsonObject>& Params)
{
#if !WITH_EDITOR
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Editor-only command"));
#else
    FString AssetPath, EntryName;
    if (!Params->TryGetStringField(TEXT("asset_path"), AssetPath))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'asset_path'"));
    if (!Params->TryGetStringField(TEXT("entry_name"), EntryName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'entry_name'"));

    UUserDefinedEnum* Enum = Cast<UUserDefinedEnum>(UEditorAssetLibrary::LoadAsset(AssetPath));
    if (!Enum)
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Not a UUserDefinedEnum: %s"), *AssetPath));

    // Validate name first
    if (!FEnumEditorUtils::IsProperNameForUserDefinedEnumerator(Enum, EntryName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Entry name '%s' is invalid or already in use"), *EntryName));

    FEnumEditorUtils::AddNewEnumeratorForUserDefinedEnum(Enum);
    // Newly added entry sits at NumEnums - 2 (the slot before _MAX). _MAX shifts to NumEnums - 1.
    const int32 NewIndex = Enum->NumEnums() - 2;
    if (NewIndex < 0)
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("AddNewEnumerator failed — no slots"));

    const bool bRenamed = FEnumEditorUtils::SetEnumeratorDisplayName(
        Enum, NewIndex, FText::FromString(EntryName));
    UEditorAssetLibrary::SaveLoadedAsset(Enum, false);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("asset"), AssetPath);
    Result->SetStringField(TEXT("entry"), EntryName);
    Result->SetNumberField(TEXT("index"), NewIndex);
    Result->SetBoolField(TEXT("renamed"), bRenamed);
    return Result;
#endif
}

TSharedPtr<FJsonObject> FUnrealMCPStructEnumCommands::HandleEnumAddEntries(const TSharedPtr<FJsonObject>& Params)
{
#if !WITH_EDITOR
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Editor-only command"));
#else
    FString AssetPath;
    if (!Params->TryGetStringField(TEXT("asset_path"), AssetPath))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'asset_path'"));
    const TArray<TSharedPtr<FJsonValue>>* EntriesJson = nullptr;
    if (!Params->TryGetArrayField(TEXT("entries"), EntriesJson) || !EntriesJson)
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'entries' array"));

    UUserDefinedEnum* Enum = Cast<UUserDefinedEnum>(UEditorAssetLibrary::LoadAsset(AssetPath));
    if (!Enum)
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Not a UUserDefinedEnum: %s"), *AssetPath));

    TArray<TSharedPtr<FJsonValue>> Added, Skipped;
    for (const TSharedPtr<FJsonValue>& V : *EntriesJson)
    {
        const FString Name = V.IsValid() ? V->AsString() : FString();
        if (Name.IsEmpty()) continue;
        if (!FEnumEditorUtils::IsProperNameForUserDefinedEnumerator(Enum, Name))
        {
            Skipped.Add(MakeShared<FJsonValueString>(Name));
            continue;
        }
        FEnumEditorUtils::AddNewEnumeratorForUserDefinedEnum(Enum);
        const int32 NewIndex = Enum->NumEnums() - 2;
        if (NewIndex >= 0)
        {
            FEnumEditorUtils::SetEnumeratorDisplayName(Enum, NewIndex, FText::FromString(Name));
            Added.Add(MakeShared<FJsonValueString>(Name));
        }
    }
    UEditorAssetLibrary::SaveLoadedAsset(Enum, false);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("asset"), AssetPath);
    Result->SetArrayField(TEXT("added"), Added);
    Result->SetArrayField(TEXT("skipped"), Skipped);
    return Result;
#endif
}

void FUnrealMCPStructEnumCommands::RegisterCommands(FMCPCommandRegistry& Registry)
{
    Registry.RegisterCommand(TEXT("omni.struct.add_variable"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.struct.add_variable"), P); });
    Registry.RegisterCommand(TEXT("omni.enum.add_entry"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.enum.add_entry"), P); });
    Registry.RegisterCommand(TEXT("omni.enum.add_entries"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.enum.add_entries"), P); });
}
