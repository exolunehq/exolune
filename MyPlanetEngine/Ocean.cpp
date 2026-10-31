#include "Ocean.h"
#include "GpuHelpers.h"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>
using namespace DirectX;
using Microsoft::WRL::ComPtr;
namespace {
    constexpr D3D12_RESOURCE_STATES ReadAll = D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE;
    void Transition(ID3D12GraphicsCommandList* cmd,ID3D12Resource* r,D3D12_RESOURCE_STATES a,D3D12_RESOURCE_STATES b) {
        auto barrier=CD3DX12_RESOURCE_BARRIER::Transition(r,a,b);cmd->ResourceBarrier(1,&barrier);
    }
    float Fraction(double x) { return float(x-std::floor(x)); }
}
D3D12_CPU_DESCRIPTOR_HANDLE Ocean::Cpu(UINT index) const {
    return CD3DX12_CPU_DESCRIPTOR_HANDLE(mHeap->GetCPUDescriptorHandleForHeapStart(),mBase+index,mStride);
}
D3D12_GPU_DESCRIPTOR_HANDLE Ocean::Gpu(UINT index) const {
    return CD3DX12_GPU_DESCRIPTOR_HANDLE(mHeap->GetGPUDescriptorHandleForHeapStart(),mBase+index,mStride);
}
void Ocean::Initialize(ID3D12Device* device,ID3D12DescriptorHeap* heap,UINT descriptorBase) {
    mDevice=device;mHeap=heap;mBase=descriptorBase;mStride=device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
    mConstantsBuffer=CreateBuffer(device,512,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
    D3D12_RANGE empty={0,0};
    Check(mConstantsBuffer->Map(0,&empty,reinterpret_cast<void**>(&mConstants)),"Ocean constants mapping failed.");
    *mConstants={};
    mConstants->lengths={1103.0f,113.1f,11.57f,1.183f};
    float* lengths=&mConstants->lengths.x;float* kmin=&mConstants->kmin.x;float* kmax=&mConstants->kmax.x;
    for(UINT c=0;c<Cascades;++c) {
        kmin[c]=c==0?XM_PI/lengths[c]:2.0f*XM_PI*6.0f/lengths[c];
        kmax[c]=c+1<Cascades?2.0f*XM_PI*6.0f/lengths[c+1]:XM_PI*N/lengths[c]*0.98f;
    }
    mConstants->settings={1.25f,0.0012f,600.0f,1.0f};
    mConstants->foamParams={0.68f,2.0f,1.0f,0.22f};
    SetWind(12.0f,70.0f,1.8f);
    mHeight=CreateBuffer(device,16,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mHeightReadback=CreateBuffer(device,16,D3D12_HEAP_TYPE_READBACK,D3D12_RESOURCE_STATE_COPY_DEST);
    D3D12_RANGE heightRange={0,16};
    Check(mHeightReadback->Map(0,&heightRange,reinterpret_cast<void**>(&mHeightValues)),"Ocean height readback failed.");
    const UINT64 bytes=UINT64(Cascades)*N*N*sizeof(XMFLOAT4);
    mH0=CreateBuffer(device,bytes,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    for(UINT i=0;i<2;++i) {
        mSpectrum[i]=CreateBuffer(device,bytes,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
        mRows[i]=CreateBuffer(device,bytes,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    }
    for(UINT i=0;i<6;++i) {
        auto& img=mImages[i];img.size=i<3?N:FoamN;img.layers=i<3?Cascades:i==3?1:2;img.mips=i<3?Mips:FoamMips;
        auto desc=CD3DX12_RESOURCE_DESC::Tex2D(i==3?DXGI_FORMAT_R8G8B8A8_UNORM:DXGI_FORMAT_R16G16B16A16_FLOAT,
            img.size,img.size,UINT16(img.layers),UINT16(img.mips),1,0,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
        auto properties=CD3DX12_HEAP_PROPERTIES(D3D12_HEAP_TYPE_DEFAULT);
        Check(device->CreateCommittedResource(&properties,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
            nullptr,IID_PPV_ARGS(&img.resource)),"Ocean texture creation failed.");
        D3D12_SHADER_RESOURCE_VIEW_DESC srv={};
        srv.Format=desc.Format;srv.ViewDimension=D3D12_SRV_DIMENSION_TEXTURE2DARRAY;
        srv.Shader4ComponentMapping=D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        srv.Texture2DArray.MipLevels=img.mips;srv.Texture2DArray.ArraySize=img.layers;
        device->CreateShaderResourceView(img.resource.Get(),&srv,Cpu(i));
    }
    // Each group has three SRVs/UAVs per mip. Single-image passes only use the first descriptor.
    for(UINT g=0;g<4;++g) for(UINT m=0;m<FoamMips;++m) for(UINT slot=0;slot<3;++slot) {
        UINT image=g==0?slot:g+2;auto& img=mImages[image];
        UINT mip=std::min(m,img.mips-1);
        D3D12_SHADER_RESOURCE_VIEW_DESC srv={};
        srv.Format=img.resource->GetDesc().Format;srv.ViewDimension=D3D12_SRV_DIMENSION_TEXTURE2DARRAY;
        srv.Shader4ComponentMapping=D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        srv.Texture2DArray.MostDetailedMip=mip;srv.Texture2DArray.MipLevels=1;srv.Texture2DArray.ArraySize=img.layers;
        device->CreateShaderResourceView(img.resource.Get(),&srv,Cpu(SrvMip(g,m)+slot));
        D3D12_UNORDERED_ACCESS_VIEW_DESC uav={};uav.Format=srv.Format;uav.ViewDimension=D3D12_UAV_DIMENSION_TEXTURE2DARRAY;
        uav.Texture2DArray.MipSlice=mip;uav.Texture2DArray.ArraySize=img.layers;
        device->CreateUnorderedAccessView(img.resource.Get(),nullptr,&uav,Cpu(UavMip(g,m)+slot));
    }
    // Full-resolution inputs for the foam update: displacement, derivative and the previous foam ping.
    for(UINT ping=0;ping<2;++ping) for(UINT slot=0;slot<3;++slot)
        device->CopyDescriptorsSimple(1,Cpu(246+3*ping+slot),Cpu(slot==2?4+ping:slot),D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
    CD3DX12_DESCRIPTOR_RANGE outRange(D3D12_DESCRIPTOR_RANGE_TYPE_UAV,3,2),inRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,3,2);
    CD3DX12_ROOT_PARAMETER params[8];
    params[0].InitAsConstantBufferView(1);
    params[1].InitAsShaderResourceView(0);params[2].InitAsShaderResourceView(1);
    params[3].InitAsUnorderedAccessView(0);params[4].InitAsUnorderedAccessView(1);
    params[5].InitAsDescriptorTable(1,&outRange);params[6].InitAsDescriptorTable(1,&inRange);
    params[7].InitAsConstants(4,2);
    CD3DX12_STATIC_SAMPLER_DESC sampler(0,D3D12_FILTER_MIN_MAG_MIP_LINEAR);
    auto rootDesc=CD3DX12_ROOT_SIGNATURE_DESC(8,params,1,&sampler);
    mRoot=CreateRootSignature(device,rootDesc);
    auto pipeline=[&](const wchar_t* path,ComPtr<ID3D12PipelineState>& target) {
        auto code=LoadShader(path);D3D12_COMPUTE_PIPELINE_STATE_DESC d={};d.pRootSignature=mRoot.Get();
        d.CS={code->GetBufferPointer(),code->GetBufferSize()};
        Check(device->CreateComputePipelineState(&d,IID_PPV_ARGS(&target)),"Ocean pipeline creation failed.");
    };
    pipeline(L"OceanInit.cso",mInit);pipeline(L"OceanEvolve.cso",mEvolve);
    pipeline(L"OceanRows.cso",mFftRows);pipeline(L"OceanColumns.cso",mFftColumns);
    pipeline(L"OceanMipWaves.cso",mMipWaves);pipeline(L"OceanPores.cso",mPores);
    pipeline(L"OceanFoam.cso",mFoamUpdate);pipeline(L"OceanMipSingle.cso",mMipSingle);
    pipeline(L"OceanCameraHeight.cso",mCameraHeight);
}
float Ocean::SurfaceHeight() const {
    if(mFirst || !mHeightValues || !std::isfinite(mHeightValues->x)) return 0.0f;
    return std::max(-64.0f,std::min(64.0f,mHeightValues->x));
}
void Ocean::SetWind(float speed,float degrees,float hs) {
    speed=std::max(0.0f,std::min(45.0f,speed));hs=std::max(0.0f,std::min(12.0f,hs));
    float angle=XMConvertToRadians(degrees);
    if(mConstants->wind.x!=speed || mConstants->wind.y!=angle || mConstants->swell.x!=hs) mSpectrumDirty=true;
    mConstants->wind={speed,angle,90000.0f,3.3f};
    float k=2.0f*XM_PI/120.0f;
    mConstants->swell={hs,angle-XMConvertToRadians(24.0f),std::sqrt(9.81f*k),48.0f};
}
void Ocean::TransitionMip(ID3D12GraphicsCommandList* cmd,UINT image,UINT mip,D3D12_RESOURCE_STATES before,D3D12_RESOURCE_STATES after) {
    auto& img=mImages[image];std::vector<D3D12_RESOURCE_BARRIER> barriers(img.layers);
    for(UINT layer=0;layer<img.layers;++layer)
        barriers[layer]=CD3DX12_RESOURCE_BARRIER::Transition(img.resource.Get(),before,after,mip+layer*img.mips);
    cmd->ResourceBarrier(UINT(barriers.size()),barriers.data());
}
void Ocean::Mipmaps(ID3D12GraphicsCommandList* cmd,UINT group) {
    UINT image=group==0?0:group+2,count=group==0?3:1;
    auto& img=mImages[image];
    for(UINT i=0;i<count;++i) TransitionMip(cmd,image+i,0,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
    cmd->SetPipelineState(group==0?mMipWaves.Get():mMipSingle.Get());
    for(UINT m=1;m<img.mips;++m) {
        UINT side=img.size>>m;const UINT constants[4]={side,0,0,0};
        cmd->SetComputeRoot32BitConstants(7,4,constants,0);
        cmd->SetComputeRootDescriptorTable(6,Gpu(SrvMip(group,m-1)));
        cmd->SetComputeRootDescriptorTable(5,Gpu(UavMip(group,m)));
        cmd->Dispatch((side+7)/8,(side+7)/8,img.layers);
        for(UINT i=0;i<count;++i) TransitionMip(cmd,image+i,m,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
    }
    for(UINT i=0;i<count;++i) Transition(cmd,mImages[image+i].resource.Get(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,ReadAll);
}
void Ocean::Update(ID3D12GraphicsCommandList* cmd,double x,double y,double time,float dt,bool reset,float elevation) {
    reset=reset||mFirst||mSpectrumDirty;
    mConstants->time={float(std::fmod(time,600.0)),std::max(0.0f,std::min(dt,0.1f)),1.0f,0};
    const float* lengths=&mConstants->lengths.x;
    for(UINT c=0;c<Cascades;++c) mConstants->origin[c]={Fraction(x/lengths[c]),Fraction(y/lengths[c]),0,0};
    const float sizes[2]={128.0f,1024.0f};
    for(UINT l=0;l<2;++l) {
        double ts=sizes[l]/FoamN;int cx=int(std::floor(x/ts)),cy=int(std::floor(y/ts));
        mConstants->foamOrigin[l]={Fraction(x/sizes[l]),Fraction(y/sizes[l]),float(ts),sizes[l]};
        mConstants->foamGrid[l]={float((x/ts-std::floor(x/ts))*ts),float((y/ts-std::floor(y/ts))*ts),0,0};
        mConstants->foamSnap[l]={cx,cy,mSnap[l].x,mSnap[l].y};mSnap[l]={cx,cy};
    }
    double ca=std::cos(mConstants->wind.y),sa=std::sin(mConstants->wind.y);
    double driftX=0.03*mConstants->wind.x*ca*time,driftY=0.03*mConstants->wind.x*sa*time;
    mConstants->poreOrigin={Fraction((x-driftX)*0.23),Fraction((y-driftY)*0.23),
        Fraction((x-driftX)*0.71+0.37),Fraction((y-driftY)*0.71+0.71)};
    mConstants->streakOrigin={Fraction((x*ca+y*sa)*0.035),Fraction((-x*sa+y*ca)*0.11),0,0};
    UINT destination=1-mActive;
    mConstants->render={float(destination),1.0f,reset?1.0f:0.0f,elevation};
    ID3D12DescriptorHeap* heaps[]={mHeap};cmd->SetDescriptorHeaps(1,heaps);
    cmd->SetComputeRootSignature(mRoot.Get());
    cmd->SetComputeRootConstantBufferView(0,ConstantsAddress());
    if(mFirst) {
        cmd->SetPipelineState(mPores.Get());cmd->SetComputeRootDescriptorTable(5,Gpu(UavMip(1,0)));
        cmd->Dispatch(FoamN/8,FoamN/8,1);Mipmaps(cmd,1);
        float zeros[4]={};
        for(UINT ping=0;ping<2;++ping) {
            for(UINT m=0;m<FoamMips;++m) {
                UINT u=UavMip(2+ping,m);
                cmd->ClearUnorderedAccessViewFloat(Gpu(u),Cpu(u),mImages[4+ping].resource.Get(),zeros,0,nullptr);
            }
            Transition(cmd,mImages[4+ping].resource.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,ReadAll);
        }
    } else {
        for(UINT i=0;i<3;++i) Transition(cmd,mImages[i].resource.Get(),ReadAll,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    }
    if(mSpectrumDirty) {
        if(!mFirst) Transition(cmd,mH0.Get(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
        cmd->SetPipelineState(mInit.Get());cmd->SetComputeRootUnorderedAccessView(3,mH0->GetGPUVirtualAddress());
        cmd->Dispatch(N/16,N/16,Cascades);
        Transition(cmd,mH0.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
        mSpectrumDirty=false;
    }
    cmd->SetPipelineState(mEvolve.Get());cmd->SetComputeRootShaderResourceView(1,mH0->GetGPUVirtualAddress());
    cmd->SetComputeRootUnorderedAccessView(3,mSpectrum[0]->GetGPUVirtualAddress());
    cmd->SetComputeRootUnorderedAccessView(4,mSpectrum[1]->GetGPUVirtualAddress());
    cmd->Dispatch(N/16,N/16,Cascades);
    for(UINT i=0;i<2;++i) Transition(cmd,mSpectrum[i].Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
    cmd->SetPipelineState(mFftRows.Get());
    for(UINT i=0;i<2;++i) { cmd->SetComputeRootShaderResourceView(1+i,mSpectrum[i]->GetGPUVirtualAddress());cmd->SetComputeRootUnorderedAccessView(3+i,mRows[i]->GetGPUVirtualAddress()); }
    cmd->Dispatch(N,Cascades,1);
    for(UINT i=0;i<2;++i) Transition(cmd,mRows[i].Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
    cmd->SetPipelineState(mFftColumns.Get());
    for(UINT i=0;i<2;++i) cmd->SetComputeRootShaderResourceView(1+i,mRows[i]->GetGPUVirtualAddress());
    cmd->SetComputeRootDescriptorTable(5,Gpu(UavMip(0,0)));cmd->Dispatch(N,Cascades,1);
    for(UINT i=0;i<2;++i) {
        Transition(cmd,mSpectrum[i].Get(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
        Transition(cmd,mRows[i].Get(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    }
    Mipmaps(cmd,0);
    Transition(cmd,mImages[4+destination].resource.Get(),ReadAll,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    cmd->SetPipelineState(mFoamUpdate.Get());
    cmd->SetComputeRootDescriptorTable(5,Gpu(UavMip(2+destination,0)));
    cmd->SetComputeRootDescriptorTable(6,Gpu(246+3*mActive));
    cmd->Dispatch(FoamN/8,FoamN/8,2);
    Mipmaps(cmd,2+destination);
    mActive=destination;
    cmd->SetPipelineState(mCameraHeight.Get());
    cmd->SetComputeRootDescriptorTable(6,Gpu(246+3*mActive));
    cmd->SetComputeRootUnorderedAccessView(3,mHeight->GetGPUVirtualAddress());
    cmd->Dispatch(1,1,1);
    Transition(cmd,mHeight.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_COPY_SOURCE);
    cmd->CopyBufferRegion(mHeightReadback.Get(),0,mHeight.Get(),0,16);
    Transition(cmd,mHeight.Get(),D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    mFirst=false;
}
