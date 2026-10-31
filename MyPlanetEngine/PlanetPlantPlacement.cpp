#include "PlanetPlantPlacement.h"
#include "GpuHelpers.h"
using Microsoft::WRL::ComPtr;
namespace {
// The scratch buffers: on the GPU, written by the passes.
ComPtr<ID3D12Resource> Buffer(ID3D12Device* device,UINT64 bytes) {
    return CreateBuffer(device,bytes,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
}
void Barrier(ID3D12GraphicsCommandList* list) { auto b=CD3DX12_RESOURCE_BARRIER::UAV(nullptr); list->ResourceBarrier(1,&b); }
}

void PlanetPlantPlacement::Initialize(ID3D12Device* device,ID3D12RootSignature* objectRoot) {
    mRecords=Buffer(device,UINT64(MaxTiles)*16); mValues=Buffer(device,UINT64(MaxTiles)*8); mOffsets=Buffer(device,UINT64(MaxTiles)*8);
    const UINT blocks=(MaxTiles+ScanGroup-1)/ScanGroup, super=(blocks+ScanGroup-1)/ScanGroup;
    mBlockSums=Buffer(device,UINT64(blocks)*8); mBlockOffsets=Buffer(device,UINT64(blocks)*8);
    mSuperSums=Buffer(device,UINT64(super)*8); mSuperOffsets=Buffer(device,UINT64(super)*8); mTotals=Buffer(device,8);
    mTiles=Buffer(device,UINT64(TileCapacity)*16); mTileDispatch=Buffer(device,16);
    mMasks=Buffer(device,UINT64(TileCapacity)*8); mScratch=Buffer(device,UINT64(TileCapacity)*16*64);
    mGround=Buffer(device,UINT64(GroundSlots)*2*32); mGroundClaims=Buffer(device,UINT64(GroundSlots)*4); mGroundZero=Buffer(device,UINT64(GroundSlots)*32); // committed: zeroed
    CD3DX12_ROOT_PARAMETER sp[4]; sp[0].InitAsUnorderedAccessView(0); sp[1].InitAsUnorderedAccessView(1);
    sp[2].InitAsUnorderedAccessView(2); sp[3].InitAsConstants(1,0);
    mScanRoot=CreateRootSignature(device,CD3DX12_ROOT_SIGNATURE_DESC(4,sp));
    CD3DX12_ROOT_PARAMETER cp[9]; for(UINT i=0;i<8;++i) cp[i].InitAsUnorderedAccessView(i); cp[8].InitAsConstants(2,1);
    mCompactRoot=CreateRootSignature(device,CD3DX12_ROOT_SIGNATURE_DESC(9,cp));
    auto make=[&](const wchar_t* file,ID3D12RootSignature* root,Pso& out) {
        auto code=LoadShader(file); D3D12_COMPUTE_PIPELINE_STATE_DESC desc={}; desc.pRootSignature=root; desc.CS=CD3DX12_SHADER_BYTECODE(code.Get());
        Check(device->CreateComputePipelineState(&desc,IID_PPV_ARGS(&out)),"Planet plant pipeline creation failed.");
    };
    make(L"PlanetPlantCandidates.cso",objectRoot,mCull); make(L"PlanetPlantPlacement.cso",objectRoot,mPlacement);
    make(L"PlanetPlantScan.cso",mScanRoot.Get(),mScan); make(L"PlanetPlantScanAdd.cso",mScanRoot.Get(),mAdd);
    make(L"PlanetPlantCompact.cso",mCompactRoot.Get(),mCompact); make(L"PlanetPlantClear.cso",mCompactRoot.Get(),mClear);
    make(L"PlanetPlantScatter.cso",mCompactRoot.Get(),mScatter);
}

void PlanetPlantPlacement::Scan(ID3D12GraphicsCommandList* list,UINT length) {
    const UINT blocks=(length+ScanGroup-1)/ScanGroup, super=(blocks+ScanGroup-1)/ScanGroup;
    list->SetComputeRootSignature(mScanRoot.Get()); list->SetPipelineState(mScan.Get());
    auto scan=[&](Resource& in,Resource& out,Resource& sums,UINT n) {
        list->SetComputeRootUnorderedAccessView(0,in->GetGPUVirtualAddress()); list->SetComputeRootUnorderedAccessView(1,out->GetGPUVirtualAddress());
        list->SetComputeRootUnorderedAccessView(2,sums->GetGPUVirtualAddress()); list->SetComputeRoot32BitConstant(3,n,0);
        list->Dispatch((n+ScanGroup-1)/ScanGroup,1,1); Barrier(list);
    };
    scan(mValues,mOffsets,mBlockSums,length); scan(mBlockSums,mBlockOffsets,mSuperSums,blocks); scan(mSuperSums,mSuperOffsets,mTotals,super);
    list->SetPipelineState(mAdd.Get());
    list->SetComputeRootUnorderedAccessView(0,mSuperOffsets->GetGPUVirtualAddress()); list->SetComputeRootUnorderedAccessView(1,mBlockOffsets->GetGPUVirtualAddress());
    list->SetComputeRoot32BitConstant(3,blocks,0); list->Dispatch((blocks+ScanGroup-1)/ScanGroup,1,1); Barrier(list);
    list->SetComputeRootUnorderedAccessView(0,mBlockOffsets->GetGPUVirtualAddress()); list->SetComputeRootUnorderedAccessView(1,mOffsets->GetGPUVirtualAddress());
    list->SetComputeRoot32BitConstant(3,length,0); list->Dispatch((length+ScanGroup-1)/ScanGroup,1,1); Barrier(list);
}

void PlanetPlantPlacement::Run(ID3D12GraphicsCommandList* list,ID3D12RootSignature* objectRoot,ID3D12CommandSignature* dispatchSignature,
    D3D12_GPU_VIRTUAL_ADDRESS frame,ID3D12Resource* mesh,ID3D12Resource* instances,ID3D12Resource* counters,
    D3D12_GPU_DESCRIPTOR_HANDLE materials,D3D12_GPU_DESCRIPTOR_HANDLE planetMap,D3D12_GPU_DESCRIPTOR_HANDLE tectonics,
    const void* placementConstants,UINT constantWords,UINT planes) {
    const UINT tileCount=512*512*7*planes;

    auto bindObject=[&](bool heavy) {
        list->SetComputeRootSignature(objectRoot); list->SetComputeRootConstantBufferView(0,frame);
        list->SetComputeRootShaderResourceView(1,mesh->GetGPUVirtualAddress()); list->SetComputeRootUnorderedAccessView(2,instances->GetGPUVirtualAddress());
        list->SetComputeRootUnorderedAccessView(3,counters->GetGPUVirtualAddress()); list->SetComputeRootDescriptorTable(4,materials);
        list->SetComputeRoot32BitConstants(5,constantWords,placementConstants,0);
        list->SetComputeRootUnorderedAccessView(6,mRecords->GetGPUVirtualAddress()); list->SetComputeRootUnorderedAccessView(7,mValues->GetGPUVirtualAddress());
        if (heavy) { list->SetComputeRootShaderResourceView(8,mTiles->GetGPUVirtualAddress()); list->SetComputeRootShaderResourceView(9,mTileDispatch->GetGPUVirtualAddress()); }
        list->SetComputeRootDescriptorTable(10,planetMap); list->SetComputeRootDescriptorTable(18,tectonics);
        list->SetComputeRootUnorderedAccessView(11,mRecords->GetGPUVirtualAddress()); list->SetComputeRootUnorderedAccessView(12,mValues->GetGPUVirtualAddress());
        list->SetComputeRootUnorderedAccessView(13,mScratch->GetGPUVirtualAddress()); list->SetComputeRootUnorderedAccessView(14,mMasks->GetGPUVirtualAddress());
    };
    bindObject(false); list->SetPipelineState(mCull.Get()); list->Dispatch(512/8,512/8,7*planes); Barrier(list);
    Scan(list,tileCount);
    auto bindCompact=[&](UINT length,UINT capacity) {
        list->SetComputeRootSignature(mCompactRoot.Get());
        ID3D12Resource* resources[8]={mRecords.Get(),mValues.Get(),mOffsets.Get(),mTotals.Get(),mTiles.Get(),mTileDispatch.Get(),counters,mMasks.Get()};
        for(UINT i=0;i<8;++i) list->SetComputeRootUnorderedAccessView(i,resources[i]->GetGPUVirtualAddress());
        const UINT data[2]={length,capacity}; list->SetComputeRoot32BitConstants(8,2,data,0);
    };
    bindCompact(tileCount,TileCapacity); list->SetPipelineState(mCompact.Get()); list->Dispatch((tileCount+255)/256,1,1); Barrier(list);
    bindCompact(TileCapacity,SourceCapacity); list->SetPipelineState(mClear.Get()); list->Dispatch((TileCapacity+255)/256,1,1); Barrier(list);
    const D3D12_RESOURCE_BARRIER beforeHeavy[2]={
        CD3DX12_RESOURCE_BARRIER::Transition(mTiles.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mTileDispatch.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT) };
    { // this frame's claims cleared; after a jump, the tables too
        const UINT64 table=UINT64(GroundSlots)*32;
        const UINT barriers=mGroundReset ? 3u : 2u;
        const D3D12_RESOURCE_BARRIER toCopy[3]={
            CD3DX12_RESOURCE_BARRIER::Transition(mGroundClaims.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_COPY_DEST),
            CD3DX12_RESOURCE_BARRIER::Transition(mGroundZero.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_COPY_SOURCE),
            CD3DX12_RESOURCE_BARRIER::Transition(mGround.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_COPY_DEST) };
        list->ResourceBarrier(barriers,toCopy); list->CopyBufferRegion(mGroundClaims.Get(),0,mGroundZero.Get(),0,UINT64(GroundSlots)*4);
        if (mGroundReset) for (UINT64 half=0;half<2;++half) list->CopyBufferRegion(mGround.Get(),half*table,mGroundZero.Get(),0,table);
        const D3D12_RESOURCE_BARRIER toWrite[3]={
            CD3DX12_RESOURCE_BARRIER::Transition(mGroundClaims.Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
            CD3DX12_RESOURCE_BARRIER::Transition(mGroundZero.Get(),D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
            CD3DX12_RESOURCE_BARRIER::Transition(mGround.Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_UNORDERED_ACCESS) };
        list->ResourceBarrier(barriers,toWrite);
        mGroundReset=false;
    }
    list->ResourceBarrier(2,beforeHeavy); bindObject(true); list->SetPipelineState(mPlacement.Get());
    const UINT64 table=UINT64(GroundSlots)*32;
    list->SetComputeRootUnorderedAccessView(15,mGround->GetGPUVirtualAddress()+table*mGroundParity);
    list->SetComputeRootUnorderedAccessView(16,mGround->GetGPUVirtualAddress()+table*(mGroundParity^1u));
    list->SetComputeRootUnorderedAccessView(17,mGroundClaims->GetGPUVirtualAddress()); mGroundParity^=1u;
    list->ExecuteIndirect(dispatchSignature,1,mTileDispatch.Get(),0,nullptr,0); Barrier(list);
    const D3D12_RESOURCE_BARRIER afterHeavy[2]={
        CD3DX12_RESOURCE_BARRIER::Transition(mTiles.Get(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
        CD3DX12_RESOURCE_BARRIER::Transition(mTileDispatch.Get(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS) };
    list->ResourceBarrier(2,afterHeavy);
    Scan(list,TileCapacity);
    list->SetComputeRootSignature(mCompactRoot.Get());
    ID3D12Resource* scatterResources[6]={mMasks.Get(),mScratch.Get(),instances,mOffsets.Get(),mTotals.Get(),counters};
    for (UINT i=0;i<6;++i) list->SetComputeRootUnorderedAccessView(i,scatterResources[i]->GetGPUVirtualAddress());
    const UINT scatterSettings[2]={TileCapacity,SourceCapacity}; list->SetComputeRoot32BitConstants(8,2,scatterSettings,0);
    list->SetPipelineState(mScatter.Get()); list->Dispatch((TileCapacity+255)/256,1,1); Barrier(list);
}
