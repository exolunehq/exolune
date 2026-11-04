// D3DApp.h
#pragma once

#define NOMINMAX
#include <windows.h>
#include <wrl.h>
#include <d3d12.h>
#include <dxgi1_6.h>
#include <d3dcompiler.h>
#include <DirectXMath.h>
#include <cmath>
#include <memory>
#include <string>
#include <vector>
#include "Ship.h"
#include "Audio.h"
#include "Glare.h"
#include "Settings.h"
#include "CineVideo.h"
#include "Climate.h"
#include "WalkController.h"
class Ocean;
namespace Tectonics { struct Map; }

using namespace Microsoft::WRL;
using namespace DirectX;

// Double precision vector for the camera: a float is only 0.5 m precise at 6 378 km.
struct Vec3d
{
    double x, y, z;
    Vec3d operator+(const Vec3d& o) const { return { x + o.x, y + o.y, z + o.z }; }
    Vec3d operator-(const Vec3d& o) const { return { x - o.x, y - o.y, z - o.z }; }
    Vec3d operator*(double s) const { return { x * s, y * s, z * s }; }
};
inline double Dot(const Vec3d& a, const Vec3d& b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline Vec3d Cross(const Vec3d& a, const Vec3d& b) { return { a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x }; }
inline double Length(const Vec3d& v) { return std::sqrt(Dot(v, v)); }
inline Vec3d Normalize(const Vec3d& v) { return v * (1.0 / Length(v)); }
// Rodrigues rotation around a unit axis; a positive angle turns v towards Cross(axis, v).
inline Vec3d Rotate(const Vec3d& v, const Vec3d& axis, double angle)
{
    const double c = std::cos(angle), s = std::sin(angle);
    return v * c + Cross(axis, v) * s + axis * (Dot(axis, v) * (1.0 - c));
}

const Vec3d kNorth = { 0.0, 1.0, 0.0 };
// Latitude and longitude to a unit direction, y towards the north: (cos lat cos lon, sin lat, cos lat sin lon).
inline Vec3d LatLonToDir(double latitude, double longitude)
{
    const double lat = latitude * XM_PI / 180.0, lon = longitude * XM_PI / 180.0;
    return { std::cos(lat) * std::cos(lon), std::sin(lat), std::cos(lat) * std::sin(lon) };
}
const double kWeatherWindSpeed = 12.0; // m/s at the equator: a shared eastward rotation, not one speed per cloud

#include "PlanetFoliage.h"
#include "FoliageHiZ.h"
#include "PlanetPlantPlacement.h"

class D3DApp {
public:
    D3DApp(HINSTANCE hInstance, double startAltitude, double latitude, double longitude, double pitchDown, double heading);
    virtual ~D3DApp();

    bool Initialize();
    int Run();

protected:
    bool InitWindow();
    void ToggleFullscreen();
    bool InitDirect3D();
    void MainLoop();
    void UpdateCamera(float dt);
    void Draw();
    void UpdateTitle(float dt, double clearance, double halfWidth, UINT ringCount);
    void ReadGpuTimes();

    static LRESULT CALLBACK WindowProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);
    LRESULT MsgProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);

    // Test views, to judge a change in flight (D3DAppTests.cpp): with MYPLANETENGINE_TESTS set to a UTF-8 text file,
    // one test per line, "label | altitude latitude longitude pitchDown heading [view] [| sunLatitude sunLongitude]" (#
    // starts a comment; view is a diagnostic name or "marche" for grounded walking), a "Tests" palette beside the render
    // window has a button for each, and F1 to F12 do the same: the camera goes there, in the test's view or the game's,
    // the temporal smoothing starts afresh, the test's label shows in the title, and the focus comes back to fly.
    struct TestView { std::wstring label; double altitude, latitude, longitude, pitchDown, heading, sunLatitude, sunLongitude; bool sun; float windSpeed,windDirection,swellHeight;bool wind; float view; bool walk; };
    std::vector<TestView> mTests;
    HWND mTestsWnd = nullptr;
    std::wstring mTestLabel;
    void ReadTests();
    void CreateTestsWindow();
    void GoToTest(size_t index);
    static LRESULT CALLBACK TestsProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

    std::unique_ptr<Ocean> mOcean;
    float mOceanSpeed=12.0f,mOceanDirection=70.0f,mOceanSwell=1.8f,mOceanElevation=-1000.0f;
    // Their plane rides tangent at the camera, carried along without turning; its origin keeps the distance flown. The
    // time runs with the clock, or 1/60 s per frame for the captures and benches; MYPLANETENGINE_TIME="start [rate]".
    Vec3d mWaveX = {}, mWaveY = {}, mWaveCamera = {};
    double mWaveOrigin[2] = {};
    double mSeaTime = 0.0, mSeaTimeRate = 1.0;
    bool mWaveReset = true; // a jump of the camera starts the plane afresh
    void UpdateOceanPlane(double dt, const Vec3d& faceX, const Vec3d& faceY, const Vec3d& faceZ);

    void WaitForPreviousFrame();
    D3D12_GPU_DESCRIPTOR_HANDLE GpuDescriptor(UINT index) const; // in mSrvHeap

    // Shared by the three shaders: must match Planet.hlsli.
    struct FrameConstants
    {
        XMFLOAT4X4 viewProj;
        XMFLOAT4 faceX;
        XMFLOAT4 faceY;
        XMFLOAT4 faceZ;
        XMFLOAT4 faceParams; // half-width, planet radius, camera altitude, cells per face side
        XMFLOAT4 lightDir;
        double nadir[4];     // nadir direction in double precision, for the noise
        XMFLOAT4 ringParams; // ring count, half-width growth from one ring to the next
        XMFLOAT4 camRight;   // camera axes, face-local; .w of right and up: tangents of the half fields of view
        XMFLOAT4 camUp;
        XMFLOAT4 camForward;
        XMFLOAT4 camPlane;   // xy: position on the face plane; z: frozen; w: observer canopy cover
        XMFLOAT4 detailOrigin; // camera minus the detail anchor, planet frame; .w: anchor unit
        XMINT4 detailAnchor;   // the detail anchor, in anchor units
        XMFLOAT4 camVertical;  // the camera's vertical, face-local; .w: camera altitude above sea level (km)
        XMFLOAT4X4 reproject;  // face-local point or direction -> previous frame's clip space
        XMFLOAT4 taa;          // .x: weight of the new frame in the temporal smoothing, 1 when off
        XMFLOAT4 waveAxisX;    // the sea's waves: their plane, face-local (UpdateOceanPlane)
        XMFLOAT4 waveAxisY;
        XMFLOAT4X4 reprojectShip; // the ship's pixels: face-local point -> previous frame's clip space, following the ship
        XMFLOAT4 shipSphere;      // xyz: the ship's centre, face-local from the camera (m); w: its radius, 0 without the ship
        XMFLOAT4X4 shipSunShadow; // face-local point -> the ship's map towards the sun, for its shadow on the ground
        XMUINT4 coordinateInfo;   // lengths of two ASCII lines; zero hides the screenshot overlay
        XMUINT4 coordinateText[8]; // two rows of 64 bytes, packed little-endian
        XMFLOAT4 reliefGradients[256]; // immutable table, shared with Noise.hlsli
        XMFLOAT4 screenRelief;         // the screen relief's texels across, its weight, pixels per texel side
        XMFLOAT4 foliageWind; // climate wind, face-local; shared weather clock
    };

    // The clouds' frame, b1 (Clouds.hlsli): the camera and the view in the planet frame (km), in double precision.
    struct CloudFrame
    {
        double cameraKm[4];  // w: 1 with the clouds (key N)
        double forward[4];
        double rightTan[4];  // w: the tangent of the half field of view
        double upTan[4];
        double wind[4];      // xy: the wind's angle, sine and cosine; z: 1 for the reference quality (key C)
        double sun[4];
        // The cloud temporal pass (CloudsTemporal.hlsli): to the previous camera, then this frame's tile pixel.
        float prevQ[3][4];
        float prevGround[3][4];
        float temporal[4];
    };
    static_assert(sizeof(CloudFrame) == 304, "The clouds' frame must match Clouds.hlsli.");

    struct FaceVertex
    {
        XMFLOAT3 pos;
        float elevation;
        XMFLOAT3 dir;
        float roughness;
        float volcanic; // the fresh volcanic ground (Planet.hlsli)
        float horizon; // toward the sun, for the terrain's cast shadow (Horizon.hlsl)
        float shadow;  // the column's shadow height, for the air (Horizon.hlsl)
    };

    static constexpr double PlanetRadius = 6378000.0;
    // The mesh: a face of FaceCells x FaceCells cells, then up to MaxRings square rings of 4 x FaceCells
    // vertices each. FaceCells is even, so that one vertex sits exactly on the nadir.
    static const UINT FaceCells = 192;
    static const UINT MaxRings = 2048; // enough for 256 cells per side down to the ground
    // Each ring is wider than the previous by this factor, so that cells stay square: a cell spans about
    // 2 / FaceCells of its distance to the nadir, whatever the face size.
    static constexpr double RingGrowth = 1.0 + 2.0 / FaceCells;
    static const UINT FaceVertexCount = (FaceCells + 1) * (FaceCells + 1);
    static const UINT RingVertexCount = 4 * FaceCells;
    static const UINT MaxVertexCount = FaceVertexCount + MaxRings * RingVertexCount;
    // The fine grid (docs/spec-rendu-lointain.md, step 2): the face cut FineSubdivision times finer, for the
    // materials' decisions, on from face cells of FineMinCell (m), fully at twice that: until the mesh carries the
    // relief's finest octave, 13.5 m (DETAIL_MIN_WAVELENGTH), over the 4 cells of MESH_BAND_LIMIT. It lights the ground
    // from larger cells only, FINE_LIGHT_MIN_CELL (PlanetSettings.hlsli).
    // Off from 20 m, the decisions lost the octaves of 13.5 to 100 m from 2 km down to 160 m: the shapes they make in
    // snow and rock came and went on the way down (docs/journal-planete.md, 2026-10-24).
    static const UINT FineSubdivision = 4;
    static const UINT FineVertexCount = (FaceCells * FineSubdivision + 1) * (FaceCells * FineSubdivision + 1);
    static constexpr double FineMinCell = 13.5 / 4.0;

    HINSTANCE mhAppInst = nullptr;
    const Settings mSettings; // read once, at startup
    HWND mhMainWnd = nullptr;
    UINT mClientWidth = 1280;
    UINT mClientHeight = 720;
    bool mFullscreen = false, mAllowTearing = false;
    RECT mWindowedRect = {};
    std::wstring mGpuName;
    std::wstring mMainWndCaption = L"MyPlanetEngine";

    static const UINT FrameCount = 2;

    ComPtr<ID3D12Device> md3dDevice;
    ComPtr<IDXGISwapChain3> mSwapChain;
    ComPtr<ID3D12CommandQueue> mCommandQueue;
    ComPtr<ID3D12DescriptorHeap> mRtvHeap;
    ComPtr<ID3D12Resource> mRenderTargets[FrameCount];
    ComPtr<ID3D12CommandAllocator> mCommandAllocator;
    ComPtr<ID3D12GraphicsCommandList> mCommandList;
    ComPtr<ID3D12Fence> mFence;
    ComPtr<ID3D12Resource> mDepthStencilBuffer;
    ComPtr<ID3D12DescriptorHeap> mDsvHeap;

    ComPtr<ID3D12RootSignature> mRootSignature;
    ComPtr<ID3D12RootSignature> mComputeRootSignature;
    ComPtr<ID3D12PipelineState> mWirePSO;
    ComPtr<ID3D12PipelineState> mTerrainDepthPSO; // the terrain's depth alone, before the plants (docs/optimisation.md, round 2)
    ComPtr<ID3D12PipelineState> mTerrainShadePSO; // then its colour, on the pixels it shows only
    ComPtr<ID3D12PipelineState> mComputePSO;
    ComPtr<ID3D12PipelineState> mComputePairsPSO; // the same, in a flight: the lattice in pairs of floats (round 8)

    // High dynamic range: the scene renders in linear light into mHdrTarget, then the tone map pass
    // writes it to the back buffer through an sRGB view. 32-bit floats: alpha carries the terrain's distance (km) to
    // the atmosphere, which needs it to the metre at any distance; in half floats, its steps reached 16 km from
    // orbit, cutting off the densest air in rings (docs/spec-rendu-lointain.md).
    static const DXGI_FORMAT HdrFormat = DXGI_FORMAT_R32G32B32A32_FLOAT;
    ComPtr<ID3D12Resource> mHdrTarget;
    ComPtr<ID3D12DescriptorHeap> mSrvHeap; // shader visible, see the Descriptor enum in D3DApp.cpp
    ComPtr<ID3D12RootSignature> mPostRootSignature;
    ComPtr<ID3D12PipelineState> mAtmospherePSO; // the clouds and the air over the scene in one pass, into mComposite
    // The terrain's sunlit part, a second render target of the scene: what the clouds' shadow takes off (Clouds.hlsli, t17).
    static const DXGI_FORMAT SunFormat = DXGI_FORMAT_R16G16B16A16_FLOAT;
    ComPtr<ID3D12Resource> mSunPart;
    ComPtr<ID3D12Resource> mLocalContacts;
    ComPtr<ID3D12RootSignature> mLocalContactRoot;
    ComPtr<ID3D12PipelineState> mLocalContactPso,mLocalContactResolvePso;
    bool mLocalContactsEnabled=true;
    void ApplyLocalContacts();

    // Temporal smoothing (key T, MYPLANETENGINE_TAA at startup): the tone map pass blends the composite image with the
    // previous result, reprojected, and writes the new result into the other history image.
    ComPtr<ID3D12Resource> mComposite;
    ComPtr<ID3D12Resource> mHistory[2];
    UINT mHistoryIndex = 0;     // the one holding the previous result
    bool mHistoryValid = false;
    bool mTaa = false;
    bool TemporalAA() const { return mTaa && mDiagnosticView == 0.0f; }
    void PlaceCamera(double latitude, double longitude, double pitchDown, double heading, double altitude);
    float mDiagnosticView = 0.0f; // MYPLANETENGINE_VIEW: a material's weight or a field, unlit and without smoothing
    ComPtr<ID3D12RootSignature> mResolveRootSignature;
    ComPtr<ID3D12PipelineState> mToneMapPSO;
    XMMATRIX mPrevViewProj = XMMatrixIdentity();
    Vec3d mPrevCamPos = {}, mPrevFaceX = {}, mPrevFaceY = {}, mPrevFaceZ = {};
    // The terrain's inputs, the frame constants its compute passes read (docs/optimisation.md, round 4): the mesh's,
    // which decide each vertex's terrain, then the view's and the sun's, which decide the vertices needed and the
    // horizon. The same as the previous frame's, what the passes wrote then is kept: their buffers are single, which holds
    // with one frame in flight.
    struct TerrainInputs
    {
        XMFLOAT4 faceX, faceY, faceZ, faceParams;
        double nadir[4];
        XMFLOAT4 ringParams, camPlane; // the mesh's, up to here
        XMFLOAT4 lightDir, camRight, camUp, camForward, waveAxisX;
    };
    TerrainInputs mTerrainInputs = {};
    bool mTerrainKept = false; // the terrain's buffers hold what its passes computed from mTerrainInputs
    bool mTerrainSlid = false;  // the previous frame's mesh had slid
    bool mTerrainPairs = false; // the terrain's buffers come from the lattice in pairs of floats (round 8)

    Glare mGlare; // the lens's glare over the composite image, with MYPLANETENGINE_GLARE

    // Close-up materials, generated once at startup (docs/spec-textures-generees.md): two texture arrays,
    // colour and cavity, then slope and height, one slice per material, with their mips. Must match
    // MaterialGenerator.hlsl and PixelShader.hlsl.
    static const UINT MaterialCount = 7; // sand, rock, scree, their fine tiles, the rock's top-down photo
    static const UINT MaterialSize = 1024;
    static const UINT MaterialMips = 11;  // 1024 down to 1
    ComPtr<ID3D12Resource> mMaterials[2];

    // Atmosphere tables, computed once at startup: transmittance, multiple scattering, sky irradiance.
    ComPtr<ID3D12Resource> mAtmosphereLuts[3];
    // The clouds (Clouds.hlsli): their weather turns east with the wind on one shared clock, independent of the camera
    // and of the render count; paused at startup at MYPLANETENGINE_WEATHER_TIME, 0 by default (Space, V: x5).
    double mWeatherTime = 0.0, mWeatherRate = 1.0;
    bool mWeatherPaused = true;
    bool mCloudsOn = true;         // key N; MYPLANETENGINE_NO_CLOUDS for the benches that want none
    bool mCloudsReference = false; // key C: finer integration steps
    // Their four textures (assets/clouds): the shape and the cirrus' fibres, the erosion, the vertical profiles, the
    // planet's weather map.
    ComPtr<ID3D12Resource> mCloudShape, mCloudDetail, mCloudProfiles, mCloudWeather;
    // The cloud temporal pass (docs/optimisation.md): one pixel per 4x4 tile traced per frame into the fresh images, then
    // resolved at full resolution with the history, reprojected. MYPLANETENGINE_CLOUD_FULL keeps the single full pass.
    static const UINT CloudTileX = 4, CloudTileY = 4; // CloudsTemporal.hlsli, CLOUD_TEMPORAL_TILE
    // The clouds' diagnostic views that the single pass alone draws (Clouds.hlsli): the weather map, their shadow.
    static constexpr float CloudWeatherView = 33.0f, CloudShadowView = 34.0f;
    // The fresh light and data, one texel per 4x4 tile, then per 2x2 quad for the drifted pixels (PSCloudTraceHalf).
    ComPtr<ID3D12Resource> mCloudFresh[4], mCloudHistory[2][3]; // [the history read this frame][light, data, spread]
    ComPtr<ID3D12PipelineState> mCloudTracePSO, mCloudHalfPSO, mCloudResolvePSO;
    UINT mCloudHistoryIndex = 0, mCloudFrame = 0;
    bool mCloudHistoryValid = false;
    Vec3d mCloudPrevCam = {}, mCloudPrevAxes[3] = {}, mCloudPrevSun = {};
    double mCloudPrevWind = 0.0;
    bool mCloudPrevReference = false, mCloudPrevEnabled = false;
    ComPtr<ID3D12Resource> mCloudConstantBuffer;
    CloudFrame* mCloudConstants = nullptr;
    ComPtr<ID3D12Resource> mShipCloudConstantBuffer;
    CloudFrame* mShipCloudConstants = nullptr; // same weather, evaluated at the ship, independent of the camera
    Vec3d mSunDir = {}; // keys O and P turn it around the planet's axis
    Vec3d mStartSunDir = {}; // the sun at startup, for the test views that give none

    ComPtr<ID3D12Resource> mConstantBuffer;
    FrameConstants* mConstants = nullptr;
    ComPtr<ID3D12Resource> mNadirConstantBuffer; // the frame's constants, the mesh kept: the exact vertex under the camera
    FrameConstants* mNadirConstants = nullptr;   // in a flight (round 8)
    ComPtr<ID3D12Resource> mFaceVertexBuffer; // written by the compute shader, then its horizon and shadow height
    ComPtr<ID3D12PipelineState> mHorizonPSO; // the march toward the sun: horizon and shadow height (Horizon.hlsl)
    ComPtr<ID3D12Resource> mFinePositions; // the fine grid: positions and elevations
    ComPtr<ID3D12Resource> mFineNormals;   // its normals, read by the pixel shader
    ComPtr<ID3D12RootSignature> mFineRootSignature;
    ComPtr<ID3D12PipelineState> mFineTerrainPSO;
    ComPtr<ID3D12PipelineState> mFineNormalsPSO;
    // The screen relief (ScreenRelief.hlsl): the relief under each texel of ScreenReliefScale pixels.
    ComPtr<ID3D12Resource> mScreenPositions;
    ComPtr<ID3D12PipelineState> mScreenReliefPSO;
    static const UINT ScreenReliefScale = 2, ScreenReliefMaxTexels = (3840 / 2) * (2160 / 2);
    static const UINT ScreenSampleBytes = 6 * sizeof(float); // Planet.hlsli: ScreenSample
    static constexpr double ScreenReliefLow = 150e3, ScreenReliefHigh = 400e3; // its weight's rise, camera altitude (m)
    ComPtr<ID3D12Resource> mIndexBuffer;
    D3D12_INDEX_BUFFER_VIEW mIndexBufferView = {};
    ComPtr<ID3D12Resource> mReadbackBuffer;   // the nadir vertex, to know the ground height
    // The planet map (PlanetMap.h): the relief on a cube fixed on the planet, drained, once at startup.
    ComPtr<ID3D12Resource> mPlanetMap;
    void CreatePlanetMap();
    // The tectonic map (Tectonics.h): the planet's plates and their fields, once at startup; its time (ms) and size (MB).
    ComPtr<ID3D12Resource> mTectonicMap, mTectonicViews;
    // The volcanoes (docs/spec-volcanisme.md) and their index, two structured buffers beside the map; their count.
    ComPtr<ID3D12Resource> mVolcanoes, mVolcanoIndex;
    UINT mVolcanoCount = 0;
    double mVolcanoMs = 0.0;
    double mTectonicMs = 0.0, mTectonicMb = 0.0;
    void CreateTectonicMap();
    // The climate map (Climate.h): the planet's rain, temperatures and winds from its large forms, once at startup, after the
    // tectonic map; its time (ms) and size (MB).
    ComPtr<ID3D12Resource> mClimateMap;
    Climate::Map mClimateCpu; // retained from CreateClimateMap for environmental wind and temperature
    double mClimateMs = 0.0, mClimateMb = 0.0, mWeatherMapMs = 0.0; // and the clouds' weather map's time (ms)
    void CreateClimateMap(const Tectonics::Map& tectonics, uint32_t seed, const std::wstring& cache);

    // Objects near the camera (docs/spec-objets-proximite.md): stones and grass tufts on the planet's lattice, placed
    // afresh every frame by a compute pass, drawn by one indirect draw per class. Must match Objects.hlsli and
    // ObjectPlacement.hlsl.
    struct ObjectInstance { XMFLOAT3 pos; float size; XMFLOAT3 axisX; float burial; XMFLOAT3 axisY; float elevation; XMFLOAT3 albedo; UINT seed; };
    struct ShapeVertex { XMFLOAT3 pos; float height; XMFLOAT3 normal; float shade; };
    static void BuildRocks(std::vector<ShapeVertex>& vertices, std::vector<UINT>& indices);
    static void BuildTufts(std::vector<ShapeVertex>& vertices, std::vector<UINT>& indices);
    static const UINT RockVariants = 8, RockVertices = 642; // an icosphere cut three times
    static const UINT TuftVariants = 4, TuftBlades = 40, TuftVertices = TuftBlades * 7;
    // The stones' instances, then the tufts' from ObjectClassCapacity, the plants' from twice it, the far ones' from three
    // times it (PlanetPlantPlacement); the census writes one record per candidate.
    static const UINT ObjectClassCapacity = 262144, ObjectCandidates = 262144;
    static const UINT ObjectCapacity = ObjectCandidates > 4 * ObjectClassCapacity ? ObjectCandidates : 4 * ObjectClassCapacity;
    static const UINT ObjectSlices = 8;    // the lattice's slices, one per class and octave: OBJECT_OCTAVES, TUFT_OCTAVES
    static constexpr double ObjectFinestCell = 0.125; // the finest lattice cell, the stones' at OBJECT_OCTAVES.x
    static const UINT ObjectWindow = 224;  // lattice cells per side of the tufts' windows, the stones' half
    static const UINT PlanetPlantWindow = 512; // the plants' tiles per side: trees keep their volume down to 5 pixels
    // The counters: the stones' indirect draw's arguments, then the measures of the gap between their feet and the
    // ground the mesh draws: placed, measured, sum of |gap| (0.01 mm), largest drop of the ground under a foot and rise
    // over it (0.01 mm), largest drop over the burial depth (per mille), objects floating; candidates whose ground was
    // evaluated; largest rise over the visible height (per mille), largest gap on screen (0.01 px); tufts placed; then
    // the tufts' indirect draw's arguments. The plants' (PlanetPlantPlacement): placed and kept, floating, largest gap on
    // screen (0.01 px), the far ones placed and kept; at 37 to 39, the tiles and plants over the capacities.
    enum ObjectStat : UINT { DrawInstances = 1, Placed = 5, Measured, GapSum, GapBelow, GapAbove, FloatRatio, Floating, Evaluated,
                             SinkRatio, GapPixels, TuftsPlaced, TuftArguments, TuftInstances, PlantsPlaced = 21, PlantInstances = 23,
                             PlantFloating = 27, PlantGap, PlantsCoarse, PlantCoarseInstances = 31, ObjectCounters = 40 };
    static constexpr float ObjectsView = 13.0f; // the objects' diagnostic view, MYPLANETENGINE_VIEW=objects
    static constexpr float HeightView = 25.0f;  // the height seen over the ground, then the distance: every object drawn
    ComPtr<ID3D12RootSignature> mObjectRootSignature;
    ComPtr<ID3D12PipelineState> mObjectCandidatesPSO; // the first pass, light: the candidates that may be seen
    ComPtr<ID3D12PipelineState> mObjectPlacementPSO;  // the second, heavy: their ground, kept or not
    ComPtr<ID3D12CommandSignature> mObjectDispatchSignature;
    ComPtr<ID3D12PipelineState> mObjectPSO;
    ComPtr<ID3D12PipelineState> mTuftPSO;
    ComPtr<ID3D12CommandSignature> mObjectCommandSignature;
    ComPtr<ID3D12Resource> mObjectInstances;
    ComPtr<ID3D12Resource> mObjectCounters;
    ComPtr<ID3D12Resource> mObjectCandidates;    // the first pass's list
    ComPtr<ID3D12Resource> mObjectDispatch;      // the second pass's dispatch, then the candidates' count
    ComPtr<ID3D12Resource> mObjectCountersReset; // upload: the arguments with no instance, the measures at 0; the dispatch
    ComPtr<ID3D12Resource> mObjectReadback;
    ComPtr<ID3D12Resource> mObjectInstancesReadback; // in batch mode, with MYPLANETENGINE_OBJECT_LIST or _CENSUS
    ComPtr<ID3D12Resource> mShapeVertices; // the rocks', then the tufts' from mTuftShapeOffset bytes
    ComPtr<ID3D12Resource> mShapeIndices;  // the same, one index list per class
    D3D12_INDEX_BUFFER_VIEW mShapeIndexView = {};
    UINT64 mTuftShapeOffset = 0;
    bool mFoliageFade = true; // key H: impostor-mesh fade of the plants (PlanetFoliageLod.hlsli)
    UINT mFoliageFadeFrame = 0;
    // The plants (docs/vegetation-planetaire.md): placed on the planet's lattice, sorted by model and representation,
    // the near ones' meshes drawn first, then the far ones' impostors, those the meshes hide rejected (FoliageHiZ).
    PlanetFoliage mPlanetFoliage;
    FoliageHiZ mFoliageHiZ;
    PlanetPlantPlacement mPlanetPlantPlacement;
    double mFoliagePlaceMs = 0, mFoliageDrawMs = 0, mFrameGpuMs = 0, mPlantPlacementMs = 0, mHiZBuildMs = 0, mHiZCullMs = 0;
    std::vector<PlanetFoliage::Sample> mPlanetFoliageSamples;
    UINT mObjectStats[ObjectCounters] = {}; // the last frame's counters
    std::wstring ObjectStatsText() const;
    std::wstring mTitle;

    // GPU timestamps: frame start, after terrain compute, frame end, object placement/draw, then the atmosphere pass and its clouds.
    ComPtr<ID3D12QueryHeap> mTimestampHeap;
    ComPtr<ID3D12Resource> mTimestampBuffer;
    UINT64 mTimestampFrequency = 0;
    double mComputeMs = 0.0; // summed over the title period
    double mDrawMs = 0.0;
    double mObjectMs = 0.0;     // their placement
    double mObjectDrawMs = 0.0; // their draw
    double mCloudPassLastMs = 0.0;
    double mGpuFrameLastMs = 0.0;
    double mCloudPassMs = 0.0; // summed over the title period
    double mOceanMs = 0.0;
    // The performance bench (tools/banc_perf.py): each pass's time, the last frame's and summed over a batch job's samples.
    // The GPU passes first, then the CPU's frame (ms): preparation, recording, submission and present, the wait for the
    // GPU, the cadence (from one present to the next), and the GPU idle between two frames.
    static const UINT PerfGpu = 14, PerfPasses = PerfGpu + 6;
    double mPerfLast[PerfPasses] = {}, mPerfSum[PerfPasses] = {};
    LARGE_INTEGER mPerfPresent = {};
    UINT64 mPerfGpuEnd = 0;
    UINT mPerfFrames = 0;
    double mDrawMinMs = 1e9; // the fastest frame: the GPU is shared, and other programs' work lengthens the others

    // The benches (D3DAppBench.cpp, Settings.h). Capture for testing: with MYPLANETENGINE_CAPTURE set to a .bmp path,
    // the app renders MYPLANETENGINE_CAPTURE_FRAME frames, 200 by default, saves the last one there and quits.
    UINT mFrameNumber = 0;

    // Tremble test for testing: with MYPLANETENGINE_TREMBLE set to a path prefix, the camera stays still
    // after TrembleWarmup frames while the mesh is placed as if it flew forward, at MYPLANETENGINE_TREMBLE_SPEED
    // (1 by default: speed x1, one 60 fps frame per frame). The next frames, 24 or MYPLANETENGINE_TREMBLE_FRAMES, are
    // saved as prefix_001.bmp, prefix_002.bmp... then the app quits. The terrain is fixed on the planet: any change
    // between these frames is the mesh resampling it, the trembling, or its detail growing as its cells shrink, the
    // mutation (docs/log/spec-stabilite.md).
    static const UINT TrembleWarmup = 60;
    // Batch capture for the quality bench (tools/banc_qualite.py): with MYPLANETENGINE_BATCH set to a list of jobs, one
    // per line, "out.bmp view height latitude longitude pitchDown heading [faceFactor [weatherTime | sunLatitude sunLongitude | weatherTime sunLatitude sunLongitude]]",
    // the app places the camera
    // `height` m above the ground there, re-placed as that ground settles for BatchSettle frames, in the diagnostic view
    // `view` ("-" for none), its mesh sized by faceFactor if given (half of the default: cells twice finer, the same
    // view); after BatchWarm more frames for the temporal smoothing, it saves the frame and goes on; then it quits.
    struct BatchJob {
        std::wstring path;
        float view;
        double height, latitude, longitude, pitchDown, heading, faceFactor;
        double weatherTime = -1.0; // optional snapshot; otherwise the environment's fixed time
        double sunLatitude = 0, sunLongitude = 0;
        bool sun = false;
    };
    static const UINT BatchSettle = 12, BatchWarm = 40;
    std::vector<BatchJob> mBatch;
    size_t mBatchIndex = 0;
    UINT mBatchFrame = 0;
    std::wstring mLabel; // MYPLANETENGINE_LABEL, then what is missing at startup: shown in the title
    ComPtr<ID3D12Resource> mCaptureBuffer;
    D3D12_PLACED_SUBRESOURCE_FOOTPRINT mCaptureFootprint = {};
    void ReadBatch();
    UINT BatchCaptureFrame() const;
    bool BeginBatchFrame();
    void SumBatchTimes(const LARGE_INTEGER (&cpuMarks)[5], bool usePlantHiZ);
    void SaveCapture(bool batchCapture, UINT trembleIndex);

    // Offline film: independent ship and camera poses, fixed clock, global frame numbers.
    struct CineFrame { bool cockpit, bare; double nav[6], cam[6], fov, weather; }; // bare: the pilot's eye, the ship hidden
    std::vector<CineFrame> mCine;
    double mCineFps = 60.0, mCineFov = 60.0, mCineShipGround = 0.0;
    UINT mCineIndex = 0, mCineEnd = 0, mCineLead = 0;
    bool mCineClamped = false;
    double mCineGpuMs = 0, mCineWallMs = 0; UINT mCineTimed = 0; LARGE_INTEGER mCineMark = {}; // ms per frame, in cine.log
    std::unique_ptr<CineVideo> mCineVideo; // MYPLANETENGINE_CINE_VIDEO: frames to ffmpeg, not to BMP files
    ComPtr<ID3D12PipelineState> mCineGroundPSO;
    ComPtr<ID3D12Resource> mCinePoints, mCineGround, mCineGroundReadback;
    D3D12_GPU_DESCRIPTOR_HANDLE mCineTectonics = {};
    void ReadCine();
    void InitCine(D3D12_GPU_DESCRIPTOR_HANDLE tectonics);
    bool BeginCineFrame();
    void ClampCine();
    void EndCineFrame();
    void LogCine(const char* message) const;

    UINT mRtvDescriptorSize = 0;
    UINT mFrameIndex = 0;
    UINT64 mFenceValue = 0;
    HANDLE mFenceEvent = nullptr;

    // Camera, in planet coordinates (planet centre at the origin).
    Vec3d mCamPos = {};
    Vec3d mCamForward = {};
    double mGroundHeight = 0.0; // terrain height under the camera, read back from the GPU
    double mFaceFactor = 2.0;   // face half-width = factor x height above the ground
    double mSpeedFactor = 0.1;  // speed = factor x height above the ground, per second: a few hundred m/s at cloud height
    bool mWireframe = false;

    // Mesh placement: the face's frame, size and ring count. Key G freezes it (diagnostic): the camera
    // keeps moving, the mesh stays where it was, so any trembling left is not the mesh sliding.
    bool mMeshFrozen = false;
    bool mFaceted = false;      // key R: faceted shading, from the triangles, to compare
    Vec3d mMeshX = {}, mMeshY = {}, mMeshZ = {};
    double mMeshHalfWidth = 0.0;
    UINT mMeshRingCount = 0;
    bool mLooking = false;
    POINT mLastMouse = {};

    // The player's ship (Ship.h, assets/vaisseau; D3DAppShip.cpp): flown with keyboard and mouse, seen from its cockpit
    // or from behind; Tab goes from the cockpit to the chase view, then to the free camera.
    // MYPLANETENGINE_VAISSEAU=cockpit, poursuite or libre chooses the first view (the benches start free);
    // MYPLANETENGINE_VERRIERE=pluie, nuage or givre forces the glass's weather, for the captures. See UpdateShip.
    enum class View { Free, Cockpit, Chase, Bare, Walk }; // Walk leaves the stationary ship at its saved pose
    View mView = View::Free;
    Ship mShip;
    Audio mAudio; // the ship's engine, thrusters and wind, set in UpdateShip
    Vec3d mShipPos = {}, mShipForward = {}, mShipUp = {}, mShipVelocity = {}; // planet frame; velocity in m/s
    Vec3d mShipRate = {};          // pitch up, yaw right, roll right (rad/s)
    double mStickX = 0.0, mStickY = 0.0; // the mouse's virtual stick, -1 to 1, recentring
    double mThrottle = 0.0;        // the gas, the wheel's notches in the ship's views: 0 stopped to 30 (UpdateShip)
    double mHeadYaw = 0.0, mHeadPitch = 0.0; // free look with the right button (rad): the pilot's head, the chase's orbit
    bool mHud = false;      // U: the head-up display on the canopy, off at start
    bool mCoordinates = true; // I: camera coordinates in the final image, independent of the cockpit HUD
    bool mHeadFree = false; // H: the mouse turns the head until H again; the head then stays where it was left
    bool mHeadKept = false; // the head stays put while the mouse flies, after H or the right button; R brings it back to rest
    Vec3d mHeadSway = {}, mHeadSwayRate = {}; // the eye pushed by the accelerations, ship axes (right, up, forward), m
    Vec3d mEyeSpin = {};                      // the eye's velocity from the ship's turns, last frame (m/s)
    double mHeadTilt = 0.0, mHeadTiltRate = 0.0; // the head's roll behind the ship's, towards the left (rad)
    double mPlume = 0.0;    // the engines' plume, 0 to 1: the gas, following it as the speed does (ShipPlume.hlsli)
    double mJets[5] = {};   // the attitude jets' commands, -1 to 1: slide right, lift, roll right, pitch up, yaw right
    Vec3d mCamUp = {};             // the view's up: the vertical for the free camera, the ship's or the head's otherwise
    Vec3d mChaseOffset = {};       // the chase camera from the ship, lagging behind its turns
    Vec3d mPrevShipPos = {}, mPrevShipForward = {}, mPrevShipUp = {};
    double mRawDx = 0.0, mRawDy = 0.0; // raw mouse motion, the ship's views
    bool mMouseHeld = false;       // cursor hidden and kept in the window
    bool mMouseFree = false;       // M: the cursor left to Windows in the ship's views, the window still in front
    double mClock = 0.0;
    View mWalkReturnView = View::Cockpit;
    Walker mWalker;
    WalkTerrain mWalkTerrain;
    Vec3d mWalkFoot = {}, mWalkVelocity = {}, mWalkPatchCentre = {}, mWalkPatchX = {}, mWalkPatchY = {};
    Vec3d mWalkReturnPos = {}, mWalkReturnForward = {}, mWalkReturnUp = {};
    bool mWalkProbePending = false, mWalkPatchValid = false, mStartWalking = false;
    bool mWalkJump = false, mWalkBob = true, mAudioMuted = false, mAudioReady = false;
    double mWalkNoticeUntil = 0.0;
    ComPtr<ID3D12PipelineState> mWalkGroundPSO, mWorldSoundPSO;
    ComPtr<ID3D12RootSignature> mWorldSoundRoot;
    ComPtr<ID3D12Resource> mWalkPoints, mWalkGround, mWalkReadback, mWorldSound, mWorldReadback;
    XMFLOAT4 mHabitat[6] = {}; // habitat/weather, foot contacts, then observer canopy/height
    float mObserverCanopy=0;
    FootContact CurrentFootContact() const;
    bool mWorldPending = false, mWorldValid = false;
    D3D12_GPU_DESCRIPTOR_HANDLE mWorldTectonics = {}, mWorldPlanet = {}, mWorldClouds = {}, mWorldMaterials = {};
    Vec3d mWorldProbePos = {};
    double mWorldNextProbe = 0.0;
    void InitializeWorld(D3D12_GPU_DESCRIPTOR_HANDLE tectonics, D3D12_GPU_DESCRIPTOR_HANDLE planet,
        D3D12_GPU_DESCRIPTOR_HANDLE clouds, D3D12_GPU_DESCRIPTOR_HANDLE materials);
    void QueueWalkGround();
    void ReadWalkGround();
    void ToggleWalking();
    void UpdateWalking(float dt);
    void QueueWorldSound();
    void ReadWorldSound();
    void UpdateWorldSound(float dt);
    void ToggleAudio();
    void EmitFootstep(float strength);
    void UpdateShip(float dt);
    void UpdateShipFrame(float dt, const Vec3d& faceX, const Vec3d& faceY, const Vec3d& faceZ);
    void PlaceShipAtCamera();
    void HoldMouse(bool hold);
    void SetView(View view);
    double mMouseDx = 0.0;
    double mMouseDy = 0.0;
    UINT mMoveKeys[6] = {};     // physical W S A D Q E, whatever the keyboard layout

    LARGE_INTEGER mFrequency = {};
    LARGE_INTEGER mLastTime = {};
    float mTitleTimer = 0.0f;
    UINT mTitleFrames = 0;
};
