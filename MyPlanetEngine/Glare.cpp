// Glare.cpp - see Glare.h.
#include "Glare.h"
#include "GpuHelpers.h"
#include <algorithm>

using Microsoft::WRL::ComPtr;

void Glare::Initialize(ID3D12Device* device, UINT width, UINT height, DXGI_FORMAT format, ID3D12Resource* composite) {
    mWidth = width;
    mHeight = height;
    mFormat = format;
    mComposite = composite;
    mLevels = 0;
    for (UINT side = std::min(width, height); side > 1; side /= 2) ++mLevels;

    CD3DX12_HEAP_PROPERTIES heapProps(D3D12_HEAP_TYPE_DEFAULT);
    const CD3DX12_RESOURCE_DESC desc = CD3DX12_RESOURCE_DESC::Tex2D(format, width / 2, height / 2, 1,
        UINT16(mLevels), 1, 0, D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET);
    Check(device->CreateCommittedResource(&heapProps, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_RENDER_TARGET,
        nullptr, IID_PPV_ARGS(&mGlare)), "Glare creation failed.");
    D3D12_DESCRIPTOR_HEAP_DESC heapDesc = { D3D12_DESCRIPTOR_HEAP_TYPE_RTV, mLevels };
    Check(device->CreateDescriptorHeap(&heapDesc, IID_PPV_ARGS(&mRtvHeap)), "Glare RTV heap creation failed.");
    heapDesc = { D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV, mLevels + 1, D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE };
    Check(device->CreateDescriptorHeap(&heapDesc, IID_PPV_ARGS(&mSrvHeap)), "Glare SRV heap creation failed.");
    mSrvSize = device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
    mRtvSize = device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_RTV);
    for (UINT i = 0; i < mLevels; ++i) {
        D3D12_RENDER_TARGET_VIEW_DESC rtv = {};
        rtv.Format = format;
        rtv.ViewDimension = D3D12_RTV_DIMENSION_TEXTURE2D;
        rtv.Texture2D.MipSlice = i;
        device->CreateRenderTargetView(mGlare.Get(), &rtv,
            CD3DX12_CPU_DESCRIPTOR_HANDLE(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), i, mRtvSize));
        D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
        srv.Format = format;
        srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
        srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        srv.Texture2D.MostDetailedMip = i;
        srv.Texture2D.MipLevels = 1;
        device->CreateShaderResourceView(mGlare.Get(), &srv,
            CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(), i, mSrvSize));
    }
    device->CreateShaderResourceView(composite, nullptr,
        CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(), mLevels, mSrvSize));

    // Signature: the pass's constants (the target's texel, whether it is the last pass), its source.
    CD3DX12_DESCRIPTOR_RANGE source(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 0);
    CD3DX12_ROOT_PARAMETER params[2];
    params[0].InitAsConstants(3, 0, 0, D3D12_SHADER_VISIBILITY_PIXEL);
    params[1].InitAsDescriptorTable(1, &source, D3D12_SHADER_VISIBILITY_PIXEL);
    const CD3DX12_STATIC_SAMPLER_DESC linearClamp(0, D3D12_FILTER_MIN_MAG_MIP_LINEAR, D3D12_TEXTURE_ADDRESS_MODE_CLAMP,
        D3D12_TEXTURE_ADDRESS_MODE_CLAMP, D3D12_TEXTURE_ADDRESS_MODE_CLAMP);
    mRootSignature = CreateRootSignature(device, CD3DX12_ROOT_SIGNATURE_DESC(2, params, 1, &linearClamp));

    ComPtr<ID3DBlob> fullscreen = LoadShader(L"Fullscreen.cso"), down = LoadShader(L"GlareDown.cso"), up = LoadShader(L"GlareUp.cso");
    D3D12_GRAPHICS_PIPELINE_STATE_DESC pso = {};
    pso.pRootSignature = mRootSignature.Get();
    pso.VS = CD3DX12_SHADER_BYTECODE(fullscreen.Get());
    pso.PS = CD3DX12_SHADER_BYTECODE(down.Get());
    pso.RasterizerState = CD3DX12_RASTERIZER_DESC(D3D12_DEFAULT);
    pso.BlendState = CD3DX12_BLEND_DESC(D3D12_DEFAULT);
    pso.DepthStencilState.DepthEnable = FALSE;
    pso.SampleMask = UINT_MAX;
    pso.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
    pso.NumRenderTargets = 1;
    pso.RTVFormats[0] = format;
    pso.SampleDesc.Count = 1;
    Check(device->CreateGraphicsPipelineState(&pso, IID_PPV_ARGS(&mDownPSO)), "Glare PSO creation failed.");
    pso.PS = CD3DX12_SHADER_BYTECODE(up.Get());
    D3D12_RENDER_TARGET_BLEND_DESC& blend = pso.BlendState.RenderTarget[0];
    blend.BlendEnable = TRUE;
    blend.SrcBlend = blend.DestBlend = blend.SrcBlendAlpha = blend.DestBlendAlpha = D3D12_BLEND_ONE; // added to the level
    Check(device->CreateGraphicsPipelineState(&pso, IID_PPV_ARGS(&mUpPSO)), "Glare PSO creation failed.");
}

void Glare::CreateSummedSrv(ID3D12Device* device, D3D12_CPU_DESCRIPTOR_HANDLE destination) const {
    D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
    srv.Format = mFormat;
    srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
    srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    srv.Texture2D.MipLevels = 1;
    device->CreateShaderResourceView(mGlare.Get(), &srv, destination);
}

void Glare::Release(ID3D12GraphicsCommandList* list) {
    const auto b = CD3DX12_RESOURCE_BARRIER::Transition(mGlare.Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,
        D3D12_RESOURCE_STATE_RENDER_TARGET);
    list->ResourceBarrier(1, &b);
}

// Down the levels, then up again; the composite image is only read.
void Glare::Draw(ID3D12GraphicsCommandList* list, ID3D12DescriptorHeap* heap) {
    auto pass = [&](ID3D12PipelineState* pso, D3D12_CPU_DESCRIPTOR_HANDLE target, UINT width, UINT height, UINT source,
                    float apply) {
        const float constants[3] = { 1.0f / width, 1.0f / height, apply };
        const CD3DX12_VIEWPORT viewport(0.0f, 0.0f, float(width), float(height));
        const CD3DX12_RECT scissor(0, 0, LONG(width), LONG(height));
        list->RSSetViewports(1, &viewport);
        list->RSSetScissorRects(1, &scissor);
        list->OMSetRenderTargets(1, &target, FALSE, nullptr);
        list->SetPipelineState(pso);
        list->SetGraphicsRoot32BitConstants(0, 3, constants, 0);
        list->SetGraphicsRootDescriptorTable(1,
            CD3DX12_GPU_DESCRIPTOR_HANDLE(mSrvHeap->GetGPUDescriptorHandleForHeapStart(), source, mSrvSize));
        list->DrawInstanced(3, 1, 0, 0);
    };
    auto level = [&](UINT i) {
        return CD3DX12_CPU_DESCRIPTOR_HANDLE(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), i, mRtvSize);
    };
    auto barrier = [&](ID3D12Resource* resource, D3D12_RESOURCE_STATES from, D3D12_RESOURCE_STATES to, UINT subresource) {
        const auto b = CD3DX12_RESOURCE_BARRIER::Transition(resource, from, to, subresource);
        list->ResourceBarrier(1, &b);
    };
    const auto rt = D3D12_RESOURCE_STATE_RENDER_TARGET, read = D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE;
    const UINT all = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES, w = mWidth / 2, h = mHeight / 2;

    ID3D12DescriptorHeap* glareHeap[] = { mSrvHeap.Get() };
    list->SetDescriptorHeaps(1, glareHeap);
    list->SetGraphicsRootSignature(mRootSignature.Get());
    barrier(mComposite.Get(), rt, read, all);
    for (UINT i = 0; i < mLevels; ++i) { // down: from the composite, then from the previous level
        pass(mDownPSO.Get(), level(i), std::max(w >> i, 1u), std::max(h >> i, 1u), i == 0 ? mLevels : i - 1, 0.0f);
        barrier(mGlare.Get(), rt, read, i);
    }
    for (UINT i = mLevels - 1; i-- > 0;) { // up: each level adds the coarser one, summed so far
        barrier(mGlare.Get(), read, rt, i);
        pass(mUpPSO.Get(), level(i), std::max(w >> i, 1u), std::max(h >> i, 1u), i + 1, 0.0f);
        barrier(mGlare.Get(), rt, read, i);
    }
    barrier(mComposite.Get(), read, rt, all);
    const CD3DX12_VIEWPORT viewport(0.0f, 0.0f, float(mWidth), float(mHeight)); // the full image again for what follows
    const CD3DX12_RECT scissor(0, 0, LONG(mWidth), LONG(mHeight));
    list->RSSetViewports(1, &viewport);
    list->RSSetScissorRects(1, &scissor);
    ID3D12DescriptorHeap* mainHeap[] = { heap };
    list->SetDescriptorHeaps(1, mainHeap);
}
