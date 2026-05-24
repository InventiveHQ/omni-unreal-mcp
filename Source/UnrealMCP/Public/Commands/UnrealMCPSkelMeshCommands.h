// Copyright (c) 2026 Inventive HQ. MIT License — see LICENSE.

#pragma once

#include "CoreMinimal.h"
#include "Json.h"

class FMCPCommandRegistry;

/**
 * Skeleton socket commands. C++ handler unblocks Python's read-only
 * USkeletalMeshSocket::SocketName UPROPERTY by mutating the skeleton
 * directly from native code.
 *
 * Commands:
 *   omni.skelmesh.add_socket
 *   omni.skelmesh.list_sockets
 *   omni.skelmesh.remove_socket
 */
class UNREALMCP_API FUnrealMCPSkelMeshCommands
{
public:
    FUnrealMCPSkelMeshCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);
    void RegisterCommands(FMCPCommandRegistry& Registry);

private:
    TSharedPtr<FJsonObject> HandleAddSocket(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleListSockets(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRemoveSocket(const TSharedPtr<FJsonObject>& Params);
};
