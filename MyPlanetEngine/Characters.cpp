// Characters.cpp - ozz-animation runtime evaluation + DX12 compute skinning and Forward HDR rendering.
#include "Characters.h"
#include "City.h"
#include "GpuHelpers.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <unordered_map>

#include "ozz/animation/runtime/animation.h"
#include "ozz/animation/runtime/blending_job.h"
#include "ozz/animation/runtime/ik_aim_job.h"
#include "ozz/animation/runtime/ik_two_bone_job.h"
#include "ozz/animation/runtime/local_to_model_job.h"
#include "ozz/animation/runtime/sampling_job.h"
#include "ozz/animation/runtime/skeleton.h"
#include "ozz/base/containers/vector.h"
#include "ozz/base/io/archive.h"
#include "ozz/base/io/stream.h"
#include "ozz/base/maths/simd_math.h"
#include "ozz/base/maths/simd_quaternion.h"
#include "ozz/base/maths/soa_transform.h"

using namespace DirectX;
using Microsoft::WRL::ComPtr;

namespace {
struct Reader {
    std::ifstream file;
    explicit Reader(const std::wstring& path) : file(path, std::ios::binary) {
        if (!file) throw std::runtime_error("Character bank file missing.");
    }
    void bytes(void* p, size_t n) {
        if (n && !file.read(static_cast<char*>(p), n))
            throw std::runtime_error("Character bank file truncated.");
    }
    template <class T> T read() { T v = {}; bytes(&v, sizeof(v)); return v; }
    void magic(const char* expected) {
        char m[8]; bytes(m, 8);
        if (memcmp(m, expected, 8) != 0) throw std::runtime_error("Unsupported character bank format.");
    }
    void end() { if (file.peek() != EOF) throw std::runtime_error("Unexpected character bank trailing data."); }
};

std::string WideToUtf8(const std::wstring& w) {
    if (w.empty()) return {};
    const int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), int(w.size()), nullptr, 0, nullptr, nullptr);
    std::string s(size_t(n), '\0');
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), int(w.size()), &s[0], n, nullptr, nullptr);
    return s;
}

template <class T>
std::unique_ptr<T> LoadOzz(const std::wstring& path) {
    const std::string u8 = WideToUtf8(path);
    ozz::io::File file(u8.c_str(), "rb");
    if (!file.opened()) throw std::runtime_error("Missing ozz file: " + u8);
    ozz::io::IArchive archive(&file);
    if (!archive.TestTag<T>()) throw std::runtime_error("Invalid ozz archive tag: " + u8);
    auto obj = std::make_unique<T>();
    archive >> *obj;
    return obj;
}

inline ozz::math::Float4x4 LoadColumnMajor(const float m[16]) {
    ozz::math::Float4x4 out;
    out.cols[0] = ozz::math::simd_float4::LoadPtrU(m + 0);
    out.cols[1] = ozz::math::simd_float4::LoadPtrU(m + 4);
    out.cols[2] = ozz::math::simd_float4::LoadPtrU(m + 8);
    out.cols[3] = ozz::math::simd_float4::LoadPtrU(m + 12);
    return out;
}

inline void StoreColumnMajor(const ozz::math::Float4x4& in, float out[16]) {
    ozz::math::StorePtrU(in.cols[0], out + 0);
    ozz::math::StorePtrU(in.cols[1], out + 4);
    ozz::math::StorePtrU(in.cols[2], out + 8);
    ozz::math::StorePtrU(in.cols[3], out + 12);
}

inline double ClampD(double v, double lo, double hi) { return std::min(std::max(v, lo), hi); }
inline float ClampF(float v, float lo, float hi) { return std::min(std::max(v, lo), hi); }

inline Vec3d CityBendDouble(double x, double y, double z) {
    const double R = Characters::PlanetRadiusM;
    const double u = (x * x + y * y) / (R * R);
    return { x * (1.0 + z / R - 0.5 * u), y * (1.0 + z / R - 0.5 * u), z - 0.5 * u * (R + z) };
}

void MultiplySoaQuaternion(ozz::vector<ozz::math::SoaTransform>& locals, int joint,
                           const ozz::math::SimdQuaternion& corr) {
    if (joint < 0) return;
    ozz::math::SoaQuaternion& r = locals[size_t(joint / 4)].rotation;
    const int lane = joint & 3;
    float qx[4], qy[4], qz[4], qw[4];
    ozz::math::StorePtrU(r.x, qx);
    ozz::math::StorePtrU(r.y, qy);
    ozz::math::StorePtrU(r.z, qz);
    ozz::math::StorePtrU(r.w, qw);
    ozz::math::SimdQuaternion cur;
    cur.xyzw = ozz::math::simd_float4::Load(qx[lane], qy[lane], qz[lane], qw[lane]);
    const ozz::math::SimdQuaternion next = cur * corr;
    float out[4];
    ozz::math::StorePtrU(next.xyzw, out);
    qx[lane] = out[0]; qy[lane] = out[1]; qz[lane] = out[2]; qw[lane] = out[3];
    r.x = ozz::math::simd_float4::LoadPtrU(qx);
    r.y = ozz::math::simd_float4::LoadPtrU(qy);
    r.z = ozz::math::simd_float4::LoadPtrU(qz);
    r.w = ozz::math::simd_float4::LoadPtrU(qw);
}

void AddSoaTranslation(ozz::vector<ozz::math::SoaTransform>& locals, int joint, float dx, float dy, float dz) {
    if (joint < 0) return;
    ozz::math::SoaFloat3& t = locals[size_t(joint / 4)].translation;
    const int lane = joint & 3;
    float tx[4], ty[4], tz[4];
    ozz::math::StorePtrU(t.x, tx);
    ozz::math::StorePtrU(t.y, ty);
    ozz::math::StorePtrU(t.z, tz);
    tx[lane] += dx;
    ty[lane] += dy;
    tz[lane] += dz;
    t.x = ozz::math::simd_float4::LoadPtrU(tx);
    t.y = ozz::math::simd_float4::LoadPtrU(ty);
    t.z = ozz::math::simd_float4::LoadPtrU(tz);
}
} // namespace

struct Characters::Impl {
    std::vector<std::unique_ptr<ozz::animation::SamplingJob::Context>> contexts;
    std::vector<std::unique_ptr<ozz::animation::SamplingJob::Context>> idleContexts;
    ozz::vector<ozz::math::SoaTransform> locals;
    ozz::vector<ozz::math::SoaTransform> localsA;
    ozz::vector<ozz::math::SoaTransform> localsB;
    ozz::vector<ozz::math::Float4x4> models;
};

Characters::Characters() : mImpl(std::make_unique<Impl>()) {}
Characters::~Characters() = default;

XMMATRIX Characters::Shadow() const {
    return mFramePtr ? XMMatrixTranspose(XMLoadFloat4x4(&mFramePtr->shadow)) : XMMatrixIdentity();
}

void Characters::Initialize(ID3D12Device* device, ID3D12GraphicsCommandList* cmd, ID3D12DescriptorHeap* heap,
                            UINT baseDescriptor, const std::wstring& folder, DXGI_FORMAT hdrFormat,
                            DXGI_FORMAT sunFormat, DXGI_FORMAT velocityFormat) {
    const UINT stride = device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
    auto cpuAt = [&](UINT offset) {
        auto h = heap->GetCPUDescriptorHandleForHeapStart();
        h.ptr += SIZE_T(baseDescriptor + offset) * stride;
        return h;
    };
    auto gpuAt = [&](UINT offset) {
        auto h = heap->GetGPUDescriptorHandleForHeapStart();
        h.ptr += UINT64(baseDescriptor + offset) * stride;
        return h;
    };
    mShadowSrv = gpuAt(0);
    mTextureTable = gpuAt(1);

    // Always allocate and clear the shadow map and fallback texture so SRV descriptors stay valid even without a bank.
    CD3DX12_HEAP_PROPERTIES gpuHeap(D3D12_HEAP_TYPE_DEFAULT);
    D3D12_DESCRIPTOR_HEAP_DESC dsvDesc = { D3D12_DESCRIPTOR_HEAP_TYPE_DSV, 1, D3D12_DESCRIPTOR_HEAP_FLAG_NONE, 0 };
    Check(device->CreateDescriptorHeap(&dsvDesc, IID_PPV_ARGS(&mDsvHeap)), "Character DSV heap failed.");
    CD3DX12_CLEAR_VALUE shadowClear(DXGI_FORMAT_D32_FLOAT, 1.0f, 0);
    auto shadowDesc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R32_TYPELESS, ShadowSize, ShadowSize, 1, 1, 1, 0,
                                                   D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL);
    Check(device->CreateCommittedResource(&gpuHeap, D3D12_HEAP_FLAG_NONE, &shadowDesc, D3D12_RESOURCE_STATE_DEPTH_WRITE,
                                          &shadowClear, IID_PPV_ARGS(&mShadow)), "Character shadow map failed.");
    D3D12_DEPTH_STENCIL_VIEW_DESC dsvView = {};
    dsvView.Format = DXGI_FORMAT_D32_FLOAT;
    dsvView.ViewDimension = D3D12_DSV_DIMENSION_TEXTURE2D;
    device->CreateDepthStencilView(mShadow.Get(), &dsvView, mDsvHeap->GetCPUDescriptorHandleForHeapStart());
    cmd->ClearDepthStencilView(mDsvHeap->GetCPUDescriptorHandleForHeapStart(), D3D12_CLEAR_FLAG_DEPTH, 1.0f, 0, 0, nullptr);
    auto shadowBarrier = CD3DX12_RESOURCE_BARRIER::Transition(mShadow.Get(), D3D12_RESOURCE_STATE_DEPTH_WRITE,
                                                              D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
    cmd->ResourceBarrier(1, &shadowBarrier);
    mShadowReadable = true;

    D3D12_SHADER_RESOURCE_VIEW_DESC shadowSrvDesc = {};
    shadowSrvDesc.Format = DXGI_FORMAT_R32_FLOAT;
    shadowSrvDesc.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
    shadowSrvDesc.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    shadowSrvDesc.Texture2D.MipLevels = 1;
    device->CreateShaderResourceView(mShadow.Get(), &shadowSrvDesc, cpuAt(0));

    // 1x1 white fallback texture for unused descriptor table slots.
    {
        auto fbDesc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R8G8B8A8_UNORM_SRGB, 1, 1, 1, 1);
        Check(device->CreateCommittedResource(&gpuHeap, D3D12_HEAP_FLAG_NONE, &fbDesc, D3D12_RESOURCE_STATE_COPY_DEST,
                                              nullptr, IID_PPV_ARGS(&mFallbackTex)), "Character fallback tex failed.");
        const uint8_t white[4] = { 255, 255, 255, 255 };
        auto stage = CreateBuffer(device, GetRequiredIntermediateSize(mFallbackTex.Get(), 0, 1),
                                  D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
        D3D12_SUBRESOURCE_DATA sub = { white, 4, 4 };
        UpdateSubresources(cmd, mFallbackTex.Get(), stage.Get(), 0, 0, 1, &sub);
        mUploads.push_back(stage);
        auto b = CD3DX12_RESOURCE_BARRIER::Transition(mFallbackTex.Get(), D3D12_RESOURCE_STATE_COPY_DEST,
                                                      D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
        cmd->ResourceBarrier(1, &b);
        D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
        srv.Format = DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;
        srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
        srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        srv.Texture2D.MipLevels = 1;
        for (UINT i = 0; i < MaxTextures; ++i)
            device->CreateShaderResourceView(mFallbackTex.Get(), &srv, cpuAt(1 + i));
    }

    if (folder.empty()) return;

    // 1. Read CHR1 binary bank.
    Reader chr(folder + L"\\characters.bin");
    chr.magic("CHR1\0\0\0\0");
    const uint32_t version = chr.read<uint32_t>();
    if (version != 1) throw std::runtime_error("Unsupported CHR1 version.");
    const uint32_t modelCount = chr.read<uint32_t>();
    const uint32_t matCount = chr.read<uint32_t>();
    const uint32_t texCount = chr.read<uint32_t>();
    const uint32_t totalVerts = chr.read<uint32_t>();
    const uint32_t totalIndices = chr.read<uint32_t>();
    mJointCount = chr.read<uint32_t>();
    if (!modelCount || modelCount > 64 || !matCount || matCount > 512 || texCount > MaxTextures
        || !totalVerts || !totalIndices || (totalIndices % 3) || !mJointCount || mJointCount > 256)
        throw std::runtime_error("CHR1 header budget invalid.");

    mJointNames.resize(mJointCount);
    for (uint32_t j = 0; j < mJointCount; ++j) {
        char buf[64]; chr.bytes(buf, 64);
        if (!memchr(buf, 0, 64)) throw std::runtime_error("CHR1 joint name not null-terminated.");
        mJointNames[j] = buf;
    }

    // Upload cooked textures.
    mTextures.resize(texCount);
    for (uint32_t t = 0; t < texCount; ++t) {
        const uint32_t w = chr.read<uint32_t>(), h = chr.read<uint32_t>();
        const uint32_t mips = chr.read<uint32_t>(), fmt = chr.read<uint32_t>(), byteSize = chr.read<uint32_t>();
        if (!w || !h || w != h || (w & (w - 1)) || mips < 1 || mips > 12 || fmt > 2 || !byteSize)
            throw std::runtime_error("CHR1 texture header invalid.");
        std::vector<uint8_t> data(byteSize);
        chr.bytes(data.data(), byteSize);

        const DXGI_FORMAT dxgiFmt = fmt == 0 ? DXGI_FORMAT_R8G8B8A8_UNORM_SRGB
                                  : fmt == 1 ? DXGI_FORMAT_BC5_UNORM
                                             : DXGI_FORMAT_R8G8B8A8_UNORM;
        auto desc = CD3DX12_RESOURCE_DESC::Tex2D(dxgiFmt, w, h, 1, UINT16(mips));
        Check(device->CreateCommittedResource(&gpuHeap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_COPY_DEST,
                                              nullptr, IID_PPV_ARGS(&mTextures[t])), "Character texture alloc failed.");
        auto stage = CreateBuffer(device, GetRequiredIntermediateSize(mTextures[t].Get(), 0, mips),
                                  D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
        std::vector<D3D12_SUBRESOURCE_DATA> subs;
        size_t offset = 0;
        for (uint32_t m = 0; m < mips; ++m) {
            const uint32_t s = std::max(w >> m, 1u);
            if (fmt == 1) {
                const size_t blocks = std::max((s + 3u) / 4u, 1u);
                const size_t rowPitch = blocks * 16;
                const size_t slicePitch = blocks * blocks * 16;
                subs.push_back({ data.data() + offset, LONG_PTR(rowPitch), LONG_PTR(slicePitch) });
                offset += slicePitch;
            } else {
                const size_t rowPitch = size_t(s) * 4;
                const size_t slicePitch = rowPitch * s;
                subs.push_back({ data.data() + offset, LONG_PTR(rowPitch), LONG_PTR(slicePitch) });
                offset += slicePitch;
            }
        }
        if (offset != byteSize) throw std::runtime_error("CHR1 texture byte count mismatch.");
        UpdateSubresources(cmd, mTextures[t].Get(), stage.Get(), 0, 0, mips, subs.data());
        mUploads.push_back(stage);
        auto b = CD3DX12_RESOURCE_BARRIER::Transition(mTextures[t].Get(), D3D12_RESOURCE_STATE_COPY_DEST,
                                                      D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
        cmd->ResourceBarrier(1, &b);

        D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
        srv.Format = dxgiFmt;
        srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
        srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        srv.Texture2D.MipLevels = mips;
        device->CreateShaderResourceView(mTextures[t].Get(), &srv, cpuAt(1 + t));
    }

    std::vector<MaterialGpu> materials(matCount);
    chr.bytes(materials.data(), materials.size() * sizeof(MaterialGpu));

    mModels.resize(modelCount);
    const wchar_t* clipNames[3] = { L"idle", L"walk", L"talk" };
    int maxOzzJoints = 0, maxOzzSoa = 0;
    for (uint32_t i = 0; i < modelCount; ++i) {
        Model& m = mModels[i];
        char nameBuf[64]; chr.bytes(nameBuf, 64);
        m.name = nameBuf;
        m.lo = chr.read<XMFLOAT3>();
        m.hi = chr.read<XMFLOAT3>();
        m.firstVertex = chr.read<uint32_t>();
        m.vertexCount = chr.read<uint32_t>();
        m.firstIndex = chr.read<uint32_t>();
        m.indexCount = chr.read<uint32_t>();
        m.invBind.resize(mJointCount);
        chr.bytes(m.invBind.data(), size_t(mJointCount) * sizeof(BoneMatrix));

        // Load per-archetype ozz skeleton and 3 clips, mapping canonical joints to ozz indices by name.
        m.skeleton = LoadOzz<ozz::animation::Skeleton>(folder + L"\\skel_" + std::to_wstring(i) + L".ozz");
        for (int c = 0; c < 3; ++c)
            m.clips[c] = LoadOzz<ozz::animation::Animation>(folder + L"\\anim_" + std::to_wstring(i) + L"_" + clipNames[c] + L".ozz");

        std::unordered_map<std::string, int> ozzMap;
        const auto names = m.skeleton->joint_names();
        for (size_t j = 0; j < names.size(); ++j) ozzMap[names[j]] = int(j);
        m.meshToOzz.resize(mJointCount);
        for (uint32_t j = 0; j < mJointCount; ++j) {
            auto it = ozzMap.find(mJointNames[j]);
            if (it == ozzMap.end())
                throw std::runtime_error("Canonical joint missing in ozz skeleton: " + mJointNames[j]);
            m.meshToOzz[j] = it->second;
        }
        auto findOzz = [&](const char* name) {
            auto it = ozzMap.find(name);
            return it != ozzMap.end() ? it->second : -1;
        };
        m.ik.root   = findOzz("Root");
        m.ik.pelvis = findOzz("pelvis");
        m.ik.neck   = findOzz("neck_01");
        m.ik.head   = findOzz("head");
        m.ik.thighL = findOzz("thigh_l");
        m.ik.calfL  = findOzz("calf_l");
        m.ik.footL  = findOzz("foot_l");
        m.ik.thighR  = findOzz("thigh_r");
        m.ik.calfR   = findOzz("calf_r");
        m.ik.footR   = findOzz("foot_r");
        m.ik.eyelidL = findOzz("eyelid_upper_l");
        m.ik.eyelidR = findOzz("eyelid_upper_r");

        maxOzzJoints = std::max(maxOzzJoints, m.skeleton->num_joints());
        maxOzzSoa = std::max(maxOzzSoa, m.skeleton->num_soa_joints());
    }

    mImpl->locals.resize(size_t(maxOzzSoa));
    mImpl->localsA.resize(size_t(maxOzzSoa));
    mImpl->localsB.resize(size_t(maxOzzSoa));
    mImpl->models.resize(size_t(maxOzzJoints));

    std::vector<RestVertex> restVerts(totalVerts);
    std::vector<uint32_t> indices(totalIndices);
    chr.bytes(restVerts.data(), restVerts.size() * sizeof(RestVertex));
    chr.bytes(indices.data(), indices.size() * sizeof(uint32_t));
    chr.end();

    // Convert global vertex indices to model-local (0..vertexCount-1) so DrawIndexedInstanced BaseVertexLocation is exact.
    for (const auto& m : mModels) {
        for (uint32_t k = 0; k < m.indexCount; ++k) {
            uint32_t& idx = indices[m.firstIndex + k];
            if (idx < m.firstVertex || idx >= m.firstVertex + m.vertexCount)
                throw std::runtime_error("CHR1 index out of model vertex range.");
            idx -= m.firstVertex;
        }
    }

    // 2. Read CHRPLC1 spaceport placements (v1 legacy default stride, v2 per-archetype measured MoCap strides).
    Reader plc(folder + L"\\placements.bin");
    plc.magic("CHRPLC1\0");
    const uint32_t plcVer = plc.read<uint32_t>();
    if (plcVer != 1 && plcVer != 2) throw std::runtime_error("Unsupported CHRPLC1 version.");
    mAnchorLat = plc.read<double>();
    mAnchorLon = plc.read<double>();
    mStrideMeters = std::max(plc.read<float>(), 0.25f);
    const uint32_t actorCount = plc.read<uint32_t>();
    if (!actorCount || actorCount > 128) throw std::runtime_error("CHRPLC1 actor count invalid.");

    for (uint32_t i = 0; i < modelCount; ++i)
        mModels[i].strideMeters = mStrideMeters;
    if (plcVer == 2) {
        const uint32_t strideCount = plc.read<uint32_t>();
        if (strideCount != modelCount) throw std::runtime_error("CHRPLC1 stride table count mismatch.");
        for (uint32_t i = 0; i < strideCount; ++i)
            mModels[i].strideMeters = std::max(plc.read<float>(), 0.35f);
    }

    mActors.resize(actorCount);
    mImpl->contexts.resize(actorCount);
    mImpl->idleContexts.resize(actorCount);
    mTotalSkinnedVerts = 0;
    mTotalBones = 0;
    for (uint32_t i = 0; i < actorCount; ++i) {
        Actor& a = mActors[i];
        a.model = plc.read<uint32_t>();
        a.clip = plc.read<uint32_t>();
        a.speed = plc.read<float>();
        a.phase = plc.read<float>();
        a.tint = plc.read<XMFLOAT4>();
        const uint32_t wpCount = plc.read<uint32_t>();
        a.yaw = plc.read<float>();
        if (a.model >= modelCount || a.clip >= 3 || wpCount == 0 || wpCount > 256)
            throw std::runtime_error("CHRPLC1 actor record invalid.");
        a.waypoints.resize(wpCount);
        plc.bytes(a.waypoints.data(), size_t(wpCount) * sizeof(XMFLOAT3));
        a.pathLength = 0.0;
        const double idleDur = std::max<double>(mModels[a.model].clips[0]->duration(), 1e-4);
        a.idleTime = std::fmod(std::max(0.0, double(a.phase)) * 3.17, idleDur);
        if (wpCount >= 2) {
            for (uint32_t w = 0; w < wpCount; ++w) {
                const auto& p0 = a.waypoints[w];
                const auto& p1 = a.waypoints[(w + 1) % wpCount];
                a.pathLength += std::hypot(double(p1.x) - p0.x, double(p1.y) - p0.y);
            }
            a.pathDist = std::fmod(std::max(0.0, double(a.phase)) * a.pathLength, std::max(a.pathLength, 1e-4));
            const double effStride = double(mModels[a.model].strideMeters) * std::max(double(a.tint.w), 0.5);
            a.walkCycle = std::fmod(a.pathDist / effStride, 1.0);
            a.walkWeight = 1.0f;
            a.curSpeed = a.speed;
        } else {
            a.walkWeight = 0.0f;
            a.curSpeed = 0.0f;
        }
        a.clipTime = double(a.phase) * double(mModels[a.model].clips[a.clip]->duration());
        a.dstVertexOffset = mTotalSkinnedVerts;
        a.boneBaseOffset = mTotalBones;
        mTotalSkinnedVerts += mModels[a.model].vertexCount;
        mTotalBones += mJointCount;
        a.prevBones.resize(mJointCount);
        a.blinkTimer = 1.4f + std::fmod(float(i) * 1.37f + a.phase * 4.2f, 3.8f);
        a.blinkPhase = -1.0f;
        mImpl->contexts[i] = std::make_unique<ozz::animation::SamplingJob::Context>(mModels[a.model].skeleton->num_joints());
        mImpl->idleContexts[i] = std::make_unique<ozz::animation::SamplingJob::Context>(mModels[a.model].skeleton->num_joints());
    }
    plc.end();

    // Auto-pair nearby stationary/talking actors (<= 3.6 m apart) for natural eye-contact Aim IK.
    for (uint32_t i = 0; i < actorCount; ++i) {
        if (mActors[i].waypoints.size() != 1) continue;
        double bestD = 3.6;
        int bestJ = -1;
        for (uint32_t j = 0; j < actorCount; ++j) {
            if (i == j || mActors[j].waypoints.size() != 1) continue;
            const double d = std::hypot(double(mActors[j].waypoints[0].x) - mActors[i].waypoints[0].x,
                                        double(mActors[j].waypoints[0].y) - mActors[i].waypoints[0].y);
            if (d < bestD) { bestD = d; bestJ = int(j); }
        }
        mActors[i].partnerIndex = bestJ;
    }

    // 3. Upload static GPU buffers and allocate per-frame dynamic buffers.
    auto uploadBuf = [&](const void* data, size_t bytes, D3D12_RESOURCE_STATES finalState) {
        auto buf = CreateBuffer(device, bytes, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COPY_DEST);
        auto stage = CreateBuffer(device, bytes, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
        void* ptr = nullptr; CD3DX12_RANGE none(0, 0);
        Check(stage->Map(0, &none, &ptr), "Character upload map failed.");
        memcpy(ptr, data, bytes);
        stage->Unmap(0, nullptr);
        cmd->CopyBufferRegion(buf.Get(), 0, stage.Get(), 0, bytes);
        auto b = CD3DX12_RESOURCE_BARRIER::Transition(buf.Get(), D3D12_RESOURCE_STATE_COPY_DEST, finalState);
        cmd->ResourceBarrier(1, &b);
        mUploads.push_back(stage);
        return buf;
    };

    mRestVertices = uploadBuf(restVerts.data(), restVerts.size() * sizeof(RestVertex), D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
    mIndices = uploadBuf(indices.data(), indices.size() * sizeof(uint32_t), D3D12_RESOURCE_STATE_INDEX_BUFFER);
    mMaterials = uploadBuf(materials.data(), materials.size() * sizeof(MaterialGpu), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
    mIndexView = { mIndices->GetGPUVirtualAddress(), UINT(indices.size() * sizeof(uint32_t)), DXGI_FORMAT_R32_UINT };

    const size_t skinnedStride = 80; // CharSkinnedVertex = 5 * float4
    mSkinnedVertices = CreateBuffer(device, size_t(mTotalSkinnedVerts) * skinnedStride, D3D12_HEAP_TYPE_DEFAULT,
                                    D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mSkinnedReadable = false;

    const size_t boneBytes = std::max<size_t>(size_t(mTotalBones) * sizeof(BoneMatrix), 256);
    mBonesCurr = CreateBuffer(device, boneBytes, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
    mBonesPrev = CreateBuffer(device, boneBytes, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
    mInstances = CreateBuffer(device, std::max<size_t>(actorCount * sizeof(InstanceGpu), 256),
                              D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
    mConstants = CreateBuffer(device, 256, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
    CD3DX12_RANGE noRead(0, 0);
    Check(mBonesCurr->Map(0, &noRead, reinterpret_cast<void**>(&mBonesCurrPtr)), "BonesCurr map failed.");
    Check(mBonesPrev->Map(0, &noRead, reinterpret_cast<void**>(&mBonesPrevPtr)), "BonesPrev map failed.");
    Check(mInstances->Map(0, &noRead, reinterpret_cast<void**>(&mInstancePtr)), "CharInstances map failed.");
    Check(mConstants->Map(0, &noRead, reinterpret_cast<void**>(&mFramePtr)), "CharConstants map failed.");
    *mFramePtr = {};

    // 4. Root signatures and PSOs.
    {
        CD3DX12_ROOT_PARAMETER p[6];
        p[0].InitAsConstants(4, 0);
        p[1].InitAsShaderResourceView(0);
        p[2].InitAsShaderResourceView(1);
        p[3].InitAsShaderResourceView(2);
        p[4].InitAsShaderResourceView(3);
        p[5].InitAsUnorderedAccessView(0);
        mSkinRoot = CreateRootSignature(device, CD3DX12_ROOT_SIGNATURE_DESC(6, p));
        auto cs = LoadShader(L"CharacterSkin.cso");
        D3D12_COMPUTE_PIPELINE_STATE_DESC desc = {};
        desc.pRootSignature = mSkinRoot.Get();
        desc.CS = CD3DX12_SHADER_BYTECODE(cs.Get());
        Check(device->CreateComputePipelineState(&desc, IID_PPV_ARGS(&mSkinPso)), "Character skin PSO failed.");
    }
    {
        CD3DX12_DESCRIPTOR_RANGE luts(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 3, 1);
        CD3DX12_DESCRIPTOR_RANGE planet(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 29);
        CD3DX12_DESCRIPTOR_RANGE charShad(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 33);
        CD3DX12_DESCRIPTOR_RANGE cityShad(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 34);
        CD3DX12_DESCRIPTOR_RANGE shipShad(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 35);
        CD3DX12_DESCRIPTOR_RANGE texArray(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, MaxTextures, 0, 1);

        CD3DX12_ROOT_PARAMETER p[12];
        p[0].InitAsConstantBufferView(0);
        p[1].InitAsConstantBufferView(2);
        p[2].InitAsShaderResourceView(30);
        p[3].InitAsShaderResourceView(31);
        p[4].InitAsShaderResourceView(32);
        p[5].InitAsDescriptorTable(1, &luts, D3D12_SHADER_VISIBILITY_PIXEL);
        p[6].InitAsDescriptorTable(1, &planet, D3D12_SHADER_VISIBILITY_PIXEL);
        p[7].InitAsDescriptorTable(1, &charShad, D3D12_SHADER_VISIBILITY_PIXEL);
        p[8].InitAsDescriptorTable(1, &cityShad, D3D12_SHADER_VISIBILITY_PIXEL);
        p[9].InitAsDescriptorTable(1, &shipShad, D3D12_SHADER_VISIBILITY_PIXEL);
        p[10].InitAsDescriptorTable(1, &texArray, D3D12_SHADER_VISIBILITY_PIXEL);
        p[11].InitAsConstants(4, 3, 0, D3D12_SHADER_VISIBILITY_VERTEX);

        CD3DX12_STATIC_SAMPLER_DESC samplers[3] = {
            CD3DX12_STATIC_SAMPLER_DESC(0, D3D12_FILTER_MIN_MAG_MIP_LINEAR, D3D12_TEXTURE_ADDRESS_MODE_CLAMP,
                                        D3D12_TEXTURE_ADDRESS_MODE_CLAMP, D3D12_TEXTURE_ADDRESS_MODE_CLAMP),
            CD3DX12_STATIC_SAMPLER_DESC(4, D3D12_FILTER_COMPARISON_MIN_MAG_LINEAR_MIP_POINT,
                                        D3D12_TEXTURE_ADDRESS_MODE_BORDER, D3D12_TEXTURE_ADDRESS_MODE_BORDER,
                                        D3D12_TEXTURE_ADDRESS_MODE_BORDER, 0, 1, D3D12_COMPARISON_FUNC_LESS_EQUAL,
                                        D3D12_STATIC_BORDER_COLOR_OPAQUE_WHITE),
            CD3DX12_STATIC_SAMPLER_DESC(5, D3D12_FILTER_ANISOTROPIC)
        };
        mDrawRoot = CreateRootSignature(device, CD3DX12_ROOT_SIGNATURE_DESC(12, p, 3, samplers));

        auto vs = LoadShader(L"CharacterVertex.cso");
        auto ps = LoadShader(L"CharacterPixel.cso");
        auto sv = LoadShader(L"CharacterShadow.cso");

        D3D12_GRAPHICS_PIPELINE_STATE_DESC pso = {};
        pso.pRootSignature = mDrawRoot.Get();
        pso.VS = CD3DX12_SHADER_BYTECODE(vs.Get());
        pso.PS = CD3DX12_SHADER_BYTECODE(ps.Get());
        pso.RasterizerState = CD3DX12_RASTERIZER_DESC(D3D12_DEFAULT);
        pso.RasterizerState.CullMode = D3D12_CULL_MODE_NONE;
        pso.BlendState = CD3DX12_BLEND_DESC(D3D12_DEFAULT);
        pso.DepthStencilState = CD3DX12_DEPTH_STENCIL_DESC(D3D12_DEFAULT);
        pso.DepthStencilState.DepthFunc = D3D12_COMPARISON_FUNC_GREATER; // reversed Z
        pso.SampleMask = UINT_MAX;
        pso.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
        pso.NumRenderTargets = 3;
        pso.RTVFormats[0] = hdrFormat;
        pso.RTVFormats[1] = sunFormat;
        pso.RTVFormats[2] = velocityFormat;
        pso.DSVFormat = DXGI_FORMAT_D32_FLOAT;
        pso.SampleDesc.Count = 1;
        Check(device->CreateGraphicsPipelineState(&pso, IID_PPV_ARGS(&mDrawPso)), "Character draw PSO failed.");

        pso.VS = CD3DX12_SHADER_BYTECODE(sv.Get());
        pso.PS = {};
        pso.NumRenderTargets = 0;
        pso.RTVFormats[0] = pso.RTVFormats[1] = pso.RTVFormats[2] = DXGI_FORMAT_UNKNOWN;
        pso.DepthStencilState.DepthFunc = D3D12_COMPARISON_FUNC_LESS;
        pso.RasterizerState.DepthBias = 80;
        pso.RasterizerState.SlopeScaledDepthBias = 1.5f;
        Check(device->CreateGraphicsPipelineState(&pso, IID_PPV_ARGS(&mShadowPso)), "Character shadow PSO failed.");
    }

    mReady = true;
}

void Characters::Update(double dt, bool historyValid, const Vec3d& camPos, const Vec3d& faceX, const Vec3d& faceY,
                        const Vec3d& faceZ, FXMMATRIX viewProj, const XMFLOAT3& sunFace,
                        UINT screenWidth, UINT screenHeight, const City& city) {
    if (!mReady) return;
    dt = std::min(std::max(dt, 0.0), 0.1);

    const double lat = mAnchorLat * XM_PI / 180.0, lon = mAnchorLon * XM_PI / 180.0;
    const Vec3d up = { std::cos(lat) * std::cos(lon), std::sin(lat), std::cos(lat) * std::sin(lon) };
    const Vec3d east = { -std::sin(lon), 0.0, std::cos(lon) };
    const Vec3d north = { -std::sin(lat) * std::cos(lon), std::cos(lat), -std::sin(lat) * std::sin(lon) };
    const Vec3d anchorOrigin = up * PlanetRadiusM;

    auto toFace = [&](const Vec3d& v) {
        return XMVectorSet(float(Dot(v, faceX)), float(Dot(v, faceY)), float(Dot(v, faceZ)), 0.0f);
    };

    // Quick visibility check against the spaceport cluster.
    double minDist2 = 1e30;
    XMFLOAT3 clusterSum = { 0, 0, 0 };
    UINT nearCount = 0;

    for (size_t i = 0; i < mActors.size(); ++i) {
        Actor& a = mActors[i];
        const Model& m = mModels[a.model];
        const ozz::animation::Animation& anim = *m.clips[a.clip];
        const ozz::animation::Animation& idleAnim = *m.clips[0];
        const double duration = std::max<double>(anim.duration(), 1e-4);
        const double idleDur = std::max<double>(idleAnim.duration(), 1e-4);
        const size_t soaCount = size_t(m.skeleton->num_soa_joints());
        const bool isWalker = (a.waypoints.size() >= 2 && a.speed > 1e-3f && a.pathLength > 1e-3);

        double cx = a.waypoints[0].x, cy = a.waypoints[0].y, cz = a.waypoints[0].z;
        float walkEase = 0.0f;
        if (isWalker) {
            if (a.hasPrev) {
                if (a.pauseTimer > 0.0f) {
                    a.pauseTimer = std::max(0.0f, a.pauseTimer - float(dt));
                    a.walkWeight = std::max(0.0f, a.walkWeight - float(dt) * 1.65f);
                } else {
                    a.walkWeight = std::min(1.0f, a.walkWeight + float(dt) * 1.50f);
                }
            }
            walkEase = a.walkWeight * a.walkWeight * (3.0f - 2.0f * a.walkWeight);
            a.curSpeed = a.speed * walkEase;
            const double stepM = double(a.curSpeed) * dt;
            a.pathDist = std::fmod(a.pathDist + stepM, a.pathLength);
            // Lock walk cycle increment strictly to world step / (modelStride * actorScale) for 0% foot sliding.
            const double effStride = double(m.strideMeters) * std::max(double(a.tint.w), 0.5);
            a.walkCycle = std::fmod(a.walkCycle + stepM / effStride, 1.0);
            a.idleTime = std::fmod(a.idleTime + dt, idleDur);

            double rem = a.pathDist;
            int curWp = 0;
            for (size_t w = 0; w < a.waypoints.size(); ++w) {
                const auto& p0 = a.waypoints[w];
                const auto& p1 = a.waypoints[(w + 1) % a.waypoints.size()];
                const double dx = double(p1.x) - p0.x, dy = double(p1.y) - p0.y, dz = double(p1.z) - p0.z;
                const double seg = std::hypot(dx, dy);
                if (rem <= seg || w + 1 == a.waypoints.size()) {
                    curWp = int(w);
                    const double t = seg > 1e-6 ? ClampD(rem / seg, 0.0, 1.0) : 0.0;
                    cx = p0.x + dx * t;
                    cy = p0.y + dy * t;
                    cz = p0.z + dz * t;
                    const double targetYaw = std::atan2(dy, dx);
                    double diff = targetYaw - double(a.yaw);
                    while (diff > XM_PI) diff -= 2.0 * XM_PI;
                    while (diff < -XM_PI) diff += 2.0 * XM_PI;
                    if (!a.hasPrev) a.yaw = float(targetYaw);
                    else if (walkEase > 0.05f) a.yaw = float(double(a.yaw) + diff * (1.0 - std::exp(-dt * 7.5 * double(walkEase))));
                    break;
                }
                rem -= seg;
            }
            if (!a.hasPrev) {
                a.lastWaypoint = curWp;
            } else if (curWp != a.lastWaypoint) {
                // Natural staggered 3-4.5 s concourse stops using ozz BlendingJob walk <-> idle cross-fade.
                if (a.pauseTimer <= 0.0f && a.walkWeight > 0.9f && ((curWp + int(i)) % 2 == 0))
                    a.pauseTimer = 3.2f + 0.45f * float(i % 4);
                a.lastWaypoint = curWp;
            }
        } else {
            a.clipTime = std::fmod(a.clipTime + dt, duration);
        }

        // Snap Z to exact cooked city walkable surface if present beneath the actor.
        if (city.Ready()) {
            double surfaceZ = cz;
            if (city.Surface(cx, cy, cz, surfaceZ) && std::abs(surfaceZ - cz) < 1.5)
                cz = surfaceZ;
        }

        // Evaluate ozz skeleton for this actor (with smooth BlendingJob walk <-> idle cross-fade for walkers).
        if (isWalker && walkEase < 0.999f) {
            if (walkEase <= 0.001f) {
                ozz::animation::SamplingJob sj;
                sj.animation = &idleAnim;
                sj.context = mImpl->idleContexts[i].get();
                sj.ratio = float(a.idleTime / idleDur);
                sj.output = ozz::span<ozz::math::SoaTransform>(mImpl->locals.data(), soaCount);
                sj.Run();
            } else {
                ozz::animation::SamplingJob sjIdle;
                sjIdle.animation = &idleAnim;
                sjIdle.context = mImpl->idleContexts[i].get();
                sjIdle.ratio = float(a.idleTime / idleDur);
                sjIdle.output = ozz::span<ozz::math::SoaTransform>(mImpl->localsA.data(), soaCount);
                sjIdle.Run();

                ozz::animation::SamplingJob sjWalk;
                sjWalk.animation = &anim;
                sjWalk.context = mImpl->contexts[i].get();
                sjWalk.ratio = float(a.walkCycle);
                sjWalk.output = ozz::span<ozz::math::SoaTransform>(mImpl->localsB.data(), soaCount);
                sjWalk.Run();

                ozz::animation::BlendingJob::Layer layers[2];
                layers[0].transform = ozz::span<const ozz::math::SoaTransform>(mImpl->localsA.data(), soaCount);
                layers[0].weight = 1.0f - walkEase;
                layers[1].transform = ozz::span<const ozz::math::SoaTransform>(mImpl->localsB.data(), soaCount);
                layers[1].weight = walkEase;

                ozz::animation::BlendingJob blend;
                blend.threshold = 0.1f;
                blend.layers = ozz::make_span(layers);
                blend.rest_pose = m.skeleton->joint_rest_poses();
                blend.output = ozz::span<ozz::math::SoaTransform>(mImpl->locals.data(), soaCount);
                blend.Run();
            }
        } else {
            ozz::animation::SamplingJob sampleJob;
            sampleJob.animation = &anim;
            sampleJob.context = mImpl->contexts[i].get();
            sampleJob.ratio = isWalker ? float(a.walkCycle) : float(a.clipTime / duration);
            sampleJob.output = ozz::span<ozz::math::SoaTransform>(mImpl->locals.data(), soaCount);
            sampleJob.Run();
        }

        auto runLtm = [&]() {
            ozz::animation::LocalToModelJob ltmJob;
            ltmJob.skeleton = m.skeleton.get();
            ltmJob.input = ozz::span<const ozz::math::SoaTransform>(mImpl->locals.data(), size_t(m.skeleton->num_soa_joints()));
            ltmJob.output = ozz::span<ozz::math::Float4x4>(mImpl->models.data(), size_t(m.skeleton->num_joints()));
            ltmJob.Run();
        };
        runLtm();

        const double cYaw = std::cos(double(a.yaw)), sYaw = std::sin(double(a.yaw));
        const Vec3d fwd = east * cYaw + north * sYaw;
        const Vec3d left = north * cYaw - east * sYaw;
        const float sc = a.tint.w;
        const double baseGroundZ = a.waypoints[0].z;

        // Milestone 2: Two-Bone Foot IK on sloped ground and raised concourse curbs.
        if (city.Ready() && m.ik.pelvis >= 0 && m.ik.thighL >= 0 && m.ik.calfL >= 0 && m.ik.footL >= 0
            && m.ik.thighR >= 0 && m.ik.calfR >= 0 && m.ik.footR >= 0) {
            auto footWorldDelta = [&](int footJoint, float& outLocalX, float& outLocalY, float& outLocalZ) -> float {
                float col3[4];
                ozz::math::StorePtrU(mImpl->models[size_t(footJoint)].cols[3], col3);
                outLocalX = col3[0]; outLocalY = col3[1]; outLocalZ = col3[2];
                // glTF +X = left, +Z = fwd -> city (cx, cy) offset.
                const double fx = cx + (-sYaw * double(col3[0]) + cYaw * double(col3[2])) * double(sc);
                const double fy = cy + ( cYaw * double(col3[0]) + sYaw * double(col3[2])) * double(sc);
                double surfZ = baseGroundZ;
                if (!city.Surface(fx, fy, baseGroundZ, surfZ)) surfZ = baseGroundZ;
                return float(ClampD((surfZ - cz) / std::max(double(sc), 0.1), -0.24, 0.24));
            };

            float lxL, lyL, lzL, lxR, lyR, lzR;
            const float dyL = footWorldDelta(m.ik.footL, lxL, lyL, lzL);
            const float dyR = footWorldDelta(m.ik.footR, lxR, lyR, lzR);
            const float targetPelvis = std::min(0.0f, std::min(dyL, dyR));
            a.smoothPelvisY = !a.hasPrev ? targetPelvis
                : a.smoothPelvisY + (targetPelvis - a.smoothPelvisY) * float(1.0 - std::exp(-dt * 12.0));

            if (std::fabs(a.smoothPelvisY) > 0.003f || std::fabs(dyL) > 0.003f || std::fabs(dyR) > 0.003f) {
                if (std::fabs(a.smoothPelvisY) > 0.001f && m.ik.root >= 0) {
                    // Transform model-space vertical pelvis shift (0, smoothPelvisY, 0) into Root's local frame.
                    float r0[4], r1[4], r2[4];
                    ozz::math::StorePtrU(mImpl->models[size_t(m.ik.root)].cols[0], r0);
                    ozz::math::StorePtrU(mImpl->models[size_t(m.ik.root)].cols[1], r1);
                    ozz::math::StorePtrU(mImpl->models[size_t(m.ik.root)].cols[2], r2);
                    AddSoaTranslation(mImpl->locals, m.ik.pelvis,
                                      r0[1] * a.smoothPelvisY, r1[1] * a.smoothPelvisY, r2[1] * a.smoothPelvisY);
                    runLtm();
                }

                auto solveLeg = [&](int thigh, int calf, int foot, float fx, float fy, float fz, float dy) {
                    // Only lock foot strongly while near stance phase (low ankle height); ease off during swing lift.
                    const float stanceWeight = ClampF(1.0f - (fy - 0.14f) / 0.14f, 0.0f, 1.0f);
                    if (stanceWeight < 0.02f || std::fabs(dy - a.smoothPelvisY) < 0.003f) return;
                    ozz::animation::IKTwoBoneJob ik;
                    ik.target = ozz::math::simd_float4::Load(fx, fy + dy, fz, 0.0f);
                    ik.mid_axis = ozz::math::simd_float4::Load(-1.0f, 0.0f, 0.0f, 0.0f);
                    ik.pole_vector = ozz::math::simd_float4::z_axis();
                    ik.soften = 0.97f;
                    ik.weight = stanceWeight;
                    ik.start_joint = &mImpl->models[size_t(thigh)];
                    ik.mid_joint = &mImpl->models[size_t(calf)];
                    ik.end_joint = &mImpl->models[size_t(foot)];
                    ozz::math::SimdQuaternion startCorr, midCorr;
                    ik.start_joint_correction = &startCorr;
                    ik.mid_joint_correction = &midCorr;
                    if (ik.Run()) {
                        MultiplySoaQuaternion(mImpl->locals, thigh, startCorr);
                        MultiplySoaQuaternion(mImpl->locals, calf, midCorr);
                    }
                };
                solveLeg(m.ik.thighL, m.ik.calfL, m.ik.footL, lxL, lyL, lzL, dyL);
                solveLeg(m.ik.thighR, m.ik.calfR, m.ik.footR, lxR, lyR, lzR, dyR);
                runLtm();
            }
        }

        // Map glTF (+X left, +Y up, +Z forward) into planet space at exact curved CityBend position.
        const Vec3d bent = CityBendDouble(cx, cy, cz);
        const Vec3d worldPos = anchorOrigin + east * bent.x + north * bent.y + up * bent.z;
        const Vec3d rel = worldPos - camPos;
        const double d2 = Dot(rel, rel);
        minDist2 = std::min(minDist2, d2);

        // Milestone 2: Natural Head & Neck Aim IK toward conversation partner or nearby observer
        // (active on stationary actors and smoothly enabled when walkers pause in idle).
        const float aimAllow = isWalker ? ClampF(1.0f - walkEase * 1.4f, 0.0f, 1.0f) : 1.0f;
        if (m.ik.neck >= 0 && m.ik.head >= 0 && (aimAllow > 0.01f || a.aimBlend > 0.01f)) {
            float headPos[4];
            ozz::math::StorePtrU(mImpl->models[size_t(m.ik.head)].cols[3], headPos);
            XMFLOAT3 targetLocal = { 0.0f, headPos[1], 3.0f };
            float desiredBlend = 0.0f;

            // 1. Prefer eye-contact with nearby player camera (0.8 - 7.5 m, inside front +/-62 deg cone).
            const Vec3d toCam = (camPos - worldPos);
            const double camDist = std::sqrt(Dot(toCam, toCam));
            if (aimAllow > 0.01f && camDist > 0.8 && camDist < 7.5) {
                const double localZ = Dot(toCam, fwd) / double(sc);
                const double localX = Dot(toCam, left) / double(sc);
                const double localY = Dot(toCam, up) / double(sc);
                const double horiz = std::hypot(localX, localZ);
                if (localZ > 0.25 && std::atan2(std::fabs(localX), localZ) < 1.08 && horiz > 0.5) {
                    const float clampedY = float(ClampD(localY, double(headPos[1]) - horiz * 0.40,
                                                        double(headPos[1]) + horiz * 0.40));
                    targetLocal = { float(localX), clampedY, float(localZ) };
                    desiredBlend = float(ClampD((7.5 - camDist) / 2.5, 0.0, 1.0)) * 0.85f * aimAllow;
                }
            }
            // 2. Otherwise keep conversational eye contact with paired partner.
            if (desiredBlend < 0.05f && a.partnerIndex >= 0 && aimAllow > 0.5f) {
                const auto& p = mActors[size_t(a.partnerIndex)];
                const double pdx = double(p.waypoints[0].x) - cx;
                const double pdy = double(p.waypoints[0].y) - cy;
                const double localZ = (pdx * cYaw + pdy * sYaw) / double(sc);
                const double localX = (pdy * cYaw - pdx * sYaw) / double(sc);
                const double partnerEye = double(mModels[p.model].hi.y) - 0.12;
                if (localZ > 0.2 && std::atan2(std::fabs(localX), localZ) < 1.15) {
                    targetLocal = { float(localX), float(partnerEye), float(localZ) };
                    desiredBlend = 0.80f;
                }
            }

            const float alpha = !a.hasPrev ? 1.0f : float(1.0 - std::exp(-dt * 4.5));
            a.aimBlend += (desiredBlend - a.aimBlend) * alpha;
            if (desiredBlend > 0.01f) {
                a.smoothAimLocal.x += (targetLocal.x - a.smoothAimLocal.x) * alpha;
                a.smoothAimLocal.y += (targetLocal.y - a.smoothAimLocal.y) * alpha;
                a.smoothAimLocal.z += (targetLocal.z - a.smoothAimLocal.z) * alpha;
            }
            if (a.aimBlend > 0.01f) {
                const ozz::math::SimdFloat4 aimTarget =
                    ozz::math::simd_float4::Load(a.smoothAimLocal.x, a.smoothAimLocal.y, a.smoothAimLocal.z, 0.0f);
                const int chain[2] = { m.ik.neck, m.ik.head };
                const float weights[2] = { 0.35f * a.aimBlend, 0.65f * a.aimBlend };
                for (int k = 0; k < 2; ++k) {
                    ozz::animation::IKAimJob aim;
                    aim.target = aimTarget;
                    aim.forward = ozz::math::simd_float4::z_axis();
                    aim.up = ozz::math::simd_float4::y_axis();
                    aim.pole_vector = ozz::math::simd_float4::y_axis();
                    aim.offset = (k == 1) ? ozz::math::simd_float4::Load(0.0f, 0.05f, 0.08f, 0.0f)
                                          : ozz::math::simd_float4::zero();
                    aim.weight = weights[k];
                    aim.joint = &mImpl->models[size_t(chain[k])];
                    ozz::math::SimdQuaternion corr;
                    aim.joint_correction = &corr;
                    if (aim.Run()) {
                        MultiplySoaQuaternion(mImpl->locals, chain[k], corr);
                        runLtm();
                    }
                }
            }
        }

        // Natural asynchronous human eye blink (fast 70ms close, 115ms open every 3.0-5.4s per actor).
        if (m.ik.eyelidL >= 0 && m.ik.eyelidR >= 0 && a.hasPrev) {
            if (a.blinkPhase >= 0.0f) {
                a.blinkPhase += float(dt);
                const float closeDur = 0.070f, holdDur = 0.025f, openDur = 0.115f;
                const float totalDur = closeDur + holdDur + openDur;
                float bAmt = 0.0f;
                if (a.blinkPhase < closeDur) {
                    const float u = a.blinkPhase / closeDur;
                    bAmt = u * u * (3.0f - 2.0f * u);
                } else if (a.blinkPhase < closeDur + holdDur) {
                    bAmt = 1.0f;
                } else if (a.blinkPhase < totalDur) {
                    const float u = 1.0f - (a.blinkPhase - closeDur - holdDur) / openDur;
                    bAmt = u * u * (3.0f - 2.0f * u);
                } else {
                    a.blinkPhase = -1.0f;
                    a.blinkTimer = 3.0f + std::fmod(float(a.idleTime * 1.7 + double(i) * 0.83), 2.6f);
                }
                if (bAmt > 0.005f) {
                    // Local +Y points out of eye and local +Z points up -> negative X rotation closes eyelid smoothly down.
                    const ozz::math::SimdQuaternion blinkQ = ozz::math::SimdQuaternion::FromAxisAngle(
                        ozz::math::simd_float4::x_axis(), ozz::math::simd_float4::Load1(-0.56f * bAmt));
                    MultiplySoaQuaternion(mImpl->locals, m.ik.eyelidL, blinkQ);
                    MultiplySoaQuaternion(mImpl->locals, m.ik.eyelidR, blinkQ);
                    runLtm();
                }
            } else {
                a.blinkTimer -= float(dt);
                if (a.blinkTimer <= 0.0f) a.blinkPhase = 0.0f;
            }
        }

        // Build current bone palette (modelMatrix * invBindMatrix) and upload curr + prev palettes.
        BoneMatrix* dstCurr = mBonesCurrPtr + a.boneBaseOffset;
        BoneMatrix* dstPrev = mBonesPrevPtr + a.boneBaseOffset;
        for (uint32_t j = 0; j < mJointCount; ++j) {
            const ozz::math::Float4x4 ibm = LoadColumnMajor(m.invBind[j].c);
            const ozz::math::Float4x4 skinMat = mImpl->models[size_t(m.meshToOzz[j])] * ibm;
            BoneMatrix bm;
            StoreColumnMajor(skinMat, bm.c);
            dstCurr[j] = bm;
            dstPrev[j] = (a.hasPrev && historyValid) ? a.prevBones[j] : bm;
            a.prevBones[j] = bm;
        }

        const XMMATRIX currModel(
            XMVectorScale(toFace(left), sc),
            XMVectorScale(toFace(up), sc),
            XMVectorScale(toFace(fwd), sc),
            XMVectorSetW(toFace(rel), 1.0f));
        const XMMATRIX currClip = currModel * viewProj;
        const XMMATRIX prevClip = (a.hasPrev && historyValid) ? XMLoadFloat4x4(&a.prevClipModel) : currClip;

        XMStoreFloat4x4(&mInstancePtr[i].currModel, XMMatrixTranspose(currModel));
        XMStoreFloat4x4(&mInstancePtr[i].prevClipModel, XMMatrixTranspose(prevClip));
        mInstancePtr[i].tint = a.tint;
        mInstancePtr[i].meta = { m.firstVertex, m.vertexCount, a.dstVertexOffset, a.boneBaseOffset };

        XMStoreFloat4x4(&a.prevClipModel, currClip);
        a.hasPrev = true;

        if (d2 < 80.0 * 80.0) {
            XMFLOAT3 relF;
            XMStoreFloat3(&relF, toFace(rel));
            clusterSum.x += relF.x;
            clusterSum.y += relF.y;
            clusterSum.z += relF.z;
            ++nearCount;
        }
    }

    mVisible = minDist2 < 600.0 * 600.0;
    mFramePtr->screen = { float(screenWidth), float(screenHeight), 1.0f / float(ShadowSize), float(mActors.size()) };

    if (mVisible && nearCount > 0) {
        // Centre the 48x48m local character shadow map on the nearby actor cluster (or camera if closer).
        XMFLOAT3 centre = { clusterSum.x / nearCount, clusterSum.y / nearCount, clusterSum.z / nearCount };
        const float distToCluster = std::sqrt(centre.x * centre.x + centre.y * centre.y + centre.z * centre.z);
        if (distToCluster > 18.0f) {
            // Pull shadow centre closer to camera when standing inside the spaceport so nearby actors stay sharp.
            const float pull = 18.0f / distToCluster;
            centre.x *= pull; centre.y *= pull; centre.z *= pull;
        }
        const XMVECTOR cVec = XMLoadFloat3(&centre);
        const XMVECTOR sunV = XMVector3Normalize(XMLoadFloat3(&sunFace));
        const XMVECTOR sUp = std::fabs(sunFace.y) < 0.95f ? XMVectorSet(0, 1, 0, 0) : XMVectorSet(1, 0, 0, 0);
        const XMMATRIX lightView = XMMatrixLookToLH(XMVectorAdd(cVec, XMVectorScale(sunV, 60.0f)),
                                                    XMVectorNegate(sunV), sUp);
        const XMMATRIX lightProj = XMMatrixOrthographicLH(ShadowSpanM, ShadowSpanM, 1.0f, 140.0f);
        XMMATRIX shadowMat = lightView * lightProj;
        XMFLOAT4X4 stable;
        XMStoreFloat4x4(&stable, shadowMat);
        stable._41 += (std::round(stable._41 * ShadowSize * 0.5f) - stable._41 * ShadowSize * 0.5f) * 2.0f / ShadowSize;
        stable._42 += (std::round(stable._42 * ShadowSize * 0.5f) - stable._42 * ShadowSize * 0.5f) * 2.0f / ShadowSize;
        XMStoreFloat4x4(&mFramePtr->shadow, XMMatrixTranspose(XMLoadFloat4x4(&stable)));
        mFramePtr->shadowBox = { centre.x, centre.y, centre.z, 1.0f };
    } else {
        XMStoreFloat4x4(&mFramePtr->shadow, XMMatrixIdentity());
        mFramePtr->shadowBox = { 0, 0, 0, 0.0f };
    }
}

void Characters::Skin(ID3D12GraphicsCommandList* cmd) {
    if (!mReady || !mVisible) return;
    if (mSkinnedReadable) {
        auto b = CD3DX12_RESOURCE_BARRIER::Transition(mSkinnedVertices.Get(),
            D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
        cmd->ResourceBarrier(1, &b);
        mSkinnedReadable = false;
    }
    cmd->SetComputeRootSignature(mSkinRoot.Get());
    cmd->SetPipelineState(mSkinPso.Get());
    cmd->SetComputeRootShaderResourceView(1, mRestVertices->GetGPUVirtualAddress());
    cmd->SetComputeRootShaderResourceView(2, mBonesCurr->GetGPUVirtualAddress());
    cmd->SetComputeRootShaderResourceView(3, mBonesPrev->GetGPUVirtualAddress());
    cmd->SetComputeRootShaderResourceView(4, mInstances->GetGPUVirtualAddress());
    cmd->SetComputeRootUnorderedAccessView(5, mSkinnedVertices->GetGPUVirtualAddress());
    for (uint32_t i = 0; i < uint32_t(mActors.size()); ++i) {
        const uint32_t vc = mModels[mActors[i].model].vertexCount;
        const uint32_t c[4] = { i, vc, 0u, 0u };
        cmd->SetComputeRoot32BitConstants(0, 4, c, 0);
        cmd->Dispatch((vc + 63u) / 64u, 1, 1);
    }
    auto b = CD3DX12_RESOURCE_BARRIER::Transition(mSkinnedVertices.Get(),
        D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
    cmd->ResourceBarrier(1, &b);
    mSkinnedReadable = true;
}

void Characters::DrawShadows(ID3D12GraphicsCommandList* cmd) {
    if (!mReady || !mVisible || mFramePtr->shadowBox.w < 0.5f) return;
    if (mShadowReadable) {
        auto b = CD3DX12_RESOURCE_BARRIER::Transition(mShadow.Get(),
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_DEPTH_WRITE);
        cmd->ResourceBarrier(1, &b);
        mShadowReadable = false;
    }
    auto dsv = mDsvHeap->GetCPUDescriptorHandleForHeapStart();
    cmd->OMSetRenderTargets(0, nullptr, FALSE, &dsv);
    cmd->ClearDepthStencilView(dsv, D3D12_CLEAR_FLAG_DEPTH, 1.0f, 0, 0, nullptr);
    CD3DX12_VIEWPORT vp(0.0f, 0.0f, float(ShadowSize), float(ShadowSize));
    CD3DX12_RECT rc(0, 0, ShadowSize, ShadowSize);
    cmd->RSSetViewports(1, &vp);
    cmd->RSSetScissorRects(1, &rc);
    cmd->SetGraphicsRootSignature(mDrawRoot.Get());
    cmd->SetPipelineState(mShadowPso.Get());
    cmd->SetGraphicsRootConstantBufferView(1, mConstants->GetGPUVirtualAddress());
    cmd->SetGraphicsRootShaderResourceView(2, mSkinnedVertices->GetGPUVirtualAddress());
    cmd->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    cmd->IASetIndexBuffer(&mIndexView);
    for (uint32_t i = 0; i < uint32_t(mActors.size()); ++i) {
        const auto& a = mActors[i];
        const auto& m = mModels[a.model];
        const uint32_t c[4] = { a.dstVertexOffset, i, 0u, 0u };
        cmd->SetGraphicsRoot32BitConstants(11, 4, c, 0);
        cmd->DrawIndexedInstanced(m.indexCount, 1, m.firstIndex, 0, 0);
    }
    auto b = CD3DX12_RESOURCE_BARRIER::Transition(mShadow.Get(),
        D3D12_RESOURCE_STATE_DEPTH_WRITE, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
    cmd->ResourceBarrier(1, &b);
    mShadowReadable = true;
}

void Characters::Draw(ID3D12GraphicsCommandList* cmd, D3D12_GPU_VIRTUAL_ADDRESS frameCbv,
                      D3D12_GPU_DESCRIPTOR_HANDLE luts, D3D12_GPU_DESCRIPTOR_HANDLE planetMap,
                      D3D12_GPU_DESCRIPTOR_HANDLE cityShadow, D3D12_GPU_DESCRIPTOR_HANDLE shipShadow) {
    if (!mReady || !mVisible) return;
    cmd->SetGraphicsRootSignature(mDrawRoot.Get());
    cmd->SetPipelineState(mDrawPso.Get());
    cmd->SetGraphicsRootConstantBufferView(0, frameCbv);
    cmd->SetGraphicsRootConstantBufferView(1, mConstants->GetGPUVirtualAddress());
    cmd->SetGraphicsRootShaderResourceView(2, mSkinnedVertices->GetGPUVirtualAddress());
    cmd->SetGraphicsRootShaderResourceView(3, mInstances->GetGPUVirtualAddress());
    cmd->SetGraphicsRootShaderResourceView(4, mMaterials->GetGPUVirtualAddress());
    cmd->SetGraphicsRootDescriptorTable(5, luts);
    cmd->SetGraphicsRootDescriptorTable(6, planetMap);
    cmd->SetGraphicsRootDescriptorTable(7, mShadowSrv);
    cmd->SetGraphicsRootDescriptorTable(8, cityShadow);
    cmd->SetGraphicsRootDescriptorTable(9, shipShadow);
    cmd->SetGraphicsRootDescriptorTable(10, mTextureTable);
    cmd->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    cmd->IASetIndexBuffer(&mIndexView);
    for (uint32_t i = 0; i < uint32_t(mActors.size()); ++i) {
        const auto& a = mActors[i];
        const auto& m = mModels[a.model];
        const uint32_t c[4] = { a.dstVertexOffset, i, 0u, 0u };
        cmd->SetGraphicsRoot32BitConstants(11, 4, c, 0);
        cmd->DrawIndexedInstanced(m.indexCount, 1, m.firstIndex, 0, 0);
    }
}
