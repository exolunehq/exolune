// Ship.h - the player's ship (assets/vaisseau): the engine's pack of it (paquet_moteur.py), its opaque surfaces drawn in the
// scene, its own two shadow maps, the canopy's weather under the clouds (ShipWeather.hlsl) and the climate it reads, and its
// glass drawn into an overlay that the tone map applies after the temporal smoothing (ToneMap.hlsl). Must match Ship.hlsli.
#pragma once
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <d3d12.h>
#include <DirectXMath.h>
#include <wrl.h>
#include <cstdint>
#include <string>
#include <vector>

class Ship {
public:
    static constexpr UINT MaxImages = 12;                    // Ship.hlsli: shipImages[12]
    // The images, the two shadow maps, the overlay, then the water's: its drops, map, film and merges as UAVs, its map and
    // film as SRVs; then the climate map (Climate.hlsli), its view made by D3DApp.
    static constexpr UINT DescriptorCount = MaxImages + 10;
    // The canopy's water (ShipWater.hlsli): the map over both panes at 1.2 mm, the simulated drops. Ship.hlsli's WATER_SIZE.
    static constexpr UINT WaterWidth = 1584, WaterHeight = 3660, DropCount = 8192;
    static constexpr UINT ShadowSize = 2048;
    static constexpr DXGI_FORMAT OverlayFormat = DXGI_FORMAT_R16G16B16A16_FLOAT;
    // The ship frame's point and radius that the shadow maps cover (m); Ship.hlsli's SHIP_CENTRE, SHIP_RADIUS.
    static constexpr float CentreY = -2.15f, CentreZ = 0.05f, Radius = 6.7f;

    struct Constants {
        DirectX::XMFLOAT4X4 model;     // ship frame -> face-local, camera-relative, transposed for HLSL
        DirectX::XMFLOAT4X4 shadow[2]; // ship frame -> the sun's and the overhead map's clip space, transposed
        DirectX::XMFLOAT4 sun, up, air, velocity;
        DirectX::XMFLOAT4 options; // x: 1 with the head-up display
        DirectX::XMFLOAT4 thrust;  // x: the main engines, 0 to 1; y: roll right, z: lift, w: slide right, -1 to 1 (ShipPlume)
        DirectX::XMFLOAT4 turn;    // x: pitch up, y: yaw right, -1 to 1; z: clock (s), wraps at 3600
        DirectX::XMFLOAT4 course;  // the dashboard (ShipScreens.hlsli): heading, latitude, longitude (deg); w: the ground (km)
        DirectX::XMFLOAT4 gauges;  // x: the gas, 0 to 1
        DirectX::XMFLOAT4X4 pose[2]; // ship frame -> ship frame: the stick, the throttle (Ship.hlsli's ShipPose), transposed
    };
    // The moving parts' pivots, ship frame, from the pack (pieces_mobiles.py): the stick's twist axis, the throttle's.
    struct Pivot { DirectX::XMFLOAT3 point, axis; };
    Pivot pivots[2] = {};

    // The pack's path: false, and the ship stays out, when it cannot be read.
    bool Load(const std::wstring& path);
    // Creates the GPU side; the overlay always exists, so that the tone map can read it without a ship.
    void Initialize(ID3D12Device*, ID3D12GraphicsCommandList*, ID3D12DescriptorHeap* srvHeap, UINT descriptorBase,
                    UINT width, UINT height, DXGI_FORMAT hdrFormat, DXGI_FORMAT sunFormat);
    // Where D3DApp puts the climate map's view, for the canopy's temperature (ShipWeather.hlsl).
    D3D12_CPU_DESCRIPTOR_HANDLE ClimateDescriptor() const { return Cpu(MaxImages + 9); }
    void ReleaseUploads() { mUploads.clear(); }
    bool Ready() const { return mReady; }
    Constants& Frame() { return *mConstants; }
    // The shadow maps' frames from the sun's and the vertical's directions, in the ship frame.
    void SetLights(const DirectX::XMFLOAT3& sun, const DirectX::XMFLOAT3& up);

    struct Tables {
        D3D12_GPU_VIRTUAL_ADDRESS frame, cloudFrame; // the clouds' frame, b1 (Clouds.hlsli)
        D3D12_GPU_VIRTUAL_ADDRESS terrain; // the mesh after its horizon pass: the relief's shadow on the ship (ShipWeather)
        D3D12_GPU_DESCRIPTOR_HANDLE luts, planetMap, composite, cloudTextures; // cloudTextures: the clouds' four, t24..t27
    };
    void DrawShadows(ID3D12GraphicsCommandList*, const Tables&);
    void DrawOpaque(ID3D12GraphicsCommandList*, const Tables&);     // into the bound scene targets, depth tested
    void UpdateWeather(ID3D12GraphicsCommandList*, const Tables&);  // after the clouds; the water's passes with it
    void ClearOverlay(ID3D12GraphicsCommandList*);
    void DrawGlass(ID3D12GraphicsCommandList*, const Tables&, D3D12_CPU_DESCRIPTOR_HANDLE dsv); // into the overlay
    void OverlayToRead(ID3D12GraphicsCommandList*);
    void OverlayToTarget(ID3D12GraphicsCommandList*);
    D3D12_GPU_DESCRIPTOR_HANDLE OverlaySrv() const { return Gpu(MaxImages + 2); }
    // The map towards the sun, for the ship's shadow on the ground; the overlay stands in without the ship.
    D3D12_GPU_DESCRIPTOR_HANDLE SunMapSrv() const { return Gpu(mReady ? MaxImages : MaxImages + 2); }

private:
    using Resource = Microsoft::WRL::ComPtr<ID3D12Resource>;
    struct Draw { uint32_t first, count, material; };
    struct Image { bool srgb; std::vector<uint8_t> png; };
    // The pack, CPU side, until Initialize uploads it.
    std::vector<uint8_t> mVertexBytes, mMaterialBytes;
    std::vector<uint32_t> mIndices;
    std::vector<Draw> mDraws;
    std::vector<uint32_t> mModes; // per material: 0 opaque, 1 blended, 2 canopy
    std::vector<Image> mImages;
    bool mLoaded = false, mReady = false;

    ID3D12DescriptorHeap* mHeap = nullptr;
    UINT mBase = 0, mStride = 0, mDsvStride = 0;
    D3D12_CPU_DESCRIPTOR_HANDLE Cpu(UINT i) const;
    D3D12_GPU_DESCRIPTOR_HANDLE Gpu(UINT i) const;
    void Bind(ID3D12GraphicsCommandList*, const Tables&, bool compute) const;

    Resource mVertices, mIndexBuffer, mMaterials, mTextures[MaxImages], mShadowMaps[2], mOverlay, mWeather, mConstantsBuffer;
    Resource mDrops, mWaterMap, mWaterFilm, mGathered;
    std::vector<Resource> mUploads;
    D3D12_INDEX_BUFFER_VIEW mIndexView = {};
    Microsoft::WRL::ComPtr<ID3D12DescriptorHeap> mDsvHeap, mRtvHeap;
    Microsoft::WRL::ComPtr<ID3D12RootSignature> mRoot;
    Microsoft::WRL::ComPtr<ID3D12PipelineState> mOpaquePSO, mShadowPSO, mGlassPSO, mPlumePSO, mWeatherPSO, mWaterPSO[3];
    Constants* mConstants = nullptr;
    bool mShadowsReadable = false, mWeatherReadable = false, mWaterReadable = false;
};
