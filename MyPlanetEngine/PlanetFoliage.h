#pragma once
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <d3d12.h>
#include <d3dcompiler.h>
#include <dxgi1_6.h>
#include <wrl.h>
#include <string>
#include <vector>

// The plants placed on the planet (PlanetPlantPlacement), sorted by model and representation on the GPU, and drawn: the
// near ones as meshes, the far ones as impostors (docs/vegetation-planetaire.md). The catalogue's fourteen models: the
// conifer, the broadleaf, then two shrubs for each of the six climates (docs/arbustes-climatiques.md).
class PlanetFoliage {
public:
    struct Sample { double placement, draw, total, sourcePlacement = 0, hizBuild = 0, hizCull = 0; bool hizActive = false; };
    static constexpr UINT DescriptorCount = 14 * 7;
    bool Enabled() const { return mReady; }
    // Throws when the catalogue at `root` is missing or invalid; the plants then stay off.
    // hdr, sun: the scene's two render targets, its light and the surface's sunlit part (D3DApp::SunFormat).
    void Initialize(ID3D12Device*, ID3D12GraphicsCommandList*, const std::wstring& root, DXGI_FORMAT hdr, DXGI_FORMAT sun,
                    DXGI_FORMAT depth, D3D12_CPU_DESCRIPTOR_HANDLE impostorCpu, D3D12_GPU_DESCRIPTOR_HANDLE impostorGpu);
    void ReleaseUploads() { mUploads.clear(); }
    void Classify(ID3D12GraphicsCommandList*, D3D12_GPU_VIRTUAL_ADDRESS frame,
                  ID3D12Resource* sourceInstances, ID3D12Resource* sourceCounters);
    void Draw(ID3D12GraphicsCommandList*, D3D12_GPU_VIRTUAL_ADDRESS frame,
              D3D12_GPU_DESCRIPTOR_HANDLE atmosphere, D3D12_GPU_DESCRIPTOR_HANDLE planetMap);
    void DrawOccluders(ID3D12GraphicsCommandList*, D3D12_GPU_VIRTUAL_ADDRESS frame,
                       D3D12_GPU_DESCRIPTOR_HANDLE atmosphere, D3D12_GPU_DESCRIPTOR_HANDLE planetMap);
    void CullOccluded(ID3D12GraphicsCommandList*, D3D12_GPU_VIRTUAL_ADDRESS frame,
                      D3D12_GPU_DESCRIPTOR_HANDLE hiZ, UINT width, UINT height, UINT mips,
                      UINT viewportWidth, UINT viewportHeight);
    void DrawRemaining(ID3D12GraphicsCommandList*, D3D12_GPU_VIRTUAL_ADDRESS frame,
                       D3D12_GPU_DESCRIPTOR_HANDLE atmosphere, D3D12_GPU_DESCRIPTOR_HANDLE planetMap);
    void ReadStats(); // only after the frame's fence
    std::wstring StatsText() const;
    void SaveStats(const std::wstring& capture, double placement, double draw, double total,
                   const std::vector<Sample>& samples) const;
private:
    using Resource = Microsoft::WRL::ComPtr<ID3D12Resource>;
    // Must match PlanetFoliageCommon.hlsli (cbuffer PlanetFoliageSettings) and PlanetFoliageDepth.hlsli (CullModel).
    struct Settings {
        UINT width, height, viewsX, viewsY;
        float boundsMin[3], radius;
        float boundsMax[3], crown;
        UINT species, reserved, materialCount, flags; // flags: 1 material atlas, 8 precomputed light, 16 masked by the HiZ
        float volumeParams[4];
        float depthBounds[4]; // imposteurs : profondeur reconstruite min, max, validité, erreur (PlanetFoliageDepth.hlsli)
    };
    struct Model {
        Resource meshVertices, meshIndices, impostor[2], meshMaps[3], meshLighting, impostorLighting[2];
        D3D12_INDEX_BUFFER_VIEW meshView = {}, meshReversedView = {};
        Resource meshIndicesReversed;
        Settings meshSettings = {}, proxySettings = {};
        UINT meshIndexCount = 0;
        UINT64 meshBytes = 0, proxyBytes = 0;
        float depthMin = 0, depthMax = 0, depthError = 0; bool depthValid = false;
    };
    static const UINT SourceCapacity = 262144, QueueCapacity = 2 * SourceCapacity, Queues = 6, MaxModels = 14, ArgStride = 28, CounterBytes = 1056;
    bool mReady = false;
    bool mHiZFrame = false;
    Model mModel[MaxModels];
    D3D12_GPU_DESCRIPTOR_HANDLE mImpostorTables[MaxModels] = {};
    Resource mQueues, mArguments, mReset, mReadback, mQuadIndices;
    Resource mVisibility, mCullModels, mCullStats, mCullReadback;
    D3D12_INDEX_BUFFER_VIEW mQuadView = {};
    Microsoft::WRL::ComPtr<ID3D12RootSignature> mClassifyRoot, mDrawRoot;
    Microsoft::WRL::ComPtr<ID3D12PipelineState> mClassifyPso, mFinalizePso, mScatterPso, mProxyPso;
    // Les maillages en profondeur matérielle : leur profondeur seule, puis leur couleur en profondeur égale.
    Microsoft::WRL::ComPtr<ID3D12PipelineState> mMeshDepthPso, mMeshShadePso;
    Microsoft::WRL::ComPtr<ID3D12CommandSignature> mIndirect;
    Microsoft::WRL::ComPtr<ID3D12RootSignature> mCullRoot;
    Microsoft::WRL::ComPtr<ID3D12PipelineState> mCullClearPso, mCullPso, mCullCountPso;
    void DrawRepresentation(ID3D12GraphicsCommandList*, D3D12_GPU_VIRTUAL_ADDRESS,
                            D3D12_GPU_DESCRIPTOR_HANDLE, D3D12_GPU_DESCRIPTOR_HANDLE,
                            UINT rep, bool masked);
    std::vector<Resource> mUploads;
    UINT mStats[36] = {}, mModelStats[2 * MaxModels] = {};
    UINT mTested = 0, mRejectedCandidates = 0, mRejected = 0;
};
