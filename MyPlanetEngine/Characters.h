// Characters.h - rigged, textured, animated characters driven by ozz-animation and DX12 compute skinning.
// Loads a cooked CHR1 bank (tools/characters/cook.py), evaluates skeletal clips on CPU, runs GPU compute
// skinning once per frame, renders a local 0-35 m dynamic shadow map, and shades into Exolune's shared
// Forward HDR + sunPart + TAA velocity buffers.
#pragma once
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <d3d12.h>
#include <DirectXMath.h>
#include <wrl.h>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>
#include "FlightFrame.h"
#include "Gameplay.h"

class City;

namespace ozz {
namespace animation {
class Skeleton;
class Animation;
struct SamplingJob;
}
}

class Characters {
public:
    static constexpr UINT MaxTextures = 96;
    static constexpr UINT DescriptorCount = 1 + MaxTextures; // shadow SRV + 96 material texture SRVs
    static constexpr UINT ShadowSize = 2048;
    static constexpr float ShadowSpanM = 48.0f;
    static constexpr double PlanetRadiusM = 6378000.0;
    static constexpr int ClipCount = 6; // 0 idle, 1 walk, 2 talk, 3 sit_idle, 4 sit_talk, 5 interact

    struct SequenceFrame {
        Gameplay::SequencePhase phase = Gameplay::SequencePhase::Dormant;
        double clock = 0.0;
        bool shuttleValid = false;
        bool cockpitCamera = false;
        Vec3d pos = {}, left = {}, back = {}, up = {};
    };
    struct SequenceAnchor {
        bool valid = false;
        double x = 0.0, y = 0.0, z = 0.0, yaw = 0.0;
    };
    struct SequenceProgress {
        uint32_t done = 0, total = 0;
    };

    Characters();
    ~Characters();

    bool Ready() const { return mReady; }
    bool Visible() const { return mReady && mVisible; }
    UINT ActorCount() const { return UINT(mActors.size()); }
    bool HasSequence(Gameplay::SequenceId id) const;
    SequenceAnchor SequenceOrigin(Gameplay::SequenceId id) const;
    SequenceProgress SequenceState(Gameplay::SequenceId id) const;
    void ResetSequence(Gameplay::SequenceId id);
    DirectX::XMMATRIX Shadow() const;
    D3D12_GPU_DESCRIPTOR_HANDLE ShadowSrv() const { return mShadowSrv; }

    void Initialize(ID3D12Device* device, ID3D12GraphicsCommandList* cmd, ID3D12DescriptorHeap* heap, UINT baseDescriptor,
                    const std::wstring& folder, DXGI_FORMAT hdrFormat, DXGI_FORMAT sunFormat, DXGI_FORMAT velocityFormat);
    void ReleaseUploads() { mUploads.clear(); }

    void Update(double dt, bool historyValid, const Vec3d& camPos, const Vec3d& faceX, const Vec3d& faceY,
                const Vec3d& faceZ, DirectX::FXMMATRIX viewProj, const DirectX::XMFLOAT3& sunFace,
                UINT screenWidth, UINT screenHeight, const City& city, const SequenceFrame& sequence = {});
    void Skin(ID3D12GraphicsCommandList* cmd);
    void DrawShadows(ID3D12GraphicsCommandList* cmd);
    void Draw(ID3D12GraphicsCommandList* cmd, D3D12_GPU_VIRTUAL_ADDRESS frameCbv,
              D3D12_GPU_DESCRIPTOR_HANDLE luts, D3D12_GPU_DESCRIPTOR_HANDLE planetMap,
              D3D12_GPU_DESCRIPTOR_HANDLE cityShadow, D3D12_GPU_DESCRIPTOR_HANDLE shipShadow);

private:
    using Resource = Microsoft::WRL::ComPtr<ID3D12Resource>;

    struct BoneMatrix {
        float c[16]; // column-major matching ozz::math::Float4x4
    };
    struct RestVertex {
        float pos[3], normal[3], tangent[4], uv[2];
        uint16_t joints[4];
        float weights[4];
        uint32_t material, pad;
    };
    static_assert(sizeof(RestVertex) == 80, "RestVertex must match Characters.hlsli.");

    struct MaterialGpu {
        DirectX::XMFLOAT4 baseColor, pbr;
        DirectX::XMINT4 textures;
        DirectX::XMFLOAT4 extra;
    };
    struct InstanceGpu {
        DirectX::XMFLOAT4X4 currModel;
        DirectX::XMFLOAT4X4 prevClipModel;
        DirectX::XMFLOAT4 tint;
        DirectX::XMUINT4 meta; // restFirstVertex, vertexCount, dstVertexOffset, boneBaseOffset
    };
    struct FrameConstants {
        DirectX::XMFLOAT4X4 shadow;
        DirectX::XMFLOAT4 screen;    // w, h, 1/shadowSize, actorCount
        DirectX::XMFLOAT4 shadowBox; // xyz centre, w enabled
    };

    struct IkJoints {
        int root = -1, pelvis = -1, neck = -1, head = -1;
        int thighL = -1, calfL = -1, footL = -1;
        int thighR = -1, calfR = -1, footR = -1;
        int eyelidL = -1, eyelidR = -1;
    };

    struct Model {
        std::string name;
        DirectX::XMFLOAT3 lo = {}, hi = {};
        uint32_t firstVertex = 0, vertexCount = 0, firstIndex = 0, indexCount = 0;
        float strideMeters = 1.45f;
        std::vector<BoneMatrix> invBind;
        std::unique_ptr<ozz::animation::Skeleton> skeleton;
        std::array<std::unique_ptr<ozz::animation::Animation>, ClipCount> clips; // 0 idle, 1 walk, 2 talk, 3 sit_idle, 4 sit_talk, 5 interact
        std::vector<int> meshToOzz; // maps canonical joint index -> ozz skeleton joint index
        IkJoints ik;
    };

    struct Actor {
        uint32_t model = 0, clip = 0;
        float speed = 0.0f, phase = 0.0f, yaw = 0.0f;
        DirectX::XMFLOAT4 tint = { 1, 1, 1, 1 };
        std::vector<DirectX::XMFLOAT3> waypoints;
        double pathLength = 0.0, pathDist = 0.0, clipTime = 0.0;
        double walkCycle = 0.0, idleTime = 0.0;
        float walkWeight = 1.0f, curSpeed = 0.0f, pauseTimer = 0.0f;
        int lastWaypoint = -1;
        uint32_t dstVertexOffset = 0, boneBaseOffset = 0;
        int partnerIndex = -1;
        float smoothPelvisY = 0.0f;
        DirectX::XMFLOAT3 smoothAimLocal = { 0.0f, 1.58f, 3.0f };
        float aimBlend = 0.0f;
        float blinkTimer = 2.0f, blinkPhase = -1.0f;
        DirectX::XMFLOAT4X4 prevClipModel = {};
        bool hasPrev = false;
        bool isSequence = false, isPilot = false;
        Gameplay::SequenceId sequenceId = Gameplay::SequenceId::ShuttleBoarding;
        uint32_t waitClip = 0, seatClip = 3;
        float startDelay = 0.0f, seatYaw = -1.5707963f, sitBlend = 0.0f;
        double boardDist = 0.0;
        int boardPhase = 0; // 0=Wait, 1=Walk, 2=Turn, 3=Sit/Seated
        std::vector<BoneMatrix> prevBones;
    };

    void LoadSequences(const std::wstring& folder, uint32_t modelCount);
    void UpdateSequenceActor(size_t i, double dt, bool historyValid, const Vec3d& camPos,
                             const Vec3d& faceX, const Vec3d& faceY, const Vec3d& faceZ,
                             DirectX::FXMMATRIX viewProj, const SequenceFrame& seq,
                             double& minDist2, DirectX::XMFLOAT3& clusterSum, UINT& nearCount);

    struct Impl;
    std::unique_ptr<Impl> mImpl;

    double mAnchorLat = 0.0, mAnchorLon = 0.0;
    float mStrideMeters = 1.30f;
    uint32_t mJointCount = 0;
    uint32_t mTotalSkinnedVerts = 0;
    uint32_t mTotalBones = 0;
    bool mReady = false, mVisible = false, mShadowReadable = false, mSkinnedReadable = false;
    SequenceAnchor mBoardingOrigin;
    uint32_t mBoardingActorCount = 0;

    std::vector<std::string> mJointNames;
    std::vector<Model> mModels;
    std::vector<Actor> mActors;

    Resource mRestVertices, mIndices, mMaterials, mSkinnedVertices;
    Resource mBonesCurr, mBonesPrev, mInstances, mConstants, mShadow, mFallbackTex;
    std::vector<Resource> mTextures;
    std::vector<Resource> mUploads;

    BoneMatrix* mBonesCurrPtr = nullptr;
    BoneMatrix* mBonesPrevPtr = nullptr;
    InstanceGpu* mInstancePtr = nullptr;
    FrameConstants* mFramePtr = nullptr;

    D3D12_INDEX_BUFFER_VIEW mIndexView = {};
    D3D12_GPU_DESCRIPTOR_HANDLE mShadowSrv = {}, mTextureTable = {};
    Microsoft::WRL::ComPtr<ID3D12DescriptorHeap> mDsvHeap;
    Microsoft::WRL::ComPtr<ID3D12RootSignature> mSkinRoot, mDrawRoot;
    Microsoft::WRL::ComPtr<ID3D12PipelineState> mSkinPso, mShadowPso, mDrawPso;
};
