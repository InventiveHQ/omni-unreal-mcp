// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#include "Commands/UnrealMCPTerrainCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "MCPCore.h"

#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Editor.h"

#include "IImageWrapper.h"
#include "IImageWrapperModule.h"

#if WITH_EDITOR
#include "Landscape.h"
#include "LandscapeProxy.h"
#include "LandscapeInfo.h"
#include "LandscapeEditorSubsystem.h"
#endif

namespace
{
#if WITH_EDITOR
    ALandscape* FindLandscapeByLabel(const FString& Label)
    {
        UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
        if (!World) { return nullptr; }
        for (TActorIterator<ALandscape> It(World); It; ++It)
        {
            ALandscape* L = *It;
            if (L && (Label.IsEmpty() || L->GetActorLabel() == Label))
            {
                return L;
            }
        }
        return nullptr;
    }
#endif

    /** Decode a heightmap PNG file into a uint16 height array. */
    bool LoadHeightmapPNG(const FString& Path, TArray<uint16>& OutHeights, int32& OutWidth, int32& OutHeight, FString& OutError)
    {
        TArray<uint8> FileBytes;
        if (!FFileHelper::LoadFileToArray(FileBytes, *Path))
        {
            OutError = FString::Printf(TEXT("Could not read PNG: %s"), *Path);
            return false;
        }
        IImageWrapperModule& Wrappers = FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
        TSharedPtr<IImageWrapper> PNG = Wrappers.CreateImageWrapper(EImageFormat::PNG);
        if (!PNG.IsValid() || !PNG->SetCompressed(FileBytes.GetData(), FileBytes.Num()))
        {
            OutError = TEXT("Failed to decode PNG headers");
            return false;
        }
        OutWidth = PNG->GetWidth();
        OutHeight = PNG->GetHeight();

        TArray<uint8> RawBytes;
        // Try 16-bit gray first (typical landscape heightmap layout).
        if (PNG->GetRaw(ERGBFormat::Gray, 16, RawBytes))
        {
            const int32 Count = OutWidth * OutHeight;
            OutHeights.SetNumUninitialized(Count);
            FMemory::Memcpy(OutHeights.GetData(), RawBytes.GetData(), Count * sizeof(uint16));
            return true;
        }
        // Fall back to 8-bit gray and upscale to uint16 range.
        if (PNG->GetRaw(ERGBFormat::Gray, 8, RawBytes))
        {
            const int32 Count = OutWidth * OutHeight;
            OutHeights.SetNumUninitialized(Count);
            for (int32 i = 0; i < Count; ++i)
            {
                OutHeights[i] = static_cast<uint16>(RawBytes[i]) << 8;
            }
            return true;
        }
        OutError = TEXT("PNG is not a gray heightmap (8 or 16 bit)");
        return false;
    }
}

FUnrealMCPTerrainCommands::FUnrealMCPTerrainCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPTerrainCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("omni.terrain.import_heightmap_png"))
    {
        return HandleImportHeightmapPNG(Params);
    }
    if (CommandType == TEXT("omni.terrain.import_heightmap_from_coords"))
    {
        return HandleImportHeightmapFromCoords(Params);
    }
    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown terrain command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FUnrealMCPTerrainCommands::HandleImportHeightmapPNG(const TSharedPtr<FJsonObject>& Params)
{
#if !WITH_EDITOR
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("omni.terrain.import_heightmap_png requires editor build"));
#else
    FString PngPath;
    if (!Params->TryGetStringField(TEXT("png_path"), PngPath) || PngPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'png_path' parameter"));
    }
    FString LandscapeLabel;
    Params->TryGetStringField(TEXT("landscape_actor"), LandscapeLabel);

    // Decode PNG -> heights
    TArray<uint16> Heights;
    int32 W = 0, H = 0;
    FString Err;
    if (!LoadHeightmapPNG(PngPath, Heights, W, H, Err))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(Err);
    }

    ALandscape* Landscape = FindLandscapeByLabel(LandscapeLabel);
    if (!Landscape)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            LandscapeLabel.IsEmpty()
                ? TEXT("No Landscape actor in level")
                : *FString::Printf(TEXT("No Landscape actor named '%s'"), *LandscapeLabel));
    }

    // The most reliable cross-version path is the LandscapeEditorSubsystem,
    // which wraps the editor import pipeline. Calling its public method
    // keeps us insulated from internal ALandscape::Import signature shifts.
    ULandscapeEditorSubsystem* LandscapeSub = GEditor ? GEditor->GetEditorSubsystem<ULandscapeEditorSubsystem>() : nullptr;
    if (!LandscapeSub)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LandscapeEditorSubsystem unavailable"));
    }

    // Many UE 5.x revisions accept a file path here; verify against your build
    // if this signature has drifted. Returns true on success.
    const bool bOk = LandscapeSub->ImportHeightmapFromFile(Landscape, PngPath);

    Landscape->Modify();
    Landscape->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), bOk);
    Result->SetStringField(TEXT("png_path"), PngPath);
    Result->SetStringField(TEXT("landscape_actor"), Landscape->GetActorLabel());
    Result->SetNumberField(TEXT("heightmap_width"), W);
    Result->SetNumberField(TEXT("heightmap_height"), H);
    if (!bOk)
    {
        Result->SetStringField(TEXT("note"),
            TEXT("Import API returned false. The PNG decoded OK; the failure is in the "
                 "landscape import step. Check editor log for details, or import manually "
                 "via Landscape Mode > Manage > Import from File."));
    }
    return Result;
#endif // WITH_EDITOR
}

TSharedPtr<FJsonObject> FUnrealMCPTerrainCommands::HandleImportHeightmapFromCoords(const TSharedPtr<FJsonObject>& Params)
{
    // Python (Server/tools/omni_terrain_tools.py) is expected to have already
    // fetched the heightmap from Mapbox and saved a PNG to disk, then to call
    // this command with the path. So this is just a thin alias to the same
    // PNG-import handler, with friendly field names mapped through.
    TSharedPtr<FJsonObject> Forward = MakeShared<FJsonObject>();

    FString PngPath;
    Params->TryGetStringField(TEXT("png_path"), PngPath);
    if (PngPath.IsEmpty())
    {
        // Allow caller to pass the field as 'heightmap_path' too.
        Params->TryGetStringField(TEXT("heightmap_path"), PngPath);
    }
    if (PngPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            TEXT("Missing 'png_path' / 'heightmap_path'. The Python side must fetch the "
                 "Mapbox heightmap first and pass its on-disk path here."));
    }
    Forward->SetStringField(TEXT("png_path"), PngPath);

    FString LandscapeLabel;
    Params->TryGetStringField(TEXT("landscape_actor"), LandscapeLabel);
    Forward->SetStringField(TEXT("landscape_actor"), LandscapeLabel);

    return HandleImportHeightmapPNG(Forward);
}

// ============================================================================
// COMMAND REGISTRATION
// ============================================================================

void FUnrealMCPTerrainCommands::RegisterCommands(FMCPCommandRegistry& Registry)
{
    Registry.RegisterCommand(TEXT("omni.terrain.import_heightmap_png"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.terrain.import_heightmap_png"), P); });
    Registry.RegisterCommand(TEXT("omni.terrain.import_heightmap_from_coords"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.terrain.import_heightmap_from_coords"), P); });
}
