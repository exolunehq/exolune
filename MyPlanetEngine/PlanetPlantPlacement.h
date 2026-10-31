#pragma once
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <d3d12.h>
#include <d3dcompiler.h>
#include <wrl.h>

// Deterministic admission of planetary plant tiles and their fine/coarse instances.
class PlanetPlantPlacement {
public:
    void Initialize(ID3D12Device*, ID3D12RootSignature* objectRoot);
    void Run(ID3D12GraphicsCommandList*, ID3D12RootSignature* objectRoot, ID3D12CommandSignature* dispatchSignature,
             D3D12_GPU_VIRTUAL_ADDRESS frame, ID3D12Resource* mesh, ID3D12Resource* instances, ID3D12Resource* counters,
              D3D12_GPU_DESCRIPTOR_HANDLE materials, D3D12_GPU_DESCRIPTOR_HANDLE planetMap, D3D12_GPU_DESCRIPTOR_HANDLE tectonics,
             const void* placementConstants, UINT constantWords, UINT planes);
    // A jump of the camera: the kept ground starts again, its tables cleared at the next Run, so that a place's plants do
    // not depend on the places seen before it, to the last bit.
    void Reset() { mGroundReset = true; }
private:
    using Resource = Microsoft::WRL::ComPtr<ID3D12Resource>;
    using Pso = Microsoft::WRL::ComPtr<ID3D12PipelineState>;
    static const UINT TileCapacity = 262144, SourceCapacity = 262144, MaxTiles = 512*512*7*3, ScanGroup = 256;
    Resource mRecords, mValues, mOffsets, mBlockSums, mBlockOffsets, mSuperSums, mSuperOffsets, mTotals;
    Resource mTiles, mTileDispatch, mMasks, mScratch;
    // The tiles' exact ground, kept from frame to frame (PlantPlacement.hlsli, GroundCached): two tables, read and
    // written in turn, and this frame's claims of their slots, cleared from a zeroed buffer.
    static const UINT GroundSlots = 1u << 20;
    Resource mGround, mGroundClaims, mGroundZero;
    UINT mGroundParity = 0;
    bool mGroundReset = true;
    Microsoft::WRL::ComPtr<ID3D12RootSignature> mScanRoot, mCompactRoot;
    Pso mCull, mPlacement, mScan, mAdd, mCompact, mClear, mScatter;
    void Scan(ID3D12GraphicsCommandList*, UINT length);
};
