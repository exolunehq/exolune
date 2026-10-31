#include "FoliageHiZ.h"
#include "GpuHelpers.h"
#include <algorithm>

using Microsoft::WRL::ComPtr;
namespace {
UINT Padded(UINT n) {
    if (!n || n > D3D12_REQ_TEXTURE2D_U_OR_V_DIMENSION)
        throw std::invalid_argument("Hi-Z dimensions are outside the D3D12 texture limit.");
    UINT result = 1;
    while (result < n) result <<= 1;
    return result;
}
UINT Levels(UINT width, UINT height) {
    UINT n = 1;
    while (width > 1 || height > 1) {
        width = std::max(1u, width / 2);
        height = std::max(1u, height / 2);
        ++n;
    }
    return n;
}
}

UINT FoliageHiZ::DescriptorCount(UINT width, UINT height) {
    return 2 + 2 * Levels(Padded(width), Padded(height));
}

void FoliageHiZ::Initialize(ID3D12Device* device, UINT width, UINT height, ID3D12Resource* depth,
                            D3D12_CPU_DESCRIPTOR_HANDLE cpu, D3D12_GPU_DESCRIPTOR_HANDLE gpu) {
    if (!device || !depth) throw std::invalid_argument("Hi-Z needs a device and depth resource.");
    const auto depthDesc = depth->GetDesc();
    if (depthDesc.Dimension != D3D12_RESOURCE_DIMENSION_TEXTURE2D ||
        depthDesc.Width != width || depthDesc.Height != height || depthDesc.DepthOrArraySize != 1 ||
        depthDesc.MipLevels != 1 || depthDesc.SampleDesc.Count != 1 ||
        depthDesc.Format != DXGI_FORMAT_R32_TYPELESS ||
        (depthDesc.Flags & D3D12_RESOURCE_FLAG_DENY_SHADER_RESOURCE))
        throw std::invalid_argument("Hi-Z needs a single-sampled R32_TYPELESS depth texture with an SRV.");
    mSourceWidth = width; mSourceHeight = height;
    mWidth = Padded(width); mHeight = Padded(height);
    mMipCount = Levels(mWidth, mHeight);
    mDepth = depth;
    mBuilt = false;

    const auto heap = CD3DX12_HEAP_PROPERTIES(D3D12_HEAP_TYPE_DEFAULT);
    const auto desc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R32_FLOAT, mWidth, mHeight, 1,
        static_cast<UINT16>(mMipCount), 1, 0, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    Check(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc,
        D3D12_RESOURCE_STATE_UNORDERED_ACCESS, nullptr, IID_PPV_ARGS(&mTexture)), "Hi-Z texture allocation failed.");

    const UINT stride = device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
    auto cpuAt = [&](UINT index) { return CD3DX12_CPU_DESCRIPTOR_HANDLE(cpu, static_cast<INT>(index), stride); };
    auto gpuAt = [&](UINT index) { return CD3DX12_GPU_DESCRIPTOR_HANDLE(gpu, static_cast<INT>(index), stride); };
    D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
    srv.Format = DXGI_FORMAT_R32_FLOAT;
    srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
    srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    srv.Texture2D.MipLevels = 1;
    device->CreateShaderResourceView(depth, &srv, cpuAt(0));
    mDepthSrv = gpuAt(0);
    srv.Texture2D.MipLevels = mMipCount;
    device->CreateShaderResourceView(mTexture.Get(), &srv, cpuAt(1));
    mFullSrv = gpuAt(1);
    D3D12_UNORDERED_ACCESS_VIEW_DESC uav = {};
    uav.Format = DXGI_FORMAT_R32_FLOAT;
    uav.ViewDimension = D3D12_UAV_DIMENSION_TEXTURE2D;
    for (UINT mip = 0; mip < mMipCount; ++mip) {
        srv.Texture2D.MostDetailedMip = mip;
        srv.Texture2D.MipLevels = 1;
        device->CreateShaderResourceView(mTexture.Get(), &srv, cpuAt(2 + mip * 2));
        uav.Texture2D.MipSlice = mip;
        device->CreateUnorderedAccessView(mTexture.Get(), nullptr, &uav, cpuAt(3 + mip * 2));
        mMipSrv[mip] = gpuAt(2 + mip * 2);
        mMipUav[mip] = gpuAt(3 + mip * 2);
    }

    CD3DX12_DESCRIPTOR_RANGE ranges[2];
    ranges[0].Init(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 0);
    ranges[1].Init(D3D12_DESCRIPTOR_RANGE_TYPE_UAV, 1, 0);
    CD3DX12_ROOT_PARAMETER params[3];
    params[0].InitAsConstants(4, 0);
    params[1].InitAsDescriptorTable(1, &ranges[0]);
    params[2].InitAsDescriptorTable(1, &ranges[1]);
    CD3DX12_ROOT_SIGNATURE_DESC rootDesc;
    rootDesc.Init(_countof(params), params);
    mRoot = CreateRootSignature(device, rootDesc);
    D3D12_COMPUTE_PIPELINE_STATE_DESC pso = {};
    pso.pRootSignature = mRoot.Get();
    auto copy = LoadShader(L"FoliageHiZCopy.cso");
    pso.CS = {copy->GetBufferPointer(), copy->GetBufferSize()};
    Check(device->CreateComputePipelineState(&pso, IID_PPV_ARGS(&mCopy)), "Hi-Z copy pipeline creation failed.");
    auto reduce = LoadShader(L"FoliageHiZReduce.cso");
    pso.CS = {reduce->GetBufferPointer(), reduce->GetBufferSize()};
    Check(device->CreateComputePipelineState(&pso, IID_PPV_ARGS(&mReduce)), "Hi-Z reduction pipeline creation failed.");
}

void FoliageHiZ::Build(ID3D12GraphicsCommandList* list, ID3D12Resource* depth) {
    if (!list || !mTexture || depth != mDepth.Get())
        throw std::invalid_argument("Hi-Z build needs its initialized depth resource.");
    auto depthToRead = CD3DX12_RESOURCE_BARRIER::Transition(depth, D3D12_RESOURCE_STATE_DEPTH_WRITE,
        D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
    list->ResourceBarrier(1, &depthToRead);
    if (mBuilt) {
        auto writable = CD3DX12_RESOURCE_BARRIER::Transition(mTexture.Get(), D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,
            D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
        list->ResourceBarrier(1, &writable);
    }
    list->SetComputeRootSignature(mRoot.Get());
    UINT srcWidth = mSourceWidth, srcHeight = mSourceHeight, width = mWidth, height = mHeight;
    for (UINT mip = 0; mip < mMipCount; ++mip) {
        const UINT constants[] = {srcWidth, srcHeight, width, height};
        list->SetPipelineState(mip == 0 ? mCopy.Get() : mReduce.Get());
        list->SetComputeRoot32BitConstants(0, 4, constants, 0);
        list->SetComputeRootDescriptorTable(1, mip == 0 ? mDepthSrv : mMipSrv[mip - 1]);
        list->SetComputeRootDescriptorTable(2, mMipUav[mip]);
        list->Dispatch((width + 7) / 8, (height + 7) / 8, 1);
        auto readable = CD3DX12_RESOURCE_BARRIER::Transition(mTexture.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
            D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE, mip);
        list->ResourceBarrier(1, &readable);
        srcWidth = width; srcHeight = height;
        width = std::max(1u, width / 2); height = std::max(1u, height / 2);
    }
    auto depthToWrite = CD3DX12_RESOURCE_BARRIER::Transition(depth, D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,
        D3D12_RESOURCE_STATE_DEPTH_WRITE);
    list->ResourceBarrier(1, &depthToWrite);
    mBuilt = true;
}
