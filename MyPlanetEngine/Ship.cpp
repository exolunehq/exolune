// Ship.cpp - see Ship.h.
#include "Ship.h"
#include "GpuHelpers.h"
#include <wincodec.h>
#include <algorithm>
#include <cstring>
#include <fstream>

using Microsoft::WRL::ComPtr;
using namespace DirectX;

namespace
{
    template <class T> T Read(const std::vector<uint8_t>& data, size_t& at)
    {
        if (at + sizeof(T) > data.size()) throw std::runtime_error("Ship pack truncated.");
        T value;
        std::memcpy(&value, data.data() + at, sizeof(T));
        at += sizeof(T);
        return value;
    }

    // A PNG from memory to RGBA8, by the Windows Imaging Component.
    void DecodePng(IWICImagingFactory* factory, const std::vector<uint8_t>& png, UINT& width, UINT& height, std::vector<uint8_t>& rgba)
    {
        ComPtr<IWICStream> stream;
        Check(factory->CreateStream(&stream), "WIC stream creation failed.");
        Check(stream->InitializeFromMemory(const_cast<BYTE*>(png.data()), (DWORD)png.size()), "WIC stream failed.");
        ComPtr<IWICBitmapDecoder> decoder;
        Check(factory->CreateDecoderFromStream(stream.Get(), nullptr, WICDecodeMetadataCacheOnDemand, &decoder), "Ship image unreadable.");
        ComPtr<IWICBitmapFrameDecode> frame;
        Check(decoder->GetFrame(0, &frame), "Ship image frame unreadable.");
        ComPtr<IWICFormatConverter> converter;
        Check(factory->CreateFormatConverter(&converter), "WIC converter creation failed.");
        Check(converter->Initialize(frame.Get(), GUID_WICPixelFormat32bppRGBA, WICBitmapDitherTypeNone, nullptr, 0.0,
                                    WICBitmapPaletteTypeCustom), "Ship image conversion failed.");
        Check(converter->GetSize(&width, &height), "Ship image size unreadable.");
        rgba.resize(size_t(width) * height * 4);
        Check(converter->CopyPixels(nullptr, width * 4, (UINT)rgba.size(), rgba.data()), "Ship image copy failed.");
    }

    // The next mip, 2 x 2 texels averaged. ponytail: averages the sRGB codes, a little dark on contrasted images; in
    // linear light if it shows.
    std::vector<uint8_t> HalfImage(const std::vector<uint8_t>& src, UINT width, UINT height)
    {
        const UINT w = std::max(width / 2, 1u), h = std::max(height / 2, 1u);
        std::vector<uint8_t> dst(size_t(w) * h * 4);
        for (UINT y = 0; y < h; ++y)
            for (UINT x = 0; x < w; ++x)
                for (UINT c = 0; c < 4; ++c) {
                    const UINT x0 = std::min(2 * x, width - 1), x1 = std::min(2 * x + 1, width - 1);
                    const UINT y0 = std::min(2 * y, height - 1), y1 = std::min(2 * y + 1, height - 1);
                    const UINT sum = src[(size_t(y0) * width + x0) * 4 + c] + src[(size_t(y0) * width + x1) * 4 + c]
                                   + src[(size_t(y1) * width + x0) * 4 + c] + src[(size_t(y1) * width + x1) * 4 + c];
                    dst[(size_t(y) * w + x) * 4 + c] = uint8_t((sum + 2) / 4);
                }
        return dst;
    }

    XMMATRIX LightFrame(const XMFLOAT3& towards)
    {
        const XMVECTOR d = XMVector3Normalize(XMLoadFloat3(&towards));
        const XMVECTOR centre = XMVectorSet(0.0f, Ship::CentreY, Ship::CentreZ, 1.0f);
        const XMVECTOR up = std::fabs(towards.z) < 0.9f ? XMVectorSet(0, 0, 1, 0) : XMVectorSet(0, 1, 0, 0);
        return XMMatrixLookToLH(centre + d * 20.0f, -d, up)
             * XMMatrixOrthographicLH(2.0f * Ship::Radius, 2.0f * Ship::Radius, 0.1f, 40.0f);
    }
}

bool Ship::Load(const std::wstring& path)
{
    std::ifstream file(path, std::ios::binary);
    if (!file) return false;
    const std::vector<uint8_t> data((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    if (data.size() < 32 || std::memcmp(data.data(), "VSX1", 4) != 0) throw std::runtime_error("Not a ship pack (VSX1).");
    size_t at = 4;
    if (Read<uint32_t>(data, at) != 2) throw std::runtime_error("Ship pack version not supported.");
    const uint32_t vertices = Read<uint32_t>(data, at), indices = Read<uint32_t>(data, at), draws = Read<uint32_t>(data, at);
    const uint32_t materials = Read<uint32_t>(data, at), images = Read<uint32_t>(data, at);
    if (images > MaxImages) throw std::runtime_error("Ship pack has more images than Ship::MaxImages.");
    const size_t vertexBytes = size_t(vertices) * 60, materialSize = 92;
    if (at + vertexBytes + size_t(indices) * 4 > data.size()) throw std::runtime_error("Ship pack truncated.");
    mVertexBytes.assign(data.begin() + at, data.begin() + at + vertexBytes);
    at += vertexBytes;
    mIndices.resize(indices);
    std::memcpy(mIndices.data(), data.data() + at, size_t(indices) * 4);
    at += size_t(indices) * 4;
    for (uint32_t i = 0; i < draws; ++i) {
        Draw d;
        d.first = Read<uint32_t>(data, at); d.count = Read<uint32_t>(data, at); d.material = Read<uint32_t>(data, at);
        mDraws.push_back(d);
    }
    if (at + materials * materialSize > data.size()) throw std::runtime_error("Ship pack truncated.");
    mMaterialBytes.assign(data.begin() + at, data.begin() + at + materials * materialSize);
    for (uint32_t m = 0; m < materials; ++m) {
        uint32_t mode;
        std::memcpy(&mode, mMaterialBytes.data() + m * materialSize + 11 * 4, 4);
        mModes.push_back(mode);
    }
    at += materials * materialSize;
    for (uint32_t i = 0; i < images; ++i) {
        Image image;
        image.srgb = Read<uint32_t>(data, at) != 0;
        const uint32_t bytes = Read<uint32_t>(data, at);
        if (at + bytes > data.size()) throw std::runtime_error("Ship pack truncated.");
        image.png.assign(data.begin() + at, data.begin() + at + bytes);
        at += bytes;
        mImages.push_back(std::move(image));
    }
    for (uint32_t i = 0, count = Read<uint32_t>(data, at); i < count; ++i)
        if (i < 2) pivots[i] = Read<Pivot>(data, at); else at += sizeof(Pivot);
    mLoaded = true;
    return true;
}

D3D12_CPU_DESCRIPTOR_HANDLE Ship::Cpu(UINT i) const
{
    D3D12_CPU_DESCRIPTOR_HANDLE h = mHeap->GetCPUDescriptorHandleForHeapStart();
    h.ptr += SIZE_T(mBase + i) * mStride;
    return h;
}

D3D12_GPU_DESCRIPTOR_HANDLE Ship::Gpu(UINT i) const
{
    D3D12_GPU_DESCRIPTOR_HANDLE h = mHeap->GetGPUDescriptorHandleForHeapStart();
    h.ptr += UINT64(mBase + i) * mStride;
    return h;
}

void Ship::Initialize(ID3D12Device* device, ID3D12GraphicsCommandList* list, ID3D12DescriptorHeap* srvHeap, UINT descriptorBase,
                      UINT width, UINT height, DXGI_FORMAT hdrFormat, DXGI_FORMAT sunFormat)
{
    mHeap = srvHeap;
    mBase = descriptorBase;
    mStride = device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);

    // The overlay: cleared to "no glass", alpha 1, every frame.
    {
        const float none[4] = { 0.0f, 0.0f, 0.0f, 1.0f };
        const CD3DX12_CLEAR_VALUE clear(OverlayFormat, none);
        const CD3DX12_HEAP_PROPERTIES heap(D3D12_HEAP_TYPE_DEFAULT);
        const auto desc = CD3DX12_RESOURCE_DESC::Tex2D(OverlayFormat, width, height, 1, 1, 1, 0, D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET);
        Check(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_RENDER_TARGET, &clear,
                                              IID_PPV_ARGS(&mOverlay)), "Ship overlay creation failed.");
        D3D12_DESCRIPTOR_HEAP_DESC rtv = { D3D12_DESCRIPTOR_HEAP_TYPE_RTV, 1, D3D12_DESCRIPTOR_HEAP_FLAG_NONE, 0 };
        Check(device->CreateDescriptorHeap(&rtv, IID_PPV_ARGS(&mRtvHeap)), "Ship RTV heap creation failed.");
        device->CreateRenderTargetView(mOverlay.Get(), nullptr, mRtvHeap->GetCPUDescriptorHandleForHeapStart());
        device->CreateShaderResourceView(mOverlay.Get(), nullptr, Cpu(MaxImages + 2));
    }
    if (!mLoaded) return;

    // The pack's buffers, through upload buffers kept until the initialisation's list has run.
    auto upload = [&](const void* bytes, size_t size, Resource& target, D3D12_RESOURCE_FLAGS flags = D3D12_RESOURCE_FLAG_NONE) {
        target = CreateBuffer(device, size, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COPY_DEST, flags);
        mUploads.push_back(CreateBuffer(device, size, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ));
        void* mapped = nullptr;
        const CD3DX12_RANGE noRead(0, 0);
        Check(mUploads.back()->Map(0, &noRead, &mapped), "Ship upload map failed.");
        std::memcpy(mapped, bytes, size);
        mUploads.back()->Unmap(0, nullptr);
        list->CopyResource(target.Get(), mUploads.back().Get());
    };
    upload(mVertexBytes.data(), mVertexBytes.size(), mVertices);
    upload(mIndices.data(), mIndices.size() * 4, mIndexBuffer);
    upload(mMaterialBytes.data(), mMaterialBytes.size(), mMaterials);
    const float zeros[12] = {};
    upload(zeros, sizeof(zeros), mWeather, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mIndexView = { mIndexBuffer->GetGPUVirtualAddress(), UINT(mIndices.size() * 4), DXGI_FORMAT_R32_UINT };

    // The images, with their mips; colour and emission in sRGB, the others as data.
    ComPtr<IWICImagingFactory> factory;
    CoInitializeEx(nullptr, COINIT_MULTITHREADED); // S_FALSE or RPC_E_CHANGED_MODE when COM is already on: fine
    Check(CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&factory)), "WIC factory failed.");
    std::vector<CD3DX12_RESOURCE_BARRIER> toRead;
    for (size_t i = 0; i < mImages.size(); ++i) {
        UINT w = 0, h = 0;
        std::vector<uint8_t> level;
        DecodePng(factory.Get(), mImages[i].png, w, h, level);
        UINT mips = 1;
        while ((std::max(w, h) >> mips) > 0) ++mips;
        const DXGI_FORMAT format = mImages[i].srgb ? DXGI_FORMAT_R8G8B8A8_UNORM_SRGB : DXGI_FORMAT_R8G8B8A8_UNORM;
        const auto desc = CD3DX12_RESOURCE_DESC::Tex2D(format, w, h, 1, UINT16(mips));
        const CD3DX12_HEAP_PROPERTIES heap(D3D12_HEAP_TYPE_DEFAULT);
        Check(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_COPY_DEST, nullptr,
                                              IID_PPV_ARGS(&mTextures[i])), "Ship texture creation failed.");
        std::vector<D3D12_PLACED_SUBRESOURCE_FOOTPRINT> footprints(mips);
        std::vector<UINT> rows(mips);
        std::vector<UINT64> rowBytes(mips);
        UINT64 total = 0;
        device->GetCopyableFootprints(&desc, 0, mips, 0, footprints.data(), rows.data(), rowBytes.data(), &total);
        mUploads.push_back(CreateBuffer(device, total, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ));
        uint8_t* mapped = nullptr;
        const CD3DX12_RANGE noRead(0, 0);
        Check(mUploads.back()->Map(0, &noRead, reinterpret_cast<void**>(&mapped)), "Ship texture upload map failed.");
        UINT lw = w, lh = h;
        for (UINT m = 0; m < mips; ++m) {
            for (UINT y = 0; y < rows[m]; ++y)
                std::memcpy(mapped + footprints[m].Offset + size_t(y) * footprints[m].Footprint.RowPitch,
                            level.data() + size_t(y) * lw * 4, size_t(lw) * 4);
            const CD3DX12_TEXTURE_COPY_LOCATION to(mTextures[i].Get(), m), from(mUploads.back().Get(), footprints[m]);
            list->CopyTextureRegion(&to, 0, 0, 0, &from, nullptr);
            if (m + 1 < mips) { level = HalfImage(level, lw, lh); lw = std::max(lw / 2, 1u); lh = std::max(lh / 2, 1u); }
        }
        mUploads.back()->Unmap(0, nullptr);
        device->CreateShaderResourceView(mTextures[i].Get(), nullptr, Cpu(UINT(i)));
        toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mTextures[i].Get(), D3D12_RESOURCE_STATE_COPY_DEST,
                                                              D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE));
    }
    // Unused image slots still need a valid view: the first image again.
    for (size_t i = mImages.size(); i < MaxImages; ++i)
        device->CreateShaderResourceView(mTextures[0].Get(), nullptr, Cpu(UINT(i)));
    const D3D12_RESOURCE_STATES readable = D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE;
    toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mVertices.Get(), D3D12_RESOURCE_STATE_COPY_DEST, readable));
    toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mIndexBuffer.Get(), D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_INDEX_BUFFER));
    toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mMaterials.Get(), D3D12_RESOURCE_STATE_COPY_DEST, readable));
    toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mWeather.Get(), D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_UNORDERED_ACCESS));
    list->ResourceBarrier(UINT(toRead.size()), toRead.data());

    // The canopy's water: its drops and their merges, zero (no drop alive), and its map and film, written by the compute
    // passes, read by the glass.
    {
        const D3D12_RESOURCE_FLAGS uav = D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS;
        mDrops = CreateBuffer(device, DropCount * 32, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COMMON, uav);
        mGathered = CreateBuffer(device, DropCount * 4, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COMMON, uav);
        const CD3DX12_HEAP_PROPERTIES heap(D3D12_HEAP_TYPE_DEFAULT);
        const DXGI_FORMAT formats[2] = { DXGI_FORMAT_R32_UINT, DXGI_FORMAT_R32_FLOAT };
        Resource* maps[2] = { &mWaterMap, &mWaterFilm };
        for (UINT k = 0; k < 2; ++k) {
            const auto desc = CD3DX12_RESOURCE_DESC::Tex2D(formats[k], WaterWidth, WaterHeight, 1, 1, 1, 0, uav);
            Check(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                                                  nullptr, IID_PPV_ARGS(maps[k]->ReleaseAndGetAddressOf())), "Ship water map creation failed.");
            device->CreateUnorderedAccessView(maps[k]->Get(), nullptr, nullptr, Cpu(MaxImages + 4 + k));
            device->CreateShaderResourceView(maps[k]->Get(), nullptr, Cpu(MaxImages + 7 + k));
        }
        D3D12_UNORDERED_ACCESS_VIEW_DESC buffer = {};
        buffer.Format = DXGI_FORMAT_UNKNOWN;
        buffer.ViewDimension = D3D12_UAV_DIMENSION_BUFFER;
        buffer.Buffer.NumElements = DropCount;
        buffer.Buffer.StructureByteStride = 32;
        device->CreateUnorderedAccessView(mDrops.Get(), nullptr, &buffer, Cpu(MaxImages + 3));
        buffer.Buffer.StructureByteStride = 4;
        device->CreateUnorderedAccessView(mGathered.Get(), nullptr, &buffer, Cpu(MaxImages + 6));
    }

    // The two shadow maps: depth, read as floats.
    D3D12_DESCRIPTOR_HEAP_DESC dsv = { D3D12_DESCRIPTOR_HEAP_TYPE_DSV, 2, D3D12_DESCRIPTOR_HEAP_FLAG_NONE, 0 };
    Check(device->CreateDescriptorHeap(&dsv, IID_PPV_ARGS(&mDsvHeap)), "Ship DSV heap creation failed.");
    mDsvStride = device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_DSV);
    for (UINT k = 0; k < 2; ++k) {
        const CD3DX12_CLEAR_VALUE clear(DXGI_FORMAT_D32_FLOAT, 1.0f, 0);
        const CD3DX12_HEAP_PROPERTIES heap(D3D12_HEAP_TYPE_DEFAULT);
        const auto desc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R32_TYPELESS, ShadowSize, ShadowSize, 1, 1, 1, 0,
                                                       D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL);
        Check(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_DEPTH_WRITE, &clear,
                                              IID_PPV_ARGS(&mShadowMaps[k])), "Ship shadow map creation failed.");
        D3D12_DEPTH_STENCIL_VIEW_DESC view = {};
        view.Format = DXGI_FORMAT_D32_FLOAT;
        view.ViewDimension = D3D12_DSV_DIMENSION_TEXTURE2D;
        D3D12_CPU_DESCRIPTOR_HANDLE h = mDsvHeap->GetCPUDescriptorHandleForHeapStart();
        h.ptr += SIZE_T(k) * mDsvStride;
        device->CreateDepthStencilView(mShadowMaps[k].Get(), &view, h);
        D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
        srv.Format = DXGI_FORMAT_R32_FLOAT;
        srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
        srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        srv.Texture2D.MipLevels = 1;
        device->CreateShaderResourceView(mShadowMaps[k].Get(), &srv, Cpu(MaxImages + k));
    }

    mConstantsBuffer = CreateBuffer(device, (sizeof(Constants) + 255) & ~255u, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
    const CD3DX12_RANGE noRead(0, 0);
    Check(mConstantsBuffer->Map(0, &noRead, reinterpret_cast<void**>(&mConstants)), "Ship constants map failed.");
    *mConstants = {};

    // One root signature for every pass: frame constants (b0), the ship's (b3), the draw's (b2), its vertices and
    // materials, the atmosphere tables, the climate map, the planet map, the images and shadow maps, the weather state,
    // the composite image for the glass's refraction, the clouds' frame (b1) and textures, for the weather, then the
    // water's UAVs (u1-u4) and its map and film for the glass (t48, t49), and the terrain's mesh for the weather (t50).
    CD3DX12_DESCRIPTOR_RANGE luts(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 3, 1), climate(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 10),
        planetMap(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 29), images(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, MaxImages + 2, 32),
        composite(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 47), planet(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 4, 24),
        water(D3D12_DESCRIPTOR_RANGE_TYPE_UAV, 4, 1), waterRead(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 2, 48);
    CD3DX12_ROOT_PARAMETER params[17];
    params[0].InitAsConstantBufferView(0);
    params[1].InitAsConstantBufferView(3);
    params[2].InitAsConstants(4, 2);
    params[3].InitAsShaderResourceView(30);
    params[4].InitAsShaderResourceView(31);
    params[5].InitAsDescriptorTable(1, &luts);
    params[6].InitAsDescriptorTable(1, &climate);
    params[7].InitAsDescriptorTable(1, &planetMap);
    params[8].InitAsDescriptorTable(1, &images);
    params[9].InitAsShaderResourceView(46);
    params[10].InitAsUnorderedAccessView(0);
    params[11].InitAsDescriptorTable(1, &composite);
    params[12].InitAsConstantBufferView(1);
    params[13].InitAsDescriptorTable(1, &planet);
    params[14].InitAsDescriptorTable(1, &water);
    params[15].InitAsDescriptorTable(1, &waterRead);
    params[16].InitAsShaderResourceView(50);
    CD3DX12_STATIC_SAMPLER_DESC samplers[6] = {
        CD3DX12_STATIC_SAMPLER_DESC(0, D3D12_FILTER_MIN_MAG_MIP_LINEAR, D3D12_TEXTURE_ADDRESS_MODE_CLAMP,
                                    D3D12_TEXTURE_ADDRESS_MODE_CLAMP, D3D12_TEXTURE_ADDRESS_MODE_CLAMP),
        CD3DX12_STATIC_SAMPLER_DESC(1, D3D12_FILTER_ANISOTROPIC),
        CD3DX12_STATIC_SAMPLER_DESC(4, D3D12_FILTER_COMPARISON_MIN_MAG_LINEAR_MIP_POINT, D3D12_TEXTURE_ADDRESS_MODE_CLAMP,
                                    D3D12_TEXTURE_ADDRESS_MODE_CLAMP, D3D12_TEXTURE_ADDRESS_MODE_CLAMP, 0.0f, 1,
                                    D3D12_COMPARISON_FUNC_LESS_EQUAL),
        CD3DX12_STATIC_SAMPLER_DESC(5, D3D12_FILTER_ANISOTROPIC),
        CD3DX12_STATIC_SAMPLER_DESC(2, D3D12_FILTER_MIN_MAG_MIP_LINEAR), // the clouds' noise, wrapping
        CD3DX12_STATIC_SAMPLER_DESC(3, D3D12_FILTER_MIN_MAG_MIP_LINEAR, D3D12_TEXTURE_ADDRESS_MODE_WRAP, // their weather map
                                    D3D12_TEXTURE_ADDRESS_MODE_CLAMP, D3D12_TEXTURE_ADDRESS_MODE_CLAMP) };
    mRoot = CreateRootSignature(device, CD3DX12_ROOT_SIGNATURE_DESC(17, params, 6, samplers));

    const ComPtr<ID3DBlob> vs = LoadShader(L"ShipVertex.cso"), shadowVs = LoadShader(L"ShipShadow.cso"),
        ps = LoadShader(L"ShipPixel.cso"), glassPs = LoadShader(L"ShipGlass.cso"), weatherCs = LoadShader(L"ShipWeather.cso");
    D3D12_GRAPHICS_PIPELINE_STATE_DESC desc = {};
    desc.pRootSignature = mRoot.Get();
    desc.VS = CD3DX12_SHADER_BYTECODE(vs.Get());
    desc.PS = CD3DX12_SHADER_BYTECODE(ps.Get());
    desc.RasterizerState = CD3DX12_RASTERIZER_DESC(D3D12_DEFAULT);
    desc.RasterizerState.CullMode = D3D12_CULL_MODE_NONE;
    desc.BlendState = CD3DX12_BLEND_DESC(D3D12_DEFAULT);
    desc.DepthStencilState = CD3DX12_DEPTH_STENCIL_DESC(D3D12_DEFAULT);
    desc.DepthStencilState.DepthFunc = D3D12_COMPARISON_FUNC_GREATER; // reversed Z, as the scene
    desc.SampleMask = UINT_MAX;
    desc.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
    desc.NumRenderTargets = 2;
    desc.RTVFormats[0] = hdrFormat;
    desc.RTVFormats[1] = sunFormat;
    desc.DSVFormat = DXGI_FORMAT_D32_FLOAT;
    desc.SampleDesc.Count = 1;
    Check(device->CreateGraphicsPipelineState(&desc, IID_PPV_ARGS(&mOpaquePSO)), "Ship PSO creation failed.");

    // The shadow maps: standard Z, nearer is smaller, a slope-scaled bias against acne.
    D3D12_GRAPHICS_PIPELINE_STATE_DESC shadow = desc;
    shadow.VS = CD3DX12_SHADER_BYTECODE(shadowVs.Get());
    shadow.PS = {};
    shadow.NumRenderTargets = 0;
    shadow.RTVFormats[0] = shadow.RTVFormats[1] = DXGI_FORMAT_UNKNOWN;
    shadow.DepthStencilState.DepthFunc = D3D12_COMPARISON_FUNC_LESS;
    shadow.RasterizerState.DepthBias = 200;
    shadow.RasterizerState.SlopeScaledDepthBias = 2.0f;
    Check(device->CreateGraphicsPipelineState(&shadow, IID_PPV_ARGS(&mShadowPSO)), "Ship shadow PSO creation failed.");

    // The glass: screen = smoothed * alpha + rgb, layer after layer, depth tested against the scene, not written.
    D3D12_GRAPHICS_PIPELINE_STATE_DESC glass = desc;
    glass.PS = CD3DX12_SHADER_BYTECODE(glassPs.Get());
    glass.NumRenderTargets = 1;
    glass.RTVFormats[0] = OverlayFormat;
    glass.RTVFormats[1] = DXGI_FORMAT_UNKNOWN;
    glass.DepthStencilState.DepthWriteMask = D3D12_DEPTH_WRITE_MASK_ZERO;
    D3D12_RENDER_TARGET_BLEND_DESC& blend = glass.BlendState.RenderTarget[0];
    blend.BlendEnable = TRUE;
    blend.SrcBlend = D3D12_BLEND_ONE;
    blend.DestBlend = D3D12_BLEND_SRC_ALPHA;
    blend.BlendOp = D3D12_BLEND_OP_ADD;
    blend.SrcBlendAlpha = D3D12_BLEND_ZERO;
    blend.DestBlendAlpha = D3D12_BLEND_SRC_ALPHA;
    blend.BlendOpAlpha = D3D12_BLEND_OP_ADD;
    Check(device->CreateGraphicsPipelineState(&glass, IID_PPV_ARGS(&mGlassPSO)), "Ship glass PSO creation failed.");

    // The jets (ShipPlume.hlsli): the same blending, boxes marched to the scene's distance, without depth.
    const ComPtr<ID3DBlob> plumeVs = LoadShader(L"ShipPlumeVertex.cso"), plumePs = LoadShader(L"ShipPlumePixel.cso");
    D3D12_GRAPHICS_PIPELINE_STATE_DESC plume = glass;
    plume.VS = CD3DX12_SHADER_BYTECODE(plumeVs.Get());
    plume.PS = CD3DX12_SHADER_BYTECODE(plumePs.Get());
    plume.DepthStencilState.DepthEnable = FALSE;
    Check(device->CreateGraphicsPipelineState(&plume, IID_PPV_ARGS(&mPlumePSO)), "Ship plume PSO creation failed.");

    D3D12_COMPUTE_PIPELINE_STATE_DESC compute = {};
    compute.pRootSignature = mRoot.Get();
    compute.CS = CD3DX12_SHADER_BYTECODE(weatherCs.Get());
    Check(device->CreateComputePipelineState(&compute, IID_PPV_ARGS(&mWeatherPSO)), "Ship weather PSO creation failed.");
    const wchar_t* waterShaders[3] = { L"ShipWaterMove.cso", L"ShipWaterClear.cso", L"ShipWaterSplat.cso" };
    for (UINT k = 0; k < 3; ++k) {
        const ComPtr<ID3DBlob> cs = LoadShader(waterShaders[k]);
        compute.CS = CD3DX12_SHADER_BYTECODE(cs.Get());
        Check(device->CreateComputePipelineState(&compute, IID_PPV_ARGS(&mWaterPSO[k])), "Ship water PSO creation failed.");
    }
    mReady = true;
}

void Ship::SetLights(const XMFLOAT3& sun, const XMFLOAT3& up)
{
    XMStoreFloat4x4(&mConstants->shadow[0], XMMatrixTranspose(LightFrame(sun)));
    XMStoreFloat4x4(&mConstants->shadow[1], XMMatrixTranspose(LightFrame(up)));
}

void Ship::Bind(ID3D12GraphicsCommandList* list, const Tables& t, bool compute) const
{
    if (compute) {
        list->SetComputeRootSignature(mRoot.Get());
        list->SetComputeRootConstantBufferView(0, t.frame);
        list->SetComputeRootConstantBufferView(1, mConstantsBuffer->GetGPUVirtualAddress());
        list->SetComputeRootShaderResourceView(3, mVertices->GetGPUVirtualAddress());
        list->SetComputeRootShaderResourceView(4, mMaterials->GetGPUVirtualAddress());
        list->SetComputeRootDescriptorTable(5, t.luts);
        list->SetComputeRootDescriptorTable(6, Gpu(MaxImages + 9));
        list->SetComputeRootDescriptorTable(7, t.planetMap);
        list->SetComputeRootDescriptorTable(8, Gpu(0));
        list->SetComputeRootUnorderedAccessView(10, mWeather->GetGPUVirtualAddress());
        list->SetComputeRootDescriptorTable(11, t.composite);
        list->SetComputeRootShaderResourceView(16, t.terrain);
        list->SetComputeRootConstantBufferView(12, t.cloudFrame);
        list->SetComputeRootDescriptorTable(13, t.cloudTextures);
        return;
    }
    list->SetGraphicsRootSignature(mRoot.Get());
    list->SetGraphicsRootConstantBufferView(0, t.frame);
    list->SetGraphicsRootConstantBufferView(1, mConstantsBuffer->GetGPUVirtualAddress());
    list->SetGraphicsRootShaderResourceView(3, mVertices->GetGPUVirtualAddress());
    list->SetGraphicsRootShaderResourceView(4, mMaterials->GetGPUVirtualAddress());
    list->SetGraphicsRootDescriptorTable(5, t.luts);
    list->SetGraphicsRootDescriptorTable(6, Gpu(MaxImages + 9));
    list->SetGraphicsRootDescriptorTable(7, t.planetMap);
    list->SetGraphicsRootDescriptorTable(8, Gpu(0));
    list->SetGraphicsRootShaderResourceView(9, mWeather->GetGPUVirtualAddress());
    list->SetGraphicsRootDescriptorTable(11, t.composite);
    list->SetGraphicsRootDescriptorTable(15, Gpu(MaxImages + 7));
    list->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    list->IASetIndexBuffer(&mIndexView);
}

void Ship::DrawShadows(ID3D12GraphicsCommandList* list, const Tables& t)
{
    if (mShadowsReadable) {
        const CD3DX12_RESOURCE_BARRIER toWrite[2] = {
            CD3DX12_RESOURCE_BARRIER::Transition(mShadowMaps[0].Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_DEPTH_WRITE),
            CD3DX12_RESOURCE_BARRIER::Transition(mShadowMaps[1].Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_DEPTH_WRITE) };
        list->ResourceBarrier(2, toWrite);
    }
    Bind(list, t, false);
    list->SetPipelineState(mShadowPSO.Get());
    const CD3DX12_VIEWPORT viewport(0.0f, 0.0f, float(ShadowSize), float(ShadowSize));
    const CD3DX12_RECT scissor(0, 0, LONG(ShadowSize), LONG(ShadowSize));
    list->RSSetViewports(1, &viewport);
    list->RSSetScissorRects(1, &scissor);
    for (UINT k = 0; k < 2; ++k) {
        D3D12_CPU_DESCRIPTOR_HANDLE dsv = mDsvHeap->GetCPUDescriptorHandleForHeapStart();
        dsv.ptr += SIZE_T(k) * mDsvStride;
        list->OMSetRenderTargets(0, nullptr, FALSE, &dsv);
        list->ClearDepthStencilView(dsv, D3D12_CLEAR_FLAG_DEPTH, 1.0f, 0, 0, nullptr);
        list->SetGraphicsRoot32BitConstant(2, k, 1);
        for (const Draw& d : mDraws)
            if (mModes[d.material] == 0)
                list->DrawIndexedInstanced(d.count, 1, d.first, 0, 0);
    }
    const CD3DX12_RESOURCE_BARRIER toRead[2] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mShadowMaps[0].Get(), D3D12_RESOURCE_STATE_DEPTH_WRITE, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mShadowMaps[1].Get(), D3D12_RESOURCE_STATE_DEPTH_WRITE, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE) };
    list->ResourceBarrier(2, toRead);
    mShadowsReadable = true;
}

void Ship::DrawOpaque(ID3D12GraphicsCommandList* list, const Tables& t)
{
    Bind(list, t, false);
    list->SetPipelineState(mOpaquePSO.Get());
    for (const Draw& d : mDraws)
        if (mModes[d.material] == 0) {
            list->SetGraphicsRoot32BitConstant(2, d.material, 0);
            list->DrawIndexedInstanced(d.count, 1, d.first, 0, 0);
        }
}

void Ship::UpdateWeather(ID3D12GraphicsCommandList* list, const Tables& t)
{
    if (mWeatherReadable) {
        const auto toUav = CD3DX12_RESOURCE_BARRIER::Transition(mWeather.Get(),
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
        list->ResourceBarrier(1, &toUav);
    }
    Bind(list, t, true);
    list->SetPipelineState(mWeatherPSO.Get());
    list->Dispatch(1, 1, 1);
    const auto uavDone = CD3DX12_RESOURCE_BARRIER::UAV(nullptr);
    list->ResourceBarrier(1, &uavDone);

    // The canopy's water (ShipWater.hlsli): move the drops, clear the map, draw them into it; the glass then reads it.
    const D3D12_RESOURCE_STATES read = D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE;
    if (mWaterReadable) {
        const CD3DX12_RESOURCE_BARRIER toWrite[2] = {
            CD3DX12_RESOURCE_BARRIER::Transition(mWaterMap.Get(), read, D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
            CD3DX12_RESOURCE_BARRIER::Transition(mWaterFilm.Get(), read, D3D12_RESOURCE_STATE_UNORDERED_ACCESS) };
        list->ResourceBarrier(2, toWrite);
    }
    list->SetComputeRootDescriptorTable(14, Gpu(MaxImages + 3));
    list->SetPipelineState(mWaterPSO[0].Get());
    list->Dispatch(DropCount / 64, 1, 1);
    list->ResourceBarrier(1, &uavDone);
    list->SetPipelineState(mWaterPSO[1].Get());
    list->Dispatch((WaterWidth + 7) / 8, (WaterHeight + 7) / 8, 1);
    list->ResourceBarrier(1, &uavDone);
    list->SetPipelineState(mWaterPSO[2].Get());
    list->Dispatch(DropCount / 64, 1, 1);
    const CD3DX12_RESOURCE_BARRIER toRead[3] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mWeather.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mWaterMap.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS, read),
        CD3DX12_RESOURCE_BARRIER::Transition(mWaterFilm.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS, read) };
    list->ResourceBarrier(3, toRead);
    mWeatherReadable = mWaterReadable = true;
}

void Ship::ClearOverlay(ID3D12GraphicsCommandList* list)
{
    const float none[4] = { 0.0f, 0.0f, 0.0f, 1.0f };
    list->ClearRenderTargetView(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), none, 0, nullptr);
}

void Ship::DrawGlass(ID3D12GraphicsCommandList* list, const Tables& t, D3D12_CPU_DESCRIPTOR_HANDLE dsv)
{
    const D3D12_CPU_DESCRIPTOR_HANDLE rtv = mRtvHeap->GetCPUDescriptorHandleForHeapStart();
    list->OMSetRenderTargets(1, &rtv, FALSE, &dsv);
    Bind(list, t, false);
    list->SetPipelineState(mGlassPSO.Get());
    for (uint32_t mode : { 2u, 1u }) // the canopy, then the combiner under it
        for (const Draw& d : mDraws)
            if (mModes[d.material] == mode) {
                list->SetGraphicsRoot32BitConstant(2, d.material, 0);
                list->DrawIndexedInstanced(d.count, 1, d.first, 0, 0);
            }
    list->SetPipelineState(mPlumePSO.Get()); // then the jets, 3 engines and 10 attitude jets
    list->DrawInstanced(36, 13, 0, 0);
}

void Ship::OverlayToRead(ID3D12GraphicsCommandList* list)
{
    const auto b = CD3DX12_RESOURCE_BARRIER::Transition(mOverlay.Get(), D3D12_RESOURCE_STATE_RENDER_TARGET, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
    list->ResourceBarrier(1, &b);
}

void Ship::OverlayToTarget(ID3D12GraphicsCommandList* list)
{
    const auto b = CD3DX12_RESOURCE_BARRIER::Transition(mOverlay.Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_RENDER_TARGET);
    list->ResourceBarrier(1, &b);
}
