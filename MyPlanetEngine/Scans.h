// Scans.h - the photo scans laid over the generated materials (docs/log/spec-hybride-scans.md,
// docs/spec-parois-minerales.md).
#pragma once

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <wrl.h>
#include <d3d12.h>
#include <string>
#include <vector>

// The scans into their slices of the materials' two textures, every mip, as MaterialGenerator.hlsl would write them,
// read from `folder`, or the first folder named scans above the executable when empty. The copies go on the command
// list, from upload buffers kept in `uploads` until it has run. Returns the scans it could not read.
std::wstring LoadScans(ID3D12Device* device, ID3D12GraphicsCommandList* list, ID3D12Resource* const materials[2],
                       UINT size, UINT mips, const std::wstring& folder,
                       std::vector<Microsoft::WRL::ComPtr<ID3D12Resource>>& uploads);
