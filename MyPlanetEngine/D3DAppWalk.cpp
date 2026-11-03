// Walking and the environmental listener. No terrain modification and no per-frame GPU wait.
#include "D3DApp.h"
#include "GpuHelpers.h"
#include "Ocean.h"
#include <algorithm>
#include <cstring>

namespace {
    float Smooth(float a,float b,float value) {
        const float t=std::min(std::max((value-a)/(b-a),0.0f),1.0f); return t*t*(3-2*t);
    }
}

void D3DApp::InitializeWorld(D3D12_GPU_DESCRIPTOR_HANDLE tectonics,D3D12_GPU_DESCRIPTOR_HANDLE planet,
    D3D12_GPU_DESCRIPTOR_HANDLE clouds,D3D12_GPU_DESCRIPTOR_HANDLE materials) {
    // The same world probe supplies observer lighting in hidden captures.
    mWorldTectonics=tectonics; mWorldPlanet=planet; mWorldClouds=clouds; mWorldMaterials=materials;
    D3D12_COMPUTE_PIPELINE_STATE_DESC desc = {};
    auto shader=LoadShader(L"WalkGround.cso");
    desc.pRootSignature=mComputeRootSignature.Get(); desc.CS=CD3DX12_SHADER_BYTECODE(shader.Get());
    Check(md3dDevice->CreateComputePipelineState(&desc,IID_PPV_ARGS(&mWalkGroundPSO)),"Walking ground PSO failed.");
    mWalkPoints=CreateBuffer(md3dDevice.Get(),256,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
    constexpr UINT bytes=WalkTerrain::Count*sizeof(float);
    mWalkGround=CreateBuffer(md3dDevice.Get(),bytes,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mWalkReadback=CreateBuffer(md3dDevice.Get(),bytes,D3D12_HEAP_TYPE_READBACK,D3D12_RESOURCE_STATE_COPY_DEST);

    CD3DX12_DESCRIPTOR_RANGE tectonicRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,5,18), planetRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,29),
        cloudRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,4,24), materialRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,2,5);
    CD3DX12_ROOT_PARAMETER params[7];
    params[0].InitAsConstantBufferView(0); params[1].InitAsConstantBufferView(1); params[2].InitAsUnorderedAccessView(0);
    params[3].InitAsDescriptorTable(1,&tectonicRange); params[4].InitAsDescriptorTable(1,&planetRange);
    params[5].InitAsDescriptorTable(1,&cloudRange); params[6].InitAsDescriptorTable(1,&materialRange);
    const CD3DX12_STATIC_SAMPLER_DESC samplers[] = {
        CD3DX12_STATIC_SAMPLER_DESC(0,D3D12_FILTER_MIN_MAG_MIP_LINEAR,D3D12_TEXTURE_ADDRESS_MODE_CLAMP,D3D12_TEXTURE_ADDRESS_MODE_CLAMP,D3D12_TEXTURE_ADDRESS_MODE_CLAMP),
        CD3DX12_STATIC_SAMPLER_DESC(1,D3D12_FILTER_ANISOTROPIC), CD3DX12_STATIC_SAMPLER_DESC(2,D3D12_FILTER_MIN_MAG_MIP_LINEAR),
        CD3DX12_STATIC_SAMPLER_DESC(3,D3D12_FILTER_MIN_MAG_MIP_LINEAR,D3D12_TEXTURE_ADDRESS_MODE_WRAP,D3D12_TEXTURE_ADDRESS_MODE_CLAMP,D3D12_TEXTURE_ADDRESS_MODE_CLAMP),
        CD3DX12_STATIC_SAMPLER_DESC(4,D3D12_FILTER_MIN_MAG_MIP_LINEAR,D3D12_TEXTURE_ADDRESS_MODE_CLAMP,D3D12_TEXTURE_ADDRESS_MODE_CLAMP,D3D12_TEXTURE_ADDRESS_MODE_CLAMP) };
    mWorldSoundRoot=CreateRootSignature(md3dDevice.Get(),CD3DX12_ROOT_SIGNATURE_DESC(7,params,5,samplers));
    shader=LoadShader(L"WorldSound.cso"); desc.pRootSignature=mWorldSoundRoot.Get(); desc.CS=CD3DX12_SHADER_BYTECODE(shader.Get());
    Check(md3dDevice->CreateComputePipelineState(&desc,IID_PPV_ARGS(&mWorldSoundPSO)),"World sound PSO failed.");
    mWorldSound=CreateBuffer(md3dDevice.Get(),sizeof(mHabitat),D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mWorldReadback=CreateBuffer(md3dDevice.Get(),sizeof(mHabitat),D3D12_HEAP_TYPE_READBACK,D3D12_RESOURCE_STATE_COPY_DEST);
}

void D3DApp::QueueWalkGround() {
    const Vec3d up=Normalize(mWalkFoot);
    mWalkPatchCentre=up*PlanetRadius;
    Vec3d east=Cross(kNorth,up);
    mWalkPatchX=Normalize(Length(east)>1e-6?east:Cross(Vec3d{1,0,0},up));
    mWalkPatchY=Cross(up,mWalkPatchX);
    const Vec3d axes[]={mWalkPatchCentre,mWalkPatchX,mWalkPatchY};
    double* points=nullptr; CD3DX12_RANGE noRead(0,0);
    Check(mWalkPoints->Map(0,&noRead,reinterpret_cast<void**>(&points)),"Walking points map failed.");
    for (int i=0;i<3;++i) { points[4*i]=axes[i].x; points[4*i+1]=axes[i].y; points[4*i+2]=axes[i].z; points[4*i+3]=0; }
    mWalkPoints->Unmap(0,nullptr);
    ID3D12DescriptorHeap* heaps[]={mSrvHeap.Get()}; mCommandList->SetDescriptorHeaps(1,heaps);
    mCommandList->SetComputeRootSignature(mComputeRootSignature.Get()); mCommandList->SetPipelineState(mWalkGroundPSO.Get());
    mCommandList->SetComputeRootConstantBufferView(0,mWalkPoints->GetGPUVirtualAddress());
    mCommandList->SetComputeRootUnorderedAccessView(1,mWalkGround->GetGPUVirtualAddress());
    mCommandList->SetComputeRootDescriptorTable(2,mWorldTectonics);
    mCommandList->Dispatch((WalkTerrain::Count+63)/64,1,1);
    auto barrier=CD3DX12_RESOURCE_BARRIER::Transition(mWalkGround.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_COPY_SOURCE);
    mCommandList->ResourceBarrier(1,&barrier);
    mCommandList->CopyResource(mWalkReadback.Get(),mWalkGround.Get());
    barrier=CD3DX12_RESOURCE_BARRIER::Transition(mWalkGround.Get(),D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    mCommandList->ResourceBarrier(1,&barrier); mWalkProbePending=true;
}

void D3DApp::ReadWalkGround() {
    if (!mWalkProbePending) return;
    mWalkProbePending=false; mWalkPatchValid=true;
    float* heights=nullptr; CD3DX12_RANGE read(0,WalkTerrain::Count*sizeof(float)), noWrite(0,0);
    Check(mWalkReadback->Map(0,&read,reinterpret_cast<void**>(&heights)),"Walking ground read failed.");
    std::memcpy(mWalkTerrain.heights.data(),heights,read.End);
    mWalkReadback->Unmap(0,&noWrite);
    for (float h:mWalkTerrain.heights) if (!std::isfinite(h)) { mWalkPatchValid=false; break; }
}

void D3DApp::ToggleWalking() {
    if (!mWalkGroundPSO) return;
    if (mView==View::Walk) {
        SetView(mWalkReturnView);
        if (mView==View::Free) { mCamPos=mWalkReturnPos; mCamForward=mWalkReturnForward; mCamUp=mWalkReturnUp; }
        else UpdateShip(0);
        mWaveReset=true; mGroundHeight=0; mWorldValid=mWorldPending=false; mAudio.ResetWorld();
        return;
    }
    mWalkFoot=Normalize(mCamPos)*PlanetRadius;
    if (mView!=View::Free) {
        const Vec3d up=Normalize(mShipPos), right=Normalize(Cross(mShipUp,mShipForward));
        mWalkFoot=Normalize(up*PlanetRadius+right*8.0)*PlanetRadius;
    }
    // One query on disembarkation prevents a frame underground after a descent from orbit.
    Check(mCommandAllocator->Reset(),"Walking allocator reset failed.");
    Check(mCommandList->Reset(mCommandAllocator.Get(),nullptr),"Walking list reset failed.");
    QueueWalkGround();
    Check(mCommandList->Close(),"Walking ground list close failed.");
    ID3D12CommandList* lists[]={mCommandList.Get()}; mCommandQueue->ExecuteCommandLists(1,lists); WaitForPreviousFrame();
    ReadWalkGround();
    double h=0,sx=0,sy=0;
    if (!mWalkPatchValid || !mWalkTerrain.Sample(0,0,h,sx,sy) || h<0.15 || std::hypot(sx,sy)>Walker::MaxSlope) {
        mWalkNoticeUntil=mClock+5.0; mWalkPatchValid=false; return;
    }
    mWalkReturnView=mView; mWalkReturnPos=mCamPos; mWalkReturnForward=mCamForward; mWalkReturnUp=mCamUp;
    mShipVelocity=mShipRate={}; mThrottle=mPlume=0; for (double& jet:mJets) jet=0;
    mWalker={}; mWalker.elevation=h; mWalkVelocity={};
    mWalkFoot=Normalize(mWalkFoot)*(PlanetRadius+h);
    const Vec3d up=Normalize(mWalkFoot);
    Vec3d forward=mCamForward-up*Dot(mCamForward,up);
    if (Length(forward)<1e-6) forward=mWalkPatchY;
    mCamForward=Normalize(forward);
    SetView(View::Walk); mCamUp=up; mCamPos=mWalkFoot+up*Walker::Eye;
    mWalkPatchValid=true; mWalkJump=false; mWaveReset=true;
    mGroundHeight=h; mOceanElevation=float(h); mWorldPending=mWorldValid=false; mAudio.ResetWorld();
    mHistoryValid=mCloudHistoryValid=false; mPlanetPlantPlacement.Reset();
}

FootContact D3DApp::CurrentFootContact() const {
    FootContact contact;
    if (mWorldValid) {
        contact.shares={{mHabitat[3].x,mHabitat[3].y,mHabitat[3].z,mHabitat[3].w,mHabitat[4].x,mHabitat[4].y}};
        contact.wetness=mHabitat[4].z;
    }
    return contact;
}

void D3DApp::EmitFootstep(float strength) {
    mAudio.Footstep(CurrentFootContact(),strength);
}

void D3DApp::UpdateWalking(float dt) {
    const Vec3d up=Normalize(mWalkFoot);
    mCamForward=Normalize(Rotate(mCamForward,up,mRawDx*0.002));
    Vec3d right=Normalize(Cross(up,mCamForward));
    const double pitch=std::asin(std::min(std::max(Dot(mCamForward,up),-1.0),1.0));
    const double wanted=std::min(std::max(pitch-mRawDy*0.002,-1.45),1.45);
    mCamForward=Normalize(Rotate(mCamForward,right,pitch-wanted)); mRawDx=mRawDy=0;
    const bool focused=GetForegroundWindow()==mhMainWnd && mMouseHeld;
    auto held=[&](UINT key) { return focused && (GetAsyncKeyState(key)&0x8000)?1.0:0.0; };
    const double forward=held(mMoveKeys[0])+held(VK_UP)-held(mMoveKeys[1])-held(VK_DOWN);
    const double strafe=held(mMoveKeys[3])+held(VK_RIGHT)-held(mMoveKeys[2])-held(VK_LEFT);
    const Vec3d ahead=Normalize(mCamForward-up*Dot(mCamForward,up)), move=ahead*forward+right*strafe;
    if (mWalkPatchValid) {
        const Vec3d foot=up*PlanetRadius-mWalkPatchCentre;
        mWalker.x=Dot(foot,mWalkPatchX); mWalker.y=Dot(foot,mWalkPatchY);
        mWalker.vx=Dot(mWalkVelocity,mWalkPatchX); mWalker.vy=Dot(mWalkVelocity,mWalkPatchY);
        mWalker.Advance(dt,{Dot(move,mWalkPatchX),Dot(move,mWalkPatchY),held(VK_SHIFT)>0,held(VK_CONTROL)>0,mWalkJump&&focused},mWalkTerrain);
        const Vec3d next=Normalize(mWalkPatchCentre+mWalkPatchX*mWalker.x+mWalkPatchY*mWalker.y);
        mWalkFoot=next*(PlanetRadius+mWalker.elevation);
        mWalkVelocity=mWalkPatchX*mWalker.vx+mWalkPatchY*mWalker.vy;
        mWalkVelocity=mWalkVelocity-next*Dot(mWalkVelocity,next);
        const Vec3d axis=Cross(up,next); const double sine=Length(axis);
        if (sine>1e-12) mCamForward=Normalize(Rotate(mCamForward,axis*(1.0/sine),std::asin(std::min(sine,1.0))));
        const float strength=held(VK_CONTROL)>0?0.5f:held(VK_SHIFT)>0?1.3f:0.85f;
        for (unsigned i=0;i<mWalker.steps;++i) EmitFootstep(strength);
        if (mWalker.landing>0.25f) EmitFootstep(mWalker.landing);
    }
    mWalkJump=false;
    const Vec3d vertical=Normalize(mWalkFoot);
    const double bob=mWalkBob&&mWalker.grounded?0.009*std::sin(mWalker.distance*2*XM_PI/0.78)*std::min(Length(mWalkVelocity)/1.5,1.0):0;
    mCamPos=mWalkFoot+vertical*(mWalker.eye+bob); mCamUp=vertical;
    double floor=mWalker.elevation,sx=0,sy=0;
    if (mWalkPatchValid) mWalkTerrain.Sample(mWalker.x,mWalker.y,floor,sx,sy);
    mGroundHeight=floor; mOceanElevation=float(floor);
    mSunDir=Rotate(mSunDir,kNorth,(held('P')-held('O'))*0.2*dt);
}

void D3DApp::QueueWorldSound() {
    if (!mWorldSoundPSO) return;
    if(mSettings.Automated()) {
        if(mDiagnosticView>0.5f || Length(mCamPos)-PlanetRadius-mGroundHeight>96) return;
        if(mWorldValid && mFrameNumber%6u!=0u && Length(mCamPos-mWorldProbePos)<0.01) return;
    } else if(mWorldValid && mClock<mWorldNextProbe) return;
    ID3D12DescriptorHeap* heaps[]={mSrvHeap.Get()}; mCommandList->SetDescriptorHeaps(1,heaps);
    mCommandList->SetComputeRootSignature(mWorldSoundRoot.Get()); mCommandList->SetPipelineState(mWorldSoundPSO.Get());
    mCommandList->SetComputeRootConstantBufferView(0,mConstantBuffer->GetGPUVirtualAddress());
    mCommandList->SetComputeRootConstantBufferView(1,mCloudConstantBuffer->GetGPUVirtualAddress());
    mCommandList->SetComputeRootUnorderedAccessView(2,mWorldSound->GetGPUVirtualAddress());
    mCommandList->SetComputeRootDescriptorTable(3,mWorldTectonics); mCommandList->SetComputeRootDescriptorTable(4,mWorldPlanet);
    mCommandList->SetComputeRootDescriptorTable(5,mWorldClouds); mCommandList->SetComputeRootDescriptorTable(6,mWorldMaterials);
    mCommandList->Dispatch(1,1,1);
    auto barrier=CD3DX12_RESOURCE_BARRIER::Transition(mWorldSound.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_COPY_SOURCE);
    mCommandList->ResourceBarrier(1,&barrier); mCommandList->CopyResource(mWorldReadback.Get(),mWorldSound.Get());
    barrier=CD3DX12_RESOURCE_BARRIER::Transition(mWorldSound.Get(),D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    mCommandList->ResourceBarrier(1,&barrier); mWorldPending=true; mWorldProbePos=mCamPos;
    mWorldNextProbe=mClock+(mView==View::Walk?0.0:0.1); // resolve small surface patches at walking speed
}

void D3DApp::ReadWorldSound() {
    if (!mWorldPending) return;
    mWorldPending=false; mWorldValid=false;
    XMFLOAT4* values=nullptr; CD3DX12_RANGE read(0,sizeof(mHabitat)), noWrite(0,0);
    Check(mWorldReadback->Map(0,&read,reinterpret_cast<void**>(&values)),"World habitat read failed.");
    std::memcpy(mHabitat,values,sizeof(mHabitat)); mWorldReadback->Unmap(0,&noWrite);
    for (const auto& v:mHabitat) for (float f:{v.x,v.y,v.z,v.w}) if (!std::isfinite(f)) return;
    mWorldValid=Length(mCamPos-mWorldProbePos)<250;
}

void D3DApp::ToggleAudio() {
    mAudioMuted=!mAudioMuted;
    mAudio.SetMix(mAudioMuted?0:mSettings.audioMaster,mSettings.audioFootsteps,mSettings.audioAmbience,mSettings.audioShip);
}

void D3DApp::UpdateWorldSound(float dt) {
    if (mSettings.Automated()) return;
    const bool focused=GetForegroundWindow()==mhMainWnd;
    const Vec3d up=Normalize(mCamPos);
    Vec3d horizontal=mCamForward-up*Dot(mCamForward,up);
    if (Length(horizontal)<1e-6) horizontal=Cross(up,Vec3d{0,0,1});
    if (Length(horizontal)<1e-6) horizontal=Cross(up,Vec3d{1,0,0});
    const Vec3d ahead=Normalize(horizontal), right=Normalize(Cross(up,ahead));
    WorldSound sound;
    sound.position[0]=mCamPos.x; sound.position[1]=mCamPos.y; sound.position[2]=mCamPos.z;
    sound.right[0]=float(right.x); sound.right[1]=float(right.y); sound.right[2]=float(right.z);
    sound.forward[0]=float(ahead.x); sound.forward[1]=float(ahead.y); sound.forward[2]=float(ahead.z);
    sound.cockpit=mView==View::Cockpit||mView==View::Bare?1.0f:0.0f;
    if (mWorldValid && focused) {
        const float altitude=float(std::max(Length(mCamPos)-PlanetRadius,0.0)), ground=mHabitat[1].w;
        const float clearance=std::max(altitude-std::max(ground,0.0f),0.0f), nearGround=std::exp(-clearance/120.0f);
        const float air=std::exp(-altitude/8000.0f), cover=mHabitat[1].x, temperature=mHabitat[1].z;
        const float day=Smooth(-0.08f,0.18f,float(Dot(up,mSunDir)));
        const double direction[]={up.x,up.y,up.z}; float climate[Climate::Channels]={}; Climate::At(mClimateCpu,direction,climate);
        const float wind=std::hypot(climate[Climate::WindEast],climate[Climate::WindNorth]);
        const float shore=(1-Smooth(2,40,std::max(ground,0.0f)))*std::max(mHabitat[2].w,ground<=0?1.0f:0.0f);
        sound.presence=air;
        sound.wind=std::min((wind*(1-cover*0.55f)+shore*mOceanSpeed*0.4f)/18.0f,1.0f);
        sound.leaves=cover*nearGround*Smooth(0,10,wind);
        const float airTemperature=climate[Climate::Temperature]-6.5f*altitude/1000.0f;
        sound.rain=mHabitat[2].x*Smooth(-2,1,airTemperature);
        sound.surf=shore*nearGround*std::min(0.4f+mOceanSpeed/20,1.0f);
        const float life=nearGround*Smooth(-2,10,temperature)*(1-Smooth(0.25f,0.9f,sound.rain));
        sound.birds=day*life*std::min(cover+0.25f*mHabitat[0].x,1.0f);
        sound.insects=(1-day)*life*Smooth(8,22,temperature)*mHabitat[1].y*std::max(cover,mHabitat[0].x);
        sound.frogs=(1-day)*life*Smooth(0.65f,0.95f,mHabitat[1].y)*cover;
    }
    mAudio.UpdateWorld(sound,dt);
}
