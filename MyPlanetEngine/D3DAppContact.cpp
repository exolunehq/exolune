// Flight contact uses the existing end-of-frame fence. No synchronous query, terrain modification or spatial patch.
#include "D3DApp.h"
#include "GpuHelpers.h"
#include <algorithm>
#include <cstring>

namespace {
    constexpr UINT ContactBytes=(FlightContact::MaxGroups+1)*sizeof(XMFLOAT4);
    FlightContact::Vec ContactVec(Vec3d p) { return {p.x,p.y,p.z}; }
}

D3DApp::FlightPose D3DApp::FlightPoseNow() const {
    return {mCamPos,mCamForward,mCamUp,mShipPos,mShipForward,mShipUp};
}
void D3DApp::SetFlightPose(const FlightPose& p) {
    mCamPos=p.camera;
    // A spherical free-camera contact constrains position, never the user's current look.
    if(mView!=View::Free) {mCamForward=p.forward;mCamUp=p.up;}
    mShipPos=p.ship; mShipForward=p.shipForward; mShipUp=p.shipUp;
}
void D3DApp::ResetFlightContact() {
    mFlightPending=mFlightQueued=false; mFlightRecovery=true; mFlightSlideNormal={};
}
void D3DApp::InitializeFlightContact() {
    if (mSettings.Automated()) return;
    const auto shader=LoadShader(L"FlightGround.cso");
    D3D12_COMPUTE_PIPELINE_STATE_DESC desc={}; desc.pRootSignature=mComputeRootSignature.Get();
    desc.CS=CD3DX12_SHADER_BYTECODE(shader.Get());
    Check(md3dDevice->CreateComputePipelineState(&desc,IID_PPV_ARGS(&mFlightContactPSO)),"Flight contact PSO failed.");
    for (unsigned i=0;i<2;++i) {
        mFlightPoints[i]=CreateBuffer(md3dDevice.Get(),256,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
        mFlightContacts[i]=CreateBuffer(md3dDevice.Get(),ContactBytes,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
        mFlightReadback[i]=CreateBuffer(md3dDevice.Get(),ContactBytes,D3D12_HEAP_TYPE_READBACK,D3D12_RESOURCE_STATE_COPY_DEST);
    }
}

void D3DApp::PrepareFlightContact(const FlightPose& before) {
    MoonFlightContact(before);
    if(NearMoon(mCamPos) || NearMoon(before.camera)) {mFlightPending=mFlightQueued=false;return;}
    if (!mFlightContactPSO || mView==View::Walk || !mCine.empty()) return;
    mFlightBefore=before; mFlightAfter=FlightPoseNow(); mFlightView=mView;
    const bool ship=mView!=View::Free;
    // The last contact's tangent carries sliding. Its influence ends after separation or a short tangential move;
    // the new corridor always tests the resulting movement against terrain again.
    const Vec3d at=mFlightSlideBody==1?before.ship:before.camera;
    if (Length(mFlightSlideNormal)>0.5 && Dot(at-mFlightSlideOrigin,mFlightSlideNormal)<0.02
        && Length(at-mFlightSlideOrigin)<1.0) {
        Vec3d travel=(mFlightSlideBody==1?mFlightAfter.ship:mFlightAfter.camera)-at;
        const double into=Dot(travel,mFlightSlideNormal);
        if (into<0) {
            const Vec3d correction=mFlightSlideNormal*(-into);
            mFlightAfter.camera=mFlightAfter.camera+correction;
            if (ship) mFlightAfter.ship=mFlightAfter.ship+correction;
        }
    } else mFlightSlideNormal={};
    if (mFlightRecovery) mFlightAfter=before; // initialize the current location before accepting its first movement
    const Vec3d starts[2]={before.camera,before.ship};
    const Vec3d ends[2]={mFlightAfter.camera,mFlightAfter.ship};
    // A fixed sphere about the ship origin contains its offset model sphere at every intermediate attitude.
    // An endpoint centre displacement alone would not bound a curved or returning rotational path.
    const double radii[2]={FlightContact::CameraRadius,double(Ship::Radius)+std::hypot(double(mShip.Profile().centreY),double(mShip.Profile().centreZ))};
    mFlightQueued=false;
    for (unsigned i=0;i<2;++i) {
        // The cockpit eye is inside the fixed hull envelope at every attitude. Chase and free eyes move outside it.
        const bool needed=i==0?(mView==View::Free || mView==View::Chase):ship;
        if (!needed) { mFlightActive[i]=false; continue; }
        // An accepted stationary sphere stays safe on the fixed terrain; looking around does not require new probes.
        // Chase still checks the eye if it moves around an otherwise stationary hull.
        const Vec3d travel=ends[i]-starts[i];
        if (!mFlightRecovery && Dot(travel,travel)==0.0) { mFlightActive[i]=false; continue; }
        mFlightSpans[i]=FlightContact::Clip(ContactVec(starts[i]),ContactVec(ends[i]),radii[i]);
        mFlightActive[i]=mFlightSpans[i].active;
        if (mFlightActive[i]) {
            mFlightProbes[i]=FlightContact::Corridor(mFlightSpans[i],radii[i]);
            mFlightQueued=true;
        }
    }
    if (!mFlightQueued) { SetFlightPose(mFlightAfter); mFlightRecovery=false; return; }
    SetFlightPose(before);
}

void D3DApp::QueueFlightContact() {
    if (!mFlightQueued) return;
    mFlightQueued=false;
    ID3D12DescriptorHeap* heaps[]={mSrvHeap.Get()}; mCommandList->SetDescriptorHeaps(1,heaps);
    mCommandList->SetComputeRootSignature(mComputeRootSignature.Get()); mCommandList->SetPipelineState(mFlightContactPSO.Get());
    mCommandList->SetComputeRootDescriptorTable(2,mWorldTectonics);
    for (unsigned i=0;i<2;++i) if (mFlightActive[i]) {
        void* upload=nullptr; CD3DX12_RANGE noRead(0,0);
        Check(mFlightPoints[i]->Map(0,&noRead,&upload),"Flight contact points map failed.");
        std::memcpy(upload,&mFlightProbes[i],sizeof(mFlightProbes[i])); mFlightPoints[i]->Unmap(0,nullptr);
        mCommandList->SetComputeRootConstantBufferView(0,mFlightPoints[i]->GetGPUVirtualAddress());
        mCommandList->SetComputeRootUnorderedAccessView(1,mFlightContacts[i]->GetGPUVirtualAddress());
        mCommandList->Dispatch(mFlightProbes[i].Groups(),1,1);
        auto barrier=CD3DX12_RESOURCE_BARRIER::Transition(mFlightContacts[i].Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_COPY_SOURCE);
        mCommandList->ResourceBarrier(1,&barrier); mCommandList->CopyResource(mFlightReadback[i].Get(),mFlightContacts[i].Get());
        barrier=CD3DX12_RESOURCE_BARRIER::Transition(mFlightContacts[i].Get(),D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
        mCommandList->ResourceBarrier(1,&barrier);
    }
    mFlightPending=true;
}

void D3DApp::ReadFlightContact() {
    if (!mFlightPending) return;
    mFlightPending=false;
    if (mView!=mFlightView || mView==View::Walk) return;
    double fraction=1.0,recovery=0.0,cameraGround=mGroundHeight;
    Vec3d normal={}; unsigned body=0; bool valid=true;
    for (unsigned i=0;i<2;++i) if (mFlightActive[i]) {
        const auto& span=mFlightSpans[i];
        if (span.sea<fraction) {
            fraction=span.sea; normal={span.seaNormal.x,span.seaNormal.y,span.seaNormal.z}; body=i;
        }
        XMFLOAT4* values=nullptr; CD3DX12_RANGE read(0,ContactBytes),noWrite(0,0);
        Check(mFlightReadback[i]->Map(0,&read,reinterpret_cast<void**>(&values)),"Flight contact read failed.");
        for (unsigned group=0;group<mFlightProbes[i].Groups();++group) {
            const XMFLOAT4 hit=values[group];
            if (!std::isfinite(hit.x) || hit.x<0) { valid=false; continue; }
            if (hit.x<=1 && span.Fraction(hit.x)<fraction) {
                fraction=span.Fraction(hit.x); const auto n=mFlightProbes[i].WorldNormal(hit.y,hit.z,hit.w);
                normal={n.x,n.y,n.z}; body=i;
            }
        }
        const XMFLOAT4 support=values[FlightContact::MaxGroups];
        valid=valid&&std::isfinite(support.x)&&std::isfinite(support.y)&&std::isfinite(support.z);
        recovery=std::max(recovery,double(support.x));
        if (i==0 && (mFlightRecovery || span.last==1)) cameraGround=mFlightRecovery?support.y:support.z;
        mFlightReadback[i]->Unmap(0,&noWrite);
    }
    if (!valid) { SetFlightPose(mFlightBefore); mFlightRecovery=true; return; }
    if (mFlightRecovery) {
        FlightPose pose=mFlightBefore;
        if (recovery>0) {
            const Vec3d lift=Normalize(pose.camera)*(recovery+0.01);
            pose.camera=pose.camera+lift;
            if (mView!=View::Free) pose.ship=pose.ship+lift;
        }
        SetFlightPose(pose); mFlightRecovery=false; mGroundHeight=std::max(cameraGround,0.0); return;
    }
    FlightPose accepted=mFlightAfter;
    if (fraction<1.0) {
        const Vec3d travel=(body==1?mFlightAfter.ship-mFlightBefore.ship:mFlightAfter.camera-mFlightBefore.camera);
        fraction=std::max(0.0,fraction-0.002/std::max(Length(travel),0.002));
        accepted.camera=mFlightBefore.camera+(mFlightAfter.camera-mFlightBefore.camera)*fraction;
        accepted.ship=mFlightBefore.ship+(mFlightAfter.ship-mFlightBefore.ship)*fraction;
        const double into=Dot(mShipVelocity,normal);
        if (into<0) mShipVelocity=mShipVelocity-normal*into;
        mFlightSlideNormal=normal; mFlightSlideOrigin=body==1?accepted.ship:accepted.camera; mFlightSlideBody=body;
    } else mGroundHeight=std::max(cameraGround,0.0);
    // Keep the eye attached to the cockpit when translation stops; the fixed hull envelope already bounds its arc.
    if (mView==View::Cockpit || mView==View::Bare)
        accepted.camera=accepted.ship+(mFlightAfter.camera-mFlightAfter.ship);
    SetFlightPose(accepted);
    if (mView==View::Chase) {
        mChaseOffset=mCamPos-mShipPos;
        mCamForward=Normalize(mShipPos+mShipForward*2.0-mCamPos);
    }
}
