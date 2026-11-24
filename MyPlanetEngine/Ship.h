// Ship.h - the player's ship (assets/vaisseau): the engine's pack of it (paquet_moteur.py), its opaque surfaces drawn in the
// scene, its own two shadow maps, the canopy's weather under the clouds (ShipWeather.hlsl) and the climate it reads, and its
// glass after temporal smoothing, or a reflective opaque hull before it (ToneMap.hlsl). Must match Ship.hlsli.
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
#include "ShipProfiles.h"
#include "TransportEquipment.h"
#include <array>

class Ship {
public:
    Ship();
    const ShipProfile& Profile() const { return mProfile; }
    static constexpr UINT MaxImages = SHIP_MAX_IMAGES;
    // The images, the two shadow maps, the overlay, then the water's: its drops, map, film and merges as UAVs, its map and
    // film as SRVs; then the climate map (Climate.hlsli), its view made by D3DApp.
    static constexpr UINT DescriptorCount = MaxImages + 12; // climate, then the shock hull cube and the actual scene depth
    // The canopy's water (ShipWater.hlsli): profile-specific chart and pitch, shared simulated drop capacity.
    static constexpr UINT DropCount = 8192;
    static constexpr UINT ShadowSize = 2048;
    // Negative alpha stores an opaque reflective surface's distance before temporal smoothing.
    static constexpr DXGI_FORMAT OverlayFormat = DXGI_FORMAT_R32G32B32A32_FLOAT;
    // Shadow radius (m); each profile supplies the centre. Match Ship.hlsli's SHIP_RADIUS.
    static constexpr float Radius = 6.7f;

    float EnvelopeRadius() const { return HasTransportRig() ? 7.3f : Radius; }

    struct Nozzle {
        DirectX::XMFLOAT4 mouthWidth, axisHeight, widthAxis;
        DirectX::XMFLOAT4 aperture; // linear image index + 1, axial depth of the curved outlet (m)
    };

    struct ExhaustPort { DirectX::XMFLOAT4 mouthRadius, axis; };
    struct Constants {
        DirectX::XMFLOAT4X4 model;     // ship frame -> face-local, camera-relative, transposed for HLSL
        DirectX::XMFLOAT4X4 shadow[2]; // ship frame -> the sun's and the overhead map's clip space, transposed
        DirectX::XMFLOAT4 sun, up, air, velocity;
        DirectX::XMFLOAT4 options; // HUD, cockpit, ShipModel, local air density relative to sea level
        DirectX::XMFLOAT4 airflow; // direction of the air over the hull in ship space; w: thermal load
        DirectX::XMFLOAT4 waterLayout; // atlas dimensions in texels, chart origin y (m), texel (m)
        DirectX::XMFLOAT4 thrust;  // x: the main engines, 0 to 1; y: roll right, z: lift, w: slide right, -1 to 1 (ShipPlume)
        DirectX::XMFLOAT4 turn;    // x: pitch up, y: yaw right, -1 to 1; z: clock (s), wraps at 3600
        DirectX::XMFLOAT4 course;  // the dashboard (ShipScreens.hlsli): heading, latitude, longitude (deg); w: the ground (km)
        DirectX::XMFLOAT4 gauges;  // x: the gas, 0 to 1
        // Packet poses first, then two sliding wings and two hinged airbrakes.
        DirectX::XMFLOAT4X4 pose[SHIP_POSE_COUNT]; // ship frame -> ship frame, transposed
        DirectX::XMFLOAT4 shockBounds; // local half-extents of the gas proxy (m), support-plane offset used by its cube (m)
        DirectX::XMFLOAT4 airframe; // wing extension, brake extension, reverse thrust, station keeping
        DirectX::XMFLOAT4 supportExhaust; // direction in ship axes and power relative to hover
        DirectX::XMFLOAT4 retroOutlet, supportOutlet; // left mouths, support outlet spacing in w
        DirectX::XMFLOAT4 radio; // receive lamp and audio meter in the cockpit
        DirectX::XMFLOAT4 equipment; // actual extension of wings, landing gear, airbrake and ramp
        DirectX::XMFLOAT4 automation; // manual switch mask, authored transport flag, exhaust deflection (radians)
        Nozzle nozzles[2]; // the shuttle's two authored main exhausts
        ExhaustPort ports[SHIP_TRANSPORT_PORT_PAIRS];
    };
    // The moving parts' pivots, ship frame, from the pack (pieces_mobiles.py, design_chasseur.py): the stick's twist axis,
    // the throttle's, the elevons' hinges, running outwards.
    struct Pivot { DirectX::XMFLOAT3 point, axis; };
    Pivot pivots[SHIP_PACK_POSES] = {};
    DirectX::XMFLOAT2 throttleStops = {};

    // The pack's path: false, and the ship stays out, when it cannot be read.
    bool Load(const std::wstring& path);
    // Creates the GPU side; the overlay always exists, so that the tone map can read it without a ship.
    void Initialize(ID3D12Device*, ID3D12GraphicsCommandList*, ID3D12DescriptorHeap* srvHeap, UINT descriptorBase,
                    UINT width, UINT height, DXGI_FORMAT hdrFormat, DXGI_FORMAT sunFormat, ID3D12Resource* sceneDepth);
    // Where D3DApp puts the climate map's view, for the canopy's temperature (ShipWeather.hlsl).
    D3D12_CPU_DESCRIPTOR_HANDLE ClimateDescriptor() const { return Cpu(MaxImages + 9); }
    void ReleaseUploads() { mUploads.clear(); }
    bool Ready() const { return mReady; }
    Constants& Frame() { return *mConstants; }
    // The shadow maps' frames from the sun's and the vertical's directions, in the ship frame.
    void SetLights(const DirectX::XMFLOAT3& sun, const DirectX::XMFLOAT3& up);
    void SetFlightSurfaces(float wings, float airbrakes);
    bool HasTransportRig() const { return !mTransportClips[0].empty(); }
    void SetTransportPose(const TransportEquipment& equipment);
    float TransportDepth(DirectX::XMFLOAT3 up, const TransportEquipment& state) const;

    struct Tables {
        D3D12_GPU_VIRTUAL_ADDRESS frame, cloudFrame; // the clouds' frame, b1 (Clouds.hlsli)
        D3D12_GPU_VIRTUAL_ADDRESS terrain; // the mesh after its horizon pass: the relief's shadow on the ship (ShipWeather)
        D3D12_GPU_DESCRIPTOR_HANDLE luts, planetMap, composite, cloudTextures; // cloudTextures: the clouds' four, t24..t27
    };
    void DrawShadows(ID3D12GraphicsCommandList*, const Tables&);
    void DrawOpaque(ID3D12GraphicsCommandList*, const Tables&);     // into the bound scene targets, depth tested
    void ResetSurfaceWeather() { mResetSurfaceWeather = true; }
    void UpdateWeather(ID3D12GraphicsCommandList*, const Tables&, ID3D12CommandSignature* dispatch);
    void ClearOverlay(ID3D12GraphicsCommandList*);
    void DrawGlass(ID3D12GraphicsCommandList*, const Tables&, D3D12_CPU_DESCRIPTOR_HANDLE dsv); // into the overlay
    void OverlayToRead(ID3D12GraphicsCommandList*);
    void OverlayToTarget(ID3D12GraphicsCommandList*);
    D3D12_GPU_DESCRIPTOR_HANDLE OverlaySrv() const { return Gpu(MaxImages + 2); }
    // The map towards the sun, for the ship's shadow on the ground; the overlay stands in without the ship.
    D3D12_GPU_DESCRIPTOR_HANDLE SunMapSrv() const { return Gpu(mReady ? MaxImages : MaxImages + 2); }

private:
    ShipProfile mProfile = FighterShip;
    using Resource = Microsoft::WRL::ComPtr<ID3D12Resource>;
    struct Draw { uint32_t first, count, material; };
    struct Image { bool srgb; std::vector<uint8_t> png; };
    // The pack, CPU side, until Initialize uploads it.
    std::vector<uint8_t> mVertexBytes, mMaterialBytes;
    std::vector<uint32_t> mIndices;
    std::vector<Draw> mDraws;
    std::vector<uint32_t> mModes; // 0 opaque, 1 blended, 2 canopy, 3 alpha-tested
    std::vector<uint32_t> mRoles; // VSX3 role 10: late reflective hull; 11: the Navigator's lit interior
    bool VisibleInView(const Draw& draw) const {
        constexpr uint32_t pilotOccupant = 13; // VSX3, the seated pilot visible through the exterior glass
        return mConstants->options.y < .5f || mRoles[draw.material] != pilotOccupant;
    }
    void ReadShuttleControls(const std::vector<uint8_t>& data, size_t& at);
    struct RigidKey { DirectX::XMFLOAT3 translation; DirectX::XMFLOAT4 rotation; };
    struct RigidTrack { unsigned slot; DirectX::XMFLOAT4X4 inverseBind; std::vector<RigidKey> keys; };
    std::array<std::vector<RigidTrack>,TransportEquipment::Count> mTransportClips;
    struct SupportHull { unsigned slot; std::vector<DirectX::XMFLOAT3> points; };
    std::vector<SupportHull> mTransportBounds;
    static DirectX::XMMATRIX TransportMatrix(const RigidTrack& track, double phase);
    void ReadTransport(const std::vector<uint8_t>& data, size_t& at);
    void ReadPane(const std::vector<uint8_t>& data, size_t& at);
    struct FlightFittings {
        DirectX::XMFLOAT3 wingPivot;
        float foldedAngle;
        DirectX::XMFLOAT3 brakePivot;
        float brakeAngle;
        DirectX::XMFLOAT3 brakeAxis;
    };
    static_assert(sizeof(FlightFittings) == 44, "FLW1 layout");
    FlightFittings mFlightFittings = {};
    void ReadLipTravel(const std::vector<uint8_t>& data, size_t& at);
    std::vector<DirectX::XMFLOAT4> mLipTravel; // signed transverse travel and its local gradient
    std::vector<DirectX::XMFLOAT4> mFittedPane; // outward normal scaled by radial distance, then signed edge distance
    Nozzle mNozzles[2] = {};
    std::array<ExhaustPort, SHIP_TRANSPORT_PORT_PAIRS> mPorts{};
    std::vector<Image> mImages;
    bool mLoaded = false, mReady = false;

    ID3D12DescriptorHeap* mHeap = nullptr;
    UINT mBase = 0, mStride = 0, mDsvStride = 0;
    D3D12_CPU_DESCRIPTOR_HANDLE Cpu(UINT i) const;
    D3D12_GPU_DESCRIPTOR_HANDLE Gpu(UINT i) const;
    void Bind(ID3D12GraphicsCommandList*, const Tables&, bool compute) const;
    using FieldRadii = float[SHIP_FIELD_COLUMNS][SHIP_FIELD_ROWS];
    void FitFieldToHull(FieldRadii& radii) const;
    DirectX::XMFLOAT4 CreateShockHull(ID3D12Device*, ID3D12GraphicsCommandList*);
    void BuildFlightSurfaces();

    Resource mVertices, mIndexBuffer, mMaterials, mTextures[MaxImages], mShadowMaps[2], mOverlay, mWeather, mConstantsBuffer;
    Resource mDrops, mWaterMap, mWaterFilm, mGathered;
    Resource mFieldRadii, mPaneChart, mLipBuffer, mShockHull, mSceneDepth;
    std::vector<Resource> mUploads;
    D3D12_INDEX_BUFFER_VIEW mIndexView = {};
    Microsoft::WRL::ComPtr<ID3D12DescriptorHeap> mDsvHeap, mRtvHeap;
    Microsoft::WRL::ComPtr<ID3D12RootSignature> mRoot;
    Microsoft::WRL::ComPtr<ID3D12PipelineState> mOpaquePSO, mReflectionPSO, mShadowPSO, mMaskedShadowPSO, mGlassPSO, mEntryParticlesPSO, mEntryVolumePSO, mPlumePSO, mWeatherPSO, mWaterPSO[3];
    Constants* mConstants = nullptr;
    bool mShadowsReadable = false, mWaterReadable = false, mResetSurfaceWeather = true;
};
