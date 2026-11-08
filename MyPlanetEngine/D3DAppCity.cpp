#include "D3DApp.h"
#include "GpuHelpers.h"
#include <fstream>
#include <cstring>

void D3DApp::UpdateCityFrame(const Vec3d& faceX,const Vec3d& faceY,const Vec3d& faceZ,FXMMATRIX viewProj) {
    mConstants->cityLandGrid={};
    if(!mCity.Ready())return;
    const double a=mCity.Latitude()*XM_PI/180.0,b=mCity.Longitude()*XM_PI/180.0;
    const Vec3d up={cos(a)*cos(b),sin(a),cos(a)*sin(b)},east={-sin(b),0,cos(b)},north={-sin(a)*cos(b),cos(a),-sin(a)*sin(b)};
    auto local=[&](const Vec3d& p){return XMVectorSet(float(Dot(p,faceX)),float(Dot(p,faceY)),float(Dot(p,faceZ)),0);};
    const XMMATRIX model(local(east),local(north),local(up),XMVectorSetW(local(up*PlanetRadius-mCamPos),1));
    const Vec3d offset=mCamPos-up*PlanetRadius;
    const XMFLOAT3 camera={float(Dot(offset,east)),float(Dot(offset,north)),float(Dot(offset,up))};
    const XMFLOAT3 sun={float(Dot(mSunDir,east)),float(Dot(mSunDir,north)),float(Dot(mSunDir,up))};
    mCity.Update(model,viewProj,camera,sun,mClientHeight);
    const XMMATRIX inverse=XMMatrixInverse(nullptr,model);
    XMStoreFloat4x4(&mConstants->cityFromFace,XMMatrixTranspose(inverse));
    XMStoreFloat4x4(&mConstants->citySunShadow,XMMatrixTranspose(inverse*mCity.Shadow()));
    mConstants->cityLandGrid=mCity.LandGrid();
    memcpy(mConstants->cityLandBits,mCity.LandBits().data(),sizeof(mConstants->cityLandBits));
}

void D3DApp::ApplyCityWalking() {
    if(!mCity.Ready()||!mWalkPatchValid)return;
    const double a=mCity.Latitude()*XM_PI/180.0,b=mCity.Longitude()*XM_PI/180.0;
    const Vec3d up={cos(a)*cos(b),sin(a),cos(a)*sin(b)},east={-sin(b),0,cos(b)},north={-sin(a)*cos(b),cos(a),-sin(a)*sin(b)};
    const Vec3d origin=up*PlanetRadius;
    for(int y=0;y<WalkTerrain::Side;++y)for(int x=0;x<WalkTerrain::Side;++x){
        const Vec3d point=mWalkPatchCentre+mWalkPatchX*((x-WalkTerrain::Side/2)*WalkTerrain::Cell)+mWalkPatchY*((y-WalkTerrain::Side/2)*WalkTerrain::Cell);
        const Vec3d offset=point-origin;double height=mWalkTerrain.heights[y*WalkTerrain::Side+x];
        if(mCity.Surface(Dot(offset,east),Dot(offset,north),height,height))mWalkTerrain.heights[y*WalkTerrain::Side+x]=float(height);
    }
}

void D3DApp::ConstrainCityWalking(Vec3d& next) {
    if(!mCity.Ready())return;
    const double a=mCity.Latitude()*XM_PI/180.0,b=mCity.Longitude()*XM_PI/180.0;
    const Vec3d up={cos(a)*cos(b),sin(a),cos(a)*sin(b)},east={-sin(b),0,cos(b)},north={-sin(a)*cos(b),cos(a),-sin(a)*sin(b)};
    const Vec3d origin=up*PlanetRadius,old=mWalkFoot-origin,wanted=next*PlanetRadius-origin;
    double x=Dot(wanted,east),y=Dot(wanted,north);
    if(!mCity.ResolveMovement(Dot(old,east),Dot(old,north),x,y,mWalker.elevation))return;
    next=Normalize(origin+east*x+north*y);
    const Vec3d foot=next*PlanetRadius-mWalkPatchCentre;
    mWalker.x=Dot(foot,mWalkPatchX);mWalker.y=Dot(foot,mWalkPatchY);
    mWalker.vx=mWalker.vy=0;
}

void D3DApp::ExportCityGround(D3D12_GPU_DESCRIPTOR_HANDLE tectonics) {
    std::ifstream input(mSettings.cityProbe);
    double lat=0,lon=0,cell=0;UINT side=0;std::string extra;
    if(!(input>>lat>>lon>>side>>cell) || (input>>extra) || !std::isfinite(lat) || !std::isfinite(lon)
       || !std::isfinite(cell) || std::abs(lat)>89.9 || std::abs(lon)>180 || side<3 || side>1025
       || !(side&1) || cell<.25 || cell>20)
        throw std::runtime_error("City terrain request expects latitude longitude odd-side[3,1025] cell-metres[.25,20].");
    const double a=lat*XM_PI/180.0,b=lon*XM_PI/180.0;
    const Vec3d up={cos(a)*cos(b),sin(a),cos(a)*sin(b)},east={-sin(b),0,cos(b)},north={-sin(a)*cos(b),cos(a),-sin(a)*sin(b)};
    const double values[12]={up.x*PlanetRadius,up.y*PlanetRadius,up.z*PlanetRadius,double(side),
                             east.x,east.y,east.z,cell,north.x,north.y,north.z,0};
    auto points=CreateBuffer(md3dDevice.Get(),256,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
    void* mapped=nullptr;CD3DX12_RANGE none(0,0);Check(points->Map(0,&none,&mapped),"City probe map failed.");
    memcpy(mapped,values,sizeof(values));points->Unmap(0,nullptr);
    const UINT bytes=side*side*4;
    auto heights=CreateBuffer(md3dDevice.Get(),bytes,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    auto readback=CreateBuffer(md3dDevice.Get(),bytes,D3D12_HEAP_TYPE_READBACK,D3D12_RESOURCE_STATE_COPY_DEST);
    auto shader=LoadShader(L"CityGround.cso");D3D12_COMPUTE_PIPELINE_STATE_DESC desc={};
    desc.pRootSignature=mComputeRootSignature.Get();desc.CS=CD3DX12_SHADER_BYTECODE(shader.Get());
    ComPtr<ID3D12PipelineState> pso;Check(md3dDevice->CreateComputePipelineState(&desc,IID_PPV_ARGS(&pso)),"City probe PSO failed.");
    Check(mCommandAllocator->Reset(),"City allocator reset failed.");Check(mCommandList->Reset(mCommandAllocator.Get(),pso.Get()),"City command reset failed.");
    ID3D12DescriptorHeap* heaps[]={mSrvHeap.Get()};mCommandList->SetDescriptorHeaps(1,heaps);
    mCommandList->SetComputeRootSignature(mComputeRootSignature.Get());
    mCommandList->SetComputeRootConstantBufferView(0,points->GetGPUVirtualAddress());
    mCommandList->SetComputeRootUnorderedAccessView(1,heights->GetGPUVirtualAddress());
    mCommandList->SetComputeRootDescriptorTable(2,tectonics);mCommandList->Dispatch((side*side+63)/64,1,1);
    auto barrier=CD3DX12_RESOURCE_BARRIER::Transition(heights.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_COPY_SOURCE);
    mCommandList->ResourceBarrier(1,&barrier);mCommandList->CopyResource(readback.Get(),heights.Get());
    Check(mCommandList->Close(),"City probe close failed.");ID3D12CommandList* lists[]={mCommandList.Get()};
    mCommandQueue->ExecuteCommandLists(1,lists);WaitForPreviousFrame();
    CD3DX12_RANGE range(0,bytes);Check(readback->Map(0,&range,&mapped),"City readback map failed.");
    std::ofstream output(mSettings.cityProbe+L".bin",std::ios::binary);
    output.write("CITYGRD1",8);output.write(reinterpret_cast<const char*>(&side),4);
    output.write(reinterpret_cast<const char*>(&mSettings.seed),4);
    for(double v:{lat,lon,cell})output.write(reinterpret_cast<const char*>(&v),8);
    output.write(static_cast<const char*>(mapped),bytes);readback->Unmap(0,&none);
    if(!output)throw std::runtime_error("City terrain output write failed.");
}
