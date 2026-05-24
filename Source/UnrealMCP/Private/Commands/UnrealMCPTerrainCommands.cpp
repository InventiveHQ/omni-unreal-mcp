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
#include "LandscapeEdit.h"
#include "LandscapeStreamingProxy.h"
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

    // Apply via FLandscapeEditDataInterface — in-place update on existing landscape
    // components. Heightmap dims must equal landscape vertex extent +1 (the +1 is
    // because landscape Min/Max are inclusive). For a World Partition landscape
    // we walk all loaded streaming proxies; unloaded cells get a warning but the
    // op still succeeds for what's loaded.
    ULandscapeInfo* LandscapeInfo = Landscape->GetLandscapeInfo();
    if (!LandscapeInfo)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Landscape has no LandscapeInfo (uninitialized)"));
    }

    FIntRect Extent;
    if (!LandscapeInfo->GetLandscapeExtent(Extent.Min.X, Extent.Min.Y, Extent.Max.X, Extent.Max.Y))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Could not query landscape extent (no loaded proxies?)"));
    }
    const int32 ExpectedW = (Extent.Max.X - Extent.Min.X) + 1;
    const int32 ExpectedH = (Extent.Max.Y - Extent.Min.Y) + 1;

    if (W != ExpectedW || H != ExpectedH)
    {
        TSharedPtr<FJsonObject> Resp = MakeShared<FJsonObject>();
        Resp->SetBoolField(TEXT("success"), false);
        Resp->SetStringField(TEXT("error"),
            FString::Printf(TEXT("Heightmap dims %dx%d do not match landscape vertex extent %dx%d "
                "(min %d,%d max %d,%d). Resize PNG to match before re-running."),
                W, H, ExpectedW, ExpectedH, Extent.Min.X, Extent.Min.Y, Extent.Max.X, Extent.Max.Y));
        Resp->SetNumberField(TEXT("expected_width"), ExpectedW);
        Resp->SetNumberField(TEXT("expected_height"), ExpectedH);
        Resp->SetNumberField(TEXT("got_width"), W);
        Resp->SetNumberField(TEXT("got_height"), H);
        return Resp;
    }

    // SetHeightData expects the data origin at (X1,Y1) — match the landscape's
    // min coords so writes land on the correct vertex columns/rows.
    {
        FLandscapeEditDataInterface LandscapeEdit(LandscapeInfo);
        LandscapeEdit.SetHeightData(
            Extent.Min.X, Extent.Min.Y, Extent.Max.X, Extent.Max.Y,
            Heights.GetData(), /*InStride*/ 0,
            /*InCalcNormals*/ true);
        LandscapeEdit.Flush();
    }

    // Reregister all components on the master + every loaded proxy so the new
    // heights become visible. Without this the editor viewport still draws stale
    // collision/render data until something else triggers a refresh.
    Landscape->ReregisterAllComponents();
    int32 ReregProxyCount = 0;
    LandscapeInfo->ForEachLandscapeProxy([&](ALandscapeProxy* Proxy) -> bool
    {
        if (Proxy && Proxy != Landscape)
        {
            Proxy->ReregisterAllComponents();
            ++ReregProxyCount;
        }
        return true;
    });

    // Mark the landscape file path so the editor "Reimport" button works later
    Landscape->ReimportHeightmapFilePath = PngPath;

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("png_path"), PngPath);
    Result->SetStringField(TEXT("landscape_actor"), Landscape->GetActorLabel());
    Result->SetNumberField(TEXT("heightmap_width"), W);
    Result->SetNumberField(TEXT("heightmap_height"), H);
    Result->SetNumberField(TEXT("landscape_min_x"), Extent.Min.X);
    Result->SetNumberField(TEXT("landscape_min_y"), Extent.Min.Y);
    Result->SetNumberField(TEXT("landscape_max_x"), Extent.Max.X);
    Result->SetNumberField(TEXT("landscape_max_y"), Extent.Max.Y);
    Result->SetNumberField(TEXT("reregistered_proxies"), ReregProxyCount);
    Result->SetStringField(TEXT("note"),
        TEXT("Heightmap applied via FLandscapeEditDataInterface::SetHeightData. "
             "For unloaded World Partition cells, reload the region and reimport."));
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
