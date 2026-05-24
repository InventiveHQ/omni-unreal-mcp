// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#pragma once

#include "CoreMinimal.h"
#include "Json.h"

class FMCPCommandRegistry;

/**
 * Handler class for DataTable-related MCP commands.
 *
 * Wraps UDataTable + the editor AssetTools / DataTableEditor APIs to let an
 * AI assistant programmatically create DataTables, add rows, and import CSV.
 *
 * Command names registered (omni-namespaced):
 *   omni.datatable.create     — make a new DataTable asset bound to a row struct
 *   omni.datatable.add_row    — add a row (row name + field-value dict)
 *   omni.datatable.import_csv — bulk-import rows from a CSV file
 */
class UNREALMCP_API FUnrealMCPDataTableCommands
{
public:
    FUnrealMCPDataTableCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);
    void RegisterCommands(FMCPCommandRegistry& Registry);

private:
    TSharedPtr<FJsonObject> HandleCreate(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddRow(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleImportCSV(const TSharedPtr<FJsonObject>& Params);
};
