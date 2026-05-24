// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#include "Commands/UnrealMCPSkelMeshCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "MCPCore.h"

#include "Animation/Skeleton.h"
#include "Engine/SkeletalMeshSocket.h"
#include "UObject/UObjectGlobals.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Editor.h"
#include "EditorAssetLibrary.h"

FUnrealMCPSkelMeshCommands::FUnrealMCPSkelMeshCommands() {}

namespace
{
    USkeleton* LoadSkeleton(const FString& Path)
    {
        UObject* Obj = UEditorAssetLibrary::LoadAsset(Path);
        return Cast<USkeleton>(Obj);
    }

    TSharedPtr<FJsonObject> SocketToJson(const USkeletalMeshSocket* Socket)
    {
        TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
        Obj->SetStringField(TEXT("name"), Socket->SocketName.ToString());
        Obj->SetStringField(TEXT("bone"), Socket->BoneName.ToString());
        TArray<TSharedPtr<FJsonValue>> Loc, Rot, Scale;
        Loc.Add(MakeShared<FJsonValueNumber>(Socket->RelativeLocation.X));
        Loc.Add(MakeShared<FJsonValueNumber>(Socket->RelativeLocation.Y));
        Loc.Add(MakeShared<FJsonValueNumber>(Socket->RelativeLocation.Z));
        Rot.Add(MakeShared<FJsonValueNumber>(Socket->RelativeRotation.Pitch));
        Rot.Add(MakeShared<FJsonValueNumber>(Socket->RelativeRotation.Yaw));
        Rot.Add(MakeShared<FJsonValueNumber>(Socket->RelativeRotation.Roll));
        Scale.Add(MakeShared<FJsonValueNumber>(Socket->RelativeScale.X));
        Scale.Add(MakeShared<FJsonValueNumber>(Socket->RelativeScale.Y));
        Scale.Add(MakeShared<FJsonValueNumber>(Socket->RelativeScale.Z));
        Obj->SetArrayField(TEXT("location"), Loc);
        Obj->SetArrayField(TEXT("rotation"), Rot);
        Obj->SetArrayField(TEXT("scale"), Scale);
        return Obj;
    }
}

TSharedPtr<FJsonObject> FUnrealMCPSkelMeshCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("omni.skelmesh.add_socket"))    return HandleAddSocket(Params);
    if (CommandType == TEXT("omni.skelmesh.list_sockets"))  return HandleListSockets(Params);
    if (CommandType == TEXT("omni.skelmesh.remove_socket")) return HandleRemoveSocket(Params);
    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown skelmesh command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FUnrealMCPSkelMeshCommands::HandleAddSocket(const TSharedPtr<FJsonObject>& Params)
{
    FString SkeletonPath, SocketName, ParentBone;
    if (!Params->TryGetStringField(TEXT("skeleton_path"), SkeletonPath))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'skeleton_path'"));
    if (!Params->TryGetStringField(TEXT("socket_name"), SocketName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'socket_name'"));
    if (!Params->TryGetStringField(TEXT("parent_bone"), ParentBone))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'parent_bone'"));

    USkeleton* Skeleton = LoadSkeleton(SkeletonPath);
    if (!Skeleton)
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Skeleton not found: %s"), *SkeletonPath));

    // Reject duplicate socket names
    if (Skeleton->FindSocket(FName(*SocketName)))
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Socket '%s' already exists on this skeleton"), *SocketName));

    auto GetVec = [&](const FString& Field, const FVector& Default) -> FVector {
        const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
        if (Params->TryGetArrayField(Field, Arr) && Arr && Arr->Num() >= 3)
            return FVector((*Arr)[0]->AsNumber(), (*Arr)[1]->AsNumber(), (*Arr)[2]->AsNumber());
        return Default;
    };
    auto GetRot = [&](const FString& Field) -> FRotator {
        const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
        if (Params->TryGetArrayField(Field, Arr) && Arr && Arr->Num() >= 3)
            return FRotator((*Arr)[0]->AsNumber(), (*Arr)[1]->AsNumber(), (*Arr)[2]->AsNumber());
        return FRotator::ZeroRotator;
    };

    USkeletalMeshSocket* NewSocket = NewObject<USkeletalMeshSocket>(Skeleton);
    NewSocket->SocketName = FName(*SocketName);
    NewSocket->BoneName = FName(*ParentBone);
    NewSocket->RelativeLocation = GetVec(TEXT("relative_location"), FVector::ZeroVector);
    NewSocket->RelativeRotation = GetRot(TEXT("relative_rotation"));
    NewSocket->RelativeScale = GetVec(TEXT("relative_scale"), FVector::OneVector);

    Skeleton->Modify();
    Skeleton->Sockets.Add(NewSocket);
    Skeleton->MarkPackageDirty();
    UEditorAssetLibrary::SaveLoadedAsset(Skeleton, false);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("skeleton"), SkeletonPath);
    Result->SetObjectField(TEXT("socket"), SocketToJson(NewSocket));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPSkelMeshCommands::HandleListSockets(const TSharedPtr<FJsonObject>& Params)
{
    FString SkeletonPath;
    if (!Params->TryGetStringField(TEXT("skeleton_path"), SkeletonPath))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'skeleton_path'"));

    USkeleton* Skeleton = LoadSkeleton(SkeletonPath);
    if (!Skeleton)
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Skeleton not found: %s"), *SkeletonPath));

    TArray<TSharedPtr<FJsonValue>> SocketArray;
    for (USkeletalMeshSocket* Socket : Skeleton->Sockets)
    {
        if (Socket) SocketArray.Add(MakeShared<FJsonValueObject>(SocketToJson(Socket)));
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("skeleton"), SkeletonPath);
    Result->SetNumberField(TEXT("count"), SocketArray.Num());
    Result->SetArrayField(TEXT("sockets"), SocketArray);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPSkelMeshCommands::HandleRemoveSocket(const TSharedPtr<FJsonObject>& Params)
{
    FString SkeletonPath, SocketName;
    if (!Params->TryGetStringField(TEXT("skeleton_path"), SkeletonPath))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'skeleton_path'"));
    if (!Params->TryGetStringField(TEXT("socket_name"), SocketName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'socket_name'"));

    USkeleton* Skeleton = LoadSkeleton(SkeletonPath);
    if (!Skeleton)
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Skeleton not found: %s"), *SkeletonPath));

    const FName Target(*SocketName);
    const int32 BeforeCount = Skeleton->Sockets.Num();
    Skeleton->Modify();
    Skeleton->Sockets.RemoveAll([&](USkeletalMeshSocket* S) {
        return S && S->SocketName == Target;
    });
    const int32 Removed = BeforeCount - Skeleton->Sockets.Num();
    if (Removed > 0)
    {
        Skeleton->MarkPackageDirty();
        UEditorAssetLibrary::SaveLoadedAsset(Skeleton, false);
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("skeleton"), SkeletonPath);
    Result->SetStringField(TEXT("socket"), SocketName);
    Result->SetNumberField(TEXT("removed"), Removed);
    Result->SetNumberField(TEXT("remaining"), Skeleton->Sockets.Num());
    return Result;
}

void FUnrealMCPSkelMeshCommands::RegisterCommands(FMCPCommandRegistry& Registry)
{
    Registry.RegisterCommand(TEXT("omni.skelmesh.add_socket"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.skelmesh.add_socket"), P); });
    Registry.RegisterCommand(TEXT("omni.skelmesh.list_sockets"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.skelmesh.list_sockets"), P); });
    Registry.RegisterCommand(TEXT("omni.skelmesh.remove_socket"),
        [this](const TSharedPtr<FJsonObject>& P) { return HandleCommand(TEXT("omni.skelmesh.remove_socket"), P); });
}
