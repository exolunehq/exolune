// GpuHelpers.h - small Direct3D 12 helpers shared by the engine's modules.
#pragma once

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <wrl.h>
#include <d3d12.h>
#include <d3dcompiler.h>
#include <stdexcept>
#include <string>
#include "d3dx12.h"

inline void Check(HRESULT hr, const char* what)
{
    if (FAILED(hr)) throw std::runtime_error(what);
}

// A file at `relative` in the first folder above the executable that has it; empty when none.
inline std::wstring FindAbove(const std::wstring& relative)
{
    wchar_t exe[MAX_PATH];
    GetModuleFileNameW(nullptr, exe, MAX_PATH);
    std::wstring folder(exe);
    for (size_t cut = folder.find_last_of(L"\\/"); cut != std::wstring::npos; cut = folder.find_last_of(L"\\/")) {
        folder.resize(cut);
        const std::wstring candidate = folder + L"\\" + relative;
        if (GetFileAttributesW(candidate.c_str()) != INVALID_FILE_ATTRIBUTES) return candidate;
    }
    return {};
}

// Shaders are compiled by the build (FxCompile) into .cso files next to the executable:
// the relief's compute shader takes about a minute to compile.
inline Microsoft::WRL::ComPtr<ID3DBlob> LoadShader(const wchar_t* name)
{
    wchar_t exePath[MAX_PATH];
    GetModuleFileNameW(nullptr, exePath, MAX_PATH);
    std::wstring path(exePath);
    path = path.substr(0, path.find_last_of(L"\\/") + 1) + name;
    Microsoft::WRL::ComPtr<ID3DBlob> code;
    Check(D3DReadFileToBlob(path.c_str(), &code), "Compiled shader not found next to the executable: rebuild the project.");
    return code;
}

inline Microsoft::WRL::ComPtr<ID3D12RootSignature> CreateRootSignature(ID3D12Device* device, const D3D12_ROOT_SIGNATURE_DESC& desc)
{
    Microsoft::WRL::ComPtr<ID3DBlob> blob, errors;
    Check(D3D12SerializeRootSignature(&desc, D3D_ROOT_SIGNATURE_VERSION_1, &blob, &errors), "Root signature serialization failed.");
    Microsoft::WRL::ComPtr<ID3D12RootSignature> rootSignature;
    Check(device->CreateRootSignature(0, blob->GetBufferPointer(), blob->GetBufferSize(), IID_PPV_ARGS(&rootSignature)),
        "Root signature creation failed.");
    return rootSignature;
}

inline Microsoft::WRL::ComPtr<ID3D12Resource> CreateBuffer(ID3D12Device* device, UINT64 size, D3D12_HEAP_TYPE heapType,
    D3D12_RESOURCE_STATES state, D3D12_RESOURCE_FLAGS flags = D3D12_RESOURCE_FLAG_NONE)
{
    CD3DX12_HEAP_PROPERTIES heap(heapType);
    CD3DX12_RESOURCE_DESC desc = CD3DX12_RESOURCE_DESC::Buffer(size, flags);
    Microsoft::WRL::ComPtr<ID3D12Resource> buffer;
    Check(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc, state, nullptr, IID_PPV_ARGS(&buffer)),
        "Buffer creation failed.");
    return buffer;
}
