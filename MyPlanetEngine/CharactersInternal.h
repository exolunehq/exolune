// CharactersInternal.h - Shared ozz-animation runtime storage and helpers for Characters modules.
#pragma once
#include "Characters.h"
#include <algorithm>
#include <memory>
#include <vector>

#include "ozz/animation/runtime/animation.h"
#include "ozz/animation/runtime/blending_job.h"
#include "ozz/animation/runtime/ik_aim_job.h"
#include "ozz/animation/runtime/ik_two_bone_job.h"
#include "ozz/animation/runtime/local_to_model_job.h"
#include "ozz/animation/runtime/sampling_job.h"
#include "ozz/animation/runtime/skeleton.h"
#include "ozz/base/containers/vector.h"
#include "ozz/base/maths/simd_math.h"
#include "ozz/base/maths/simd_quaternion.h"
#include "ozz/base/maths/soa_transform.h"

struct Characters::Impl {
    std::vector<std::unique_ptr<ozz::animation::SamplingJob::Context>> contexts;
    std::vector<std::unique_ptr<ozz::animation::SamplingJob::Context>> idleContexts;
    ozz::vector<ozz::math::SoaTransform> locals;
    ozz::vector<ozz::math::SoaTransform> localsA;
    ozz::vector<ozz::math::SoaTransform> localsB;
    ozz::vector<ozz::math::Float4x4> models;
};

namespace CharactersDetail {

inline double ClampD(double v, double lo, double hi) {
    return std::min(std::max(v, lo), hi);
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

inline void MultiplySoaQuaternion(ozz::vector<ozz::math::SoaTransform>& locals, int joint,
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

} // namespace CharactersDetail
