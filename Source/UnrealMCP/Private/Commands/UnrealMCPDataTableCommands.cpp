// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#include "Commands/UnrealMCPDataTableCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "MCPCore.h"

#include "Engine/DataTable.h"
#include "Engine/UserDefinedStruct.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "PackageTools.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"

#if WITH_EDITOR
#include "DataTableEditorUtils.h"
#include "AssetToolsModule.h"
#include "IAssetTools.h"
#include "Factories/DataTableFactory.h"
#endif

namespace
{
    /** Resolve a row-struct path (either /Game/... for UUserDefinedStruct or /Script/... for native UScriptStruct). */
    UScriptStruct* ResolveRowStruct(const FString& StructPath)
    {
        if (StructPath.IsEmpty())
        {
            return nullptr;
        }

        // Native struct (e.g. /Script/PanzerStrikeUE.TankStatsRow)
        if (StructPath.StartsWith(TEXT("/Script/")))
        {
            return FindObject<UScriptStruct>(nullptr, *StructPath);
        }

        // Asset-backed (UUserDefinedStruct)
        UObject* Loaded = StaticLoadObject(UScriptStruct::StaticClass(), nullptr, *StructPath);
        return Cast<UScriptStruct>(Loaded);
    }

    /** Split "/Game/Path/Asset" into ("/Game/Path", "Asset"). */
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

FUnrealMCPDataTableCommands::FUnrealMCPDataTableCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPDataTableCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("omni.datatable.create"))
    {
        return HandleCreate(Params);
    }
    if (CommandType == TEXT("omni.datatable.add_row"))
    {
        return HandleAddRow(Params);
    }
    if (CommandType == TEXT("omni.datatable.import_csv"))
    {
        return HandleImportCSV(Params);
    }
    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown datatable command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FUnrealMCPDataTableCommands::HandleCreate(const TSharedPtr<FJsonObject>& Params)
{
#if !WITH_EDITOR
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("omni.datatable.create requires editor build"));
#else
    FString AssetPath;
    if (!Params->TryGetStringField(TEXT("asset_path"), AssetPath) || AssetPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'asset_path' parameter"));
    }
    FString RowStructPath;
    if (!Params->TryGetStringField(TEXT("row_struct_path"), RowStructPath) || RowStructPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'row_struct_path' parameter"));
    }

    UScriptStruct* RowStruct = ResolveRowStruct(RowStructPath);
    if (!RowStruct)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Could not resolve row struct: %s"), *RowStructPath));
    }

    FString PackagePath, AssetName;
    if (!SplitAssetPath(AssetPath, PackagePath, AssetName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Bad asset_path (expected /Game/Folder/Name): %s"), *AssetPath));
    }

    FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools"));
    IAssetTools& AssetTools = AssetToolsModule.Get();

    UDataTableFactory* Factory = NewObject<UDataTableFactory>();
    Factory->Struct = RowStruct;

    UObject* NewAsset = AssetTools.CreateAsset(AssetName, PackagePath, UDataTable::StaticClass(), Factory);
    UDataTable* NewTable = Cast<UDataTable>(NewAsset);
    if (!NewTable)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Failed to create DataTable at %s"), *AssetPath));
    }

    // Belt-and-braces: ensure RowStruct is set even if the factory didn't carry it.
    if (NewTable->RowStruct != RowStruct)
    {
        NewTable->RowStruct = RowStruct;
        NewTable->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("asset_path"), AssetPath);
    Result->SetStringField(TEXT("row_struct"), RowStructPath);
    return Result;
#endif // WITH_EDITOR
}

TSharedPtr<FJsonObject> FUnrealMCPDataTableCommands::HandleAddRow(const TSharedPtr<FJsonObject>& Params)
{
#if !WITH_EDITOR
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("omni.datatable.add_row requires editor build"));
#else
    FString AssetPath;
    if (!Params->TryGetStringField(TEXT("asset_path"), AssetPath) || AssetPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'asset_path' parameter"));
    }
    FString RowName;
    if (!Params->TryGetStringField(TEXT("row_name"), RowName) || RowName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'row_name' parameter"));
    }
    const TSharedPtr<FJsonObject>* RowDataObj = nullptr;
    if (!Params->TryGetObjectField(TEXT("row_data"), RowDataObj) || !RowDataObj || !RowDataObj->IsValid())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'row_data' parameter (object)"));
    }

    UDataTable* Table = Cast<UDataTable>(StaticLoadObject(UDataTable::StaticClass(), nullptr, *AssetPath));
    if (!Table)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("DataTable not found: %s"), *AssetPath));
    }
    if (!Table->RowStruct)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("DataTable has no RowStruct: %s"), *AssetPath));
    }

    const FName RowFName(*RowName);
    if (Table->GetRowMap().Contains(RowFName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Row already exists: %s"), *RowName));
    }

    // Add an empty row, then set fields from JSON.
    FDataTableEditorUtils::AddRow(Table, RowFName);
    uint8* RowPtr = Table->GetRowMap().FindRef(RowFName);
    if (!RowPtr)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("AddRow succeeded but row pointer is null"));
    }

    int32 FieldsSet = 0;
    TArray<FString> Skipped;
    for (const TPair<FString, TSharedPtr<FJsonValue>>& Field : (*RowDataObj)->Values)
    {
        FProperty* Prop = Table->RowStruct->FindPropertyByName(FName(*Field.Key));
        if (!Prop)
        {
            Skipped.Add(Field.Key);
            continue;
        }
        void* ValuePtr = Prop->ContainerPtrToValuePtr<void>(RowPtr);

        // Cover the common primitive cases. Complex struct/array fields are
        // a TODO — use ImportText against the JSON value's stringification.
        if (Field.Value->Type == EJson::Number)
        {
            const double N = Field.Value->AsNumber();
            if (FFloatProperty* F = CastField<FFloatProperty>(Prop)) { F->SetPropertyValue(ValuePtr, static_cast<float>(N)); ++FieldsSet; continue; }
            if (FDoubleProperty* D = CastField<FDoubleProperty>(Prop)) { D->SetPropertyValue(ValuePtr, N); ++FieldsSet; continue; }
            if (FIntProperty* I = CastField<FIntProperty>(Prop)) { I->SetPropertyValue(ValuePtr, static_cast<int32>(N)); ++FieldsSet; continue; }
            if (FInt64Property* I64 = CastField<FInt64Property>(Prop)) { I64->SetPropertyValue(ValuePtr, static_cast<int64>(N)); ++FieldsSet; continue; }
            if (FByteProperty* B = CastField<FByteProperty>(Prop)) { B->SetPropertyValue(ValuePtr, static_cast<uint8>(N)); ++FieldsSet; continue; }
        }
        else if (Field.Value->Type == EJson::String)
        {
            const FString S = Field.Value->AsString();
            if (FStrProperty* SP = CastField<FStrProperty>(Prop)) { SP->SetPropertyValue(ValuePtr, S); ++FieldsSet; continue; }
            if (FNameProperty* NP = CastField<FNameProperty>(Prop)) { NP->SetPropertyValue(ValuePtr, FName(*S)); ++FieldsSet; continue; }
            if (FTextProperty* TP = CastField<FTextProperty>(Prop)) { TP->SetPropertyValue(ValuePtr, FText::FromString(S)); ++FieldsSet; continue; }
            // Fallback: try ImportText for enums/structs/etc.
            Prop->ImportText_Direct(*S, ValuePtr, nullptr, PPF_None);
            ++FieldsSet;
            continue;
        }
        else if (Field.Value->Type == EJson::Boolean)
        {
            if (FBoolProperty* BP = CastField<FBoolProperty>(Prop)) { BP->SetPropertyValue(ValuePtr, Field.Value->AsBool()); ++FieldsSet; continue; }
        }
        Skipped.Add(Field.Key);
    }

    Table->Modify();
    Table->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("asset_path"), AssetPath);
    Result->SetStringField(TEXT("row_name"), RowName);
    Result->SetNumberField(TEXT("fields_set"), FieldsSet);
    if (Skipped.Num() > 0)
    {
        TArray<TSharedPtr<FJsonValue>> SkippedArr;
        for (const FString& S : Skipped) { SkippedArr.Add(MakeShared<FJsonValueString>(S)); }
        Result->SetArrayField(TEXT("skipped_fields"), SkippedArr);
    }
    return Result;
#endif // WITH_EDITOR
}

TSharedPtr<FJsonObject> FUnrealMCPDataTableCommands::HandleImportCSV(const TSharedPtr<FJsonObject>& Params)
{
#if !WITH_EDITOR
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("omni.datatable.import_csv requires editor build"));
#else
    FString AssetPath;
    if (!Params->TryGetStringField(TEXT("asset_path"), AssetPath) || AssetPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'asset_path' parameter"));
    }
    FString CSVPath;
    if (!Params->TryGetStringField(TEXT("csv_path"), CSVPath) || CSVPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'csv_path' parameter"));
    }
    FString RowStructPath;
    Params->TryGetStringField(TEXT("row_struct_path"), RowStructPath);

    UDataTable* Table = Cast<UDataTable>(StaticLoadObject(UDataTable::StaticClass(), nullptr, *AssetPath));
    if (!Table)
    {
        // Create-on-import path: if asset doesn't exist, build it first.
        if (RowStructPath.IsEmpty())
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("DataTable not found and no row_struct_path provided to create it: %s"), *AssetPath));
        }
        TSharedPtr<FJsonObject> CreateParams = MakeShared<FJsonObject>();
        CreateParams->SetStringField(TEXT("asset_path"), AssetPath);
        CreateParams->SetStringField(TEXT("row_struct_path"), RowStructPath);
        TSharedPtr<FJsonObject> CreateResult = HandleCreate(CreateParams);
        bool bOk = false;
        if (CreateResult.IsValid()) { CreateResult->TryGetBoolField(TEXT("success"), bOk); }
        if (!bOk)
        {
            return CreateResult;
        }
        Table = Cast<UDataTable>(StaticLoadObject(UDataTable::StaticClass(), nullptr, *AssetPath));
    }
    if (!Table)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("DataTable still unavailable after create attempt"));
    }
    if (!Table->RowStruct)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("DataTable has no RowStruct"));
    }

    FString CSVText;
    if (!FFileHelper::LoadFileToString(CSVText, *CSVPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Could not read CSV: %s"), *CSVPath));
    }

    TArray<FString> Errors = Table->CreateTableFromCSVString(CSVText);
    Table->Modify();
    Table->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), Errors.Num() == 0);
    Result->SetStringField(TEXT("asset_path"), AssetPath);
    Result->SetNumberField(TEXT("rows"), Table->GetRowMap().Num());
    if (Errors.Num() > 0)
    {
        TArray<TSharedPtr<FJsonValue>> Arr;
        for (const FString& E : Errors) { Arr.Add(MakeShared<FJsonValueString>(E)); }
        Result->SetArrayField(TEXT("errors"), Arr);
    }
    return Result;
#endif // WITH_EDITOR
}

// ============================================================================
// COMMAND REGISTRATION
// ============================================================================

void FUnrealMCPDataTableCommands::RegisterCommands(FMCPCommandRegistry& Registry)
{
    Registry.RegisterCommand(TEXT("omni.datatable.create"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.datatable.create"), P); });
    Registry.RegisterCommand(TEXT("omni.datatable.add_row"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.datatable.add_row"), P); });
    Registry.RegisterCommand(TEXT("omni.datatable.import_csv"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.datatable.import_csv"), P); });
}
