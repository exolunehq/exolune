// Standalone CPU verification for the cooked CHR1/CHRPLC1 character bank and ozz-animation runtime.
#define NOMINMAX
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

#include "ozz/animation/runtime/animation.h"
#include "ozz/animation/runtime/blending_job.h"
#include "ozz/animation/runtime/local_to_model_job.h"
#include "ozz/animation/runtime/sampling_job.h"
#include "ozz/animation/runtime/skeleton.h"
#include "ozz/base/containers/vector.h"
#include "ozz/base/io/archive.h"
#include "ozz/base/io/stream.h"
#include "ozz/base/maths/simd_math.h"
#include "ozz/base/maths/soa_transform.h"

namespace {
struct Reader {
    std::ifstream file;
    explicit Reader(const std::string& path) : file(path, std::ios::binary) {
        if (!file) throw std::runtime_error("Missing file: " + path);
    }
    void bytes(void* p, size_t n) {
        if (n && !file.read(static_cast<char*>(p), n))
            throw std::runtime_error("Truncated file.");
    }
    template <class T> T read() { T v = {}; bytes(&v, sizeof(v)); return v; }
    void magic(const char* expected) {
        char m[8]; bytes(m, 8);
        if (memcmp(m, expected, 8) != 0) throw std::runtime_error("Bad magic.");
    }
    void end() { if (file.peek() != EOF) throw std::runtime_error("Unexpected trailing bytes."); }
};

template <class T>
std::unique_ptr<T> LoadOzz(const std::string& path) {
    ozz::io::File file(path.c_str(), "rb");
    if (!file.opened()) throw std::runtime_error("Missing ozz file: " + path);
    ozz::io::IArchive archive(&file);
    if (!archive.TestTag<T>()) throw std::runtime_error("Invalid ozz tag: " + path);
    auto obj = std::make_unique<T>();
    archive >> *obj;
    return obj;
}

struct BoneMatrix { float c[16]; };
struct RestVertex {
    float pos[3], normal[3], tangent[4], uv[2];
    uint16_t joints[4];
    float weights[4];
    uint32_t material, pad;
};
static_assert(sizeof(RestVertex) == 80, "RestVertex layout mismatch.");

struct MaterialGpu {
    float baseColor[4], pbr[4];
    int32_t textures[4];
    float extra[4];
};
static_assert(sizeof(MaterialGpu) == 64, "MaterialGpu layout mismatch.");

ozz::math::Float4x4 LoadColMajor(const float m[16]) {
    ozz::math::Float4x4 out;
    out.cols[0] = ozz::math::simd_float4::LoadPtrU(m + 0);
    out.cols[1] = ozz::math::simd_float4::LoadPtrU(m + 4);
    out.cols[2] = ozz::math::simd_float4::LoadPtrU(m + 8);
    out.cols[3] = ozz::math::simd_float4::LoadPtrU(m + 12);
    return out;
}

void StoreColMajor(const ozz::math::Float4x4& in, float out[16]) {
    ozz::math::StorePtrU(in.cols[0], out + 0);
    ozz::math::StorePtrU(in.cols[1], out + 4);
    ozz::math::StorePtrU(in.cols[2], out + 8);
    ozz::math::StorePtrU(in.cols[3], out + 12);
}

void TransformPoint(const float m[16], const float p[3], float out[3]) {
    out[0] = m[0] * p[0] + m[4] * p[1] + m[8]  * p[2] + m[12];
    out[1] = m[1] * p[0] + m[5] * p[1] + m[9]  * p[2] + m[13];
    out[2] = m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14];
}

float MaxIdentityError(const float m[16]) {
    static const float id[16] = { 1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1 };
    float err = 0.0f;
    for (int i = 0; i < 16; ++i) {
        if (!std::isfinite(m[i])) return 1e9f;
        err = std::max(err, std::abs(m[i] - id[i]));
    }
    return err;
}

float Det3x3(const float m[16]) {
    return m[0] * (m[5] * m[10] - m[9] * m[6])
         - m[4] * (m[1] * m[10] - m[9] * m[2])
         + m[8] * (m[1] * m[6]  - m[5] * m[2]);
}

void Require(bool cond, const std::string& msg) {
    if (!cond) throw std::runtime_error("CHECK FAILED: " + msg);
}
} // namespace

int main(int argc, char** argv) {
    try {
        if (argc < 2) {
            std::cerr << "Usage: character_checks.exe <bank_folder>\n";
            return 2;
        }
        const std::string folder = argv[1];

        // 1. Validate CHR1 binary bank.
        Reader chr(folder + "\\characters.bin");
        chr.magic("CHR1\0\0\0\0");
        const uint32_t version = chr.read<uint32_t>();
        Require(version == 1, "CHR1 version == 1");
        const uint32_t modelCount = chr.read<uint32_t>();
        const uint32_t matCount = chr.read<uint32_t>();
        const uint32_t texCount = chr.read<uint32_t>();
        const uint32_t totalVerts = chr.read<uint32_t>();
        const uint32_t totalIndices = chr.read<uint32_t>();
        const uint32_t jointCount = chr.read<uint32_t>();

        Require(modelCount > 0 && modelCount <= 64, "valid modelCount");
        Require(matCount > 0 && matCount <= 512, "valid matCount");
        Require(texCount <= 96, "texCount <= 96");
        Require(totalVerts > 0 && totalIndices > 0 && (totalIndices % 3) == 0, "valid geometry counts");
        Require(jointCount == 59 || jointCount == 57 || jointCount == 53, "canonical 53/57/59-bone game_engine skeleton");

        std::vector<std::string> jointNames(jointCount);
        for (uint32_t j = 0; j < jointCount; ++j) {
            char buf[64]; chr.bytes(buf, 64);
            Require(memchr(buf, 0, 64) != nullptr, "null-terminated joint name");
            jointNames[j] = buf;
        }

        for (uint32_t t = 0; t < texCount; ++t) {
            const uint32_t w = chr.read<uint32_t>(), h = chr.read<uint32_t>();
            const uint32_t mips = chr.read<uint32_t>(), fmt = chr.read<uint32_t>(), byteSize = chr.read<uint32_t>();
            Require(w > 0 && w == h && (w & (w - 1)) == 0, "square power-of-two texture");
            Require(mips >= 1 && mips <= 12 && fmt <= 2, "valid texture mips/format");
            size_t expected = 0;
            for (uint32_t m = 0; m < mips; ++m) {
                const uint32_t s = std::max(w >> m, 1u);
                if (fmt == 1) {
                    const size_t b = std::max((s + 3u) / 4u, 1u);
                    expected += b * b * 16;
                } else {
                    expected += size_t(s) * s * 4;
                }
            }
            Require(expected == byteSize, "exact texture mip byte size");
            std::vector<uint8_t> skip(byteSize);
            chr.bytes(skip.data(), byteSize);
        }

        std::vector<MaterialGpu> materials(matCount);
        chr.bytes(materials.data(), materials.size() * sizeof(MaterialGpu));
        for (uint32_t m = 0; m < matCount; ++m) {
            Require(materials[m].textures[0] < int32_t(texCount), "color tex index in range");
            Require(materials[m].textures[1] < int32_t(texCount), "normal tex index in range");
        }

        struct Model {
            std::string name;
            float lo[3], hi[3];
            uint32_t firstVertex, vertexCount, firstIndex, indexCount;
            std::vector<BoneMatrix> invBind;
        };
        std::vector<Model> models(modelCount);
        for (uint32_t i = 0; i < modelCount; ++i) {
            char nameBuf[64]; chr.bytes(nameBuf, 64);
            models[i].name = nameBuf;
            chr.bytes(models[i].lo, sizeof(models[i].lo));
            chr.bytes(models[i].hi, sizeof(models[i].hi));
            models[i].firstVertex = chr.read<uint32_t>();
            models[i].vertexCount = chr.read<uint32_t>();
            models[i].firstIndex = chr.read<uint32_t>();
            models[i].indexCount = chr.read<uint32_t>();
            models[i].invBind.resize(jointCount);
            chr.bytes(models[i].invBind.data(), size_t(jointCount) * sizeof(BoneMatrix));
            Require(std::abs(models[i].lo[1]) < 0.025f, "model grounded at Y=0: " + models[i].name);
            Require(models[i].hi[1] > 1.45f && models[i].hi[1] < 2.15f, "realistic human height: " + models[i].name);
        }

        std::vector<RestVertex> verts(totalVerts);
        std::vector<uint32_t> indices(totalIndices);
        chr.bytes(verts.data(), verts.size() * sizeof(RestVertex));
        chr.bytes(indices.data(), indices.size() * sizeof(uint32_t));
        chr.end();

        // Validate every rest vertex and index.
        for (size_t i = 0; i < verts.size(); ++i) {
            const auto& v = verts[i];
            for (int k = 0; k < 3; ++k) {
                Require(std::isfinite(v.pos[k]) && std::isfinite(v.normal[k]) && std::isfinite(v.tangent[k]), "finite vertex");
            }
            const float nLen = std::sqrt(v.normal[0]*v.normal[0] + v.normal[1]*v.normal[1] + v.normal[2]*v.normal[2]);
            const float tLen = std::sqrt(v.tangent[0]*v.tangent[0] + v.tangent[1]*v.tangent[1] + v.tangent[2]*v.tangent[2]);
            Require(std::abs(nLen - 1.0f) < 0.02f, "unit rest normal");
            Require(std::abs(tLen - 1.0f) < 0.02f, "unit rest tangent");
            Require(std::abs(v.tangent[3]) > 0.99f && std::abs(v.tangent[3]) < 1.01f, "valid tangent handedness");
            float wSum = 0.0f;
            for (int k = 0; k < 4; ++k) {
                Require(v.joints[k] < jointCount, "joint index < jointCount");
                Require(std::isfinite(v.weights[k]) && v.weights[k] >= -1e-5f, "non-negative weight");
                wSum += v.weights[k];
            }
            Require(std::abs(wSum - 1.0f) < 1e-3f, "normalized skinning weights");
            Require(v.material < matCount, "vertex material index in range");
        }
        for (const auto& m : models) {
            for (uint32_t k = 0; k < m.indexCount; ++k) {
                const uint32_t idx = indices[m.firstIndex + k];
                Require(idx >= m.firstVertex && idx < m.firstVertex + m.vertexCount, "index in model range");
            }
        }

        // 2. Validate ozz skeletons, bind-pose identity, animation sampling & loop continuity.
        const char* clipNames[3] = { "idle", "walk", "talk" };
        float worstRestErr = 0.0f;
        float worstLoopErr = 0.0f;
        for (uint32_t i = 0; i < modelCount; ++i) {
            auto skel = LoadOzz<ozz::animation::Skeleton>(folder + "\\skel_" + std::to_string(i) + ".ozz");
            std::unordered_map<std::string, int> ozzMap;
            const auto names = skel->joint_names();
            for (size_t j = 0; j < names.size(); ++j) ozzMap[names[j]] = int(j);
            std::vector<int> meshToOzz(jointCount);
            for (uint32_t j = 0; j < jointCount; ++j) {
                auto it = ozzMap.find(jointNames[j]);
                Require(it != ozzMap.end(), "joint in ozz skeleton: " + jointNames[j]);
                meshToOzz[j] = it->second;
            }

            ozz::vector<ozz::math::Float4x4> restModels(size_t(skel->num_joints()));
            ozz::animation::LocalToModelJob restJob;
            restJob.skeleton = skel.get();
            restJob.input = skel->joint_rest_poses();
            restJob.output = ozz::make_span(restModels);
            Require(restJob.Run(), "rest LocalToModelJob");

            for (uint32_t j = 0; j < jointCount; ++j) {
                const auto skin = restModels[size_t(meshToOzz[j])] * LoadColMajor(models[i].invBind[j].c);
                float out[16];
                StoreColMajor(skin, out);
                const float err = MaxIdentityError(out);
                worstRestErr = std::max(worstRestErr, err);
                Require(err < 5e-3f, "rest model * invBind == Identity for " + models[i].name + ":" + jointNames[j]
                    + " (err=" + std::to_string(err) + ")");
            }

            ozz::animation::SamplingJob::Context ctx(skel->num_joints());
            ozz::animation::SamplingJob::Context ctxIdle(skel->num_joints());
            ozz::vector<ozz::math::SoaTransform> locals(size_t(skel->num_soa_joints()));
            ozz::vector<ozz::math::SoaTransform> localsIdle(size_t(skel->num_soa_joints()));
            ozz::vector<ozz::math::SoaTransform> localsWalk(size_t(skel->num_soa_joints()));
            ozz::vector<ozz::math::Float4x4> animModels(size_t(skel->num_joints()));
            std::array<std::unique_ptr<ozz::animation::Animation>, 3> loadedClips;

            for (int c = 0; c < 3; ++c) {
                ctx.Invalidate();
                loadedClips[c] = LoadOzz<ozz::animation::Animation>(
                    folder + "\\anim_" + std::to_string(i) + "_" + clipNames[c] + ".ozz");
                auto& anim = loadedClips[c];
                Require(anim->duration() > 0.2f, "positive clip duration");
                std::vector<BoneMatrix> firstPose(jointCount), lastPose(jointCount);
                const float ratios[5] = { 0.0f, 0.25f, 0.5f, 0.75f, 1.0f };
                for (int r = 0; r < 5; ++r) {
                    ozz::animation::SamplingJob sj;
                    sj.animation = anim.get();
                    sj.context = &ctx;
                    sj.ratio = ratios[r];
                    sj.output = ozz::make_span(locals);
                    Require(sj.Run(), "SamplingJob");

                    ozz::animation::LocalToModelJob ltm;
                    ltm.skeleton = skel.get();
                    ltm.input = ozz::make_span(locals);
                    ltm.output = ozz::make_span(animModels);
                    Require(ltm.Run(), "LocalToModelJob");

                    std::vector<BoneMatrix> palette(jointCount);
                    for (uint32_t j = 0; j < jointCount; ++j) {
                        const auto sm = animModels[size_t(meshToOzz[j])] * LoadColMajor(models[i].invBind[j].c);
                        StoreColMajor(sm, palette[j].c);
                        for (int k = 0; k < 16; ++k) Require(std::isfinite(palette[j].c[k]), "finite skin matrix");
                        const float det = Det3x3(palette[j].c);
                        Require(det > 0.5f && det < 2.0f, "rigid skin matrix det near 1");
                    }
                    if (r == 0) firstPose = palette;
                    if (r == 4) lastPose = palette;

                    // Spot-check skinned bounds on model vertices at keyframe ratios.
                    float minY = 1e9f, maxY = -1e9f;
                    for (uint32_t v = 0; v < models[i].vertexCount; v += 7) {
                        const auto& rv = verts[models[i].firstVertex + v];
                        float sp[3] = { 0, 0, 0 };
                        for (int k = 0; k < 4; ++k) {
                            float tp[3];
                            TransformPoint(palette[rv.joints[k]].c, rv.pos, tp);
                            sp[0] += tp[0] * rv.weights[k];
                            sp[1] += tp[1] * rv.weights[k];
                            sp[2] += tp[2] * rv.weights[k];
                        }
                        Require(std::isfinite(sp[0]) && std::isfinite(sp[1]) && std::isfinite(sp[2]), "finite skinned pos");
                        minY = std::min(minY, sp[1]);
                        maxY = std::max(maxY, sp[1]);
                    }
                    Require(minY > -0.15f && minY < 0.25f, "animated character grounded minY (" + models[i].name + " " + clipNames[c] + ")");
                    Require(maxY > 1.35f && maxY < 2.25f, "animated character height maxY");
                }
                for (uint32_t j = 0; j < jointCount; ++j) {
                    for (int k = 0; k < 16; ++k) {
                        const float d = std::abs(firstPose[j].c[k] - lastPose[j].c[k]);
                        worstLoopErr = std::max(worstLoopErr, d);
                        Require(d < 0.05f, "seamless loop continuity " + models[i].name + " " + clipNames[c]);
                    }
                }
            }

            // Validate runtime ozz BlendingJob cross-fade (50% idle + 50% walk).
            {
                ctxIdle.Invalidate();
                ctx.Invalidate();
                ozz::animation::SamplingJob sIdle;
                sIdle.animation = loadedClips[0].get();
                sIdle.context = &ctxIdle;
                sIdle.ratio = 0.35f;
                sIdle.output = ozz::make_span(localsIdle);
                Require(sIdle.Run(), "BlendingJob idle sample");

                ozz::animation::SamplingJob sWalk;
                sWalk.animation = loadedClips[1].get();
                sWalk.context = &ctx;
                sWalk.ratio = 0.40f;
                sWalk.output = ozz::make_span(localsWalk);
                Require(sWalk.Run(), "BlendingJob walk sample");

                ozz::animation::BlendingJob::Layer layers[2];
                layers[0].transform = ozz::make_span(localsIdle);
                layers[0].weight = 0.5f;
                layers[1].transform = ozz::make_span(localsWalk);
                layers[1].weight = 0.5f;
                ozz::animation::BlendingJob blend;
                blend.threshold = 0.1f;
                blend.layers = ozz::make_span(layers);
                blend.rest_pose = skel->joint_rest_poses();
                blend.output = ozz::make_span(locals);
                Require(blend.Run(), "BlendingJob walk<->idle");

                ozz::animation::LocalToModelJob ltm;
                ltm.skeleton = skel.get();
                ltm.input = ozz::make_span(locals);
                ltm.output = ozz::make_span(animModels);
                Require(ltm.Run(), "BlendingJob LocalToModelJob");
                for (uint32_t j = 0; j < jointCount; ++j) {
                    float m[16];
                    StoreColMajor(animModels[size_t(meshToOzz[j])] * LoadColMajor(models[i].invBind[j].c), m);
                    for (int k = 0; k < 16; ++k) Require(std::isfinite(m[k]), "finite blended skin matrix");
                    const float det = Det3x3(m);
                    Require(det > 0.5f && det < 2.0f, "rigid blended skin matrix det near 1");
                }
            }
        }

        // 3. Validate CHRPLC1 placements (v1 default stride or v2 per-model MoCap stride table).
        Reader plc(folder + "\\placements.bin");
        plc.magic("CHRPLC1\0");
        const uint32_t plcVer = plc.read<uint32_t>();
        Require(plcVer == 1 || plcVer == 2, "CHRPLC1 version == 1 or 2");
        const double lat = plc.read<double>(), lon = plc.read<double>();
        const float stride = plc.read<float>();
        const uint32_t actorCount = plc.read<uint32_t>();
        Require(std::isfinite(lat) && std::isfinite(lon) && stride > 0.5f && stride < 2.5f, "valid anchor & stride");
        Require(actorCount == 12, "12 spaceport actors");
        if (plcVer == 2) {
            const uint32_t strideCount = plc.read<uint32_t>();
            Require(strideCount == modelCount, "CHRPLC1 v2 per-model stride count == modelCount");
            for (uint32_t s = 0; s < strideCount; ++s) {
                const float ms = plc.read<float>();
                Require(std::isfinite(ms) && ms > 0.5f && ms < 2.5f, "valid per-model MoCap stride");
            }
        }
        uint32_t walkers = 0;
        for (uint32_t a = 0; a < actorCount; ++a) {
            const uint32_t model = plc.read<uint32_t>(), clip = plc.read<uint32_t>();
            const float speed = plc.read<float>(), phase = plc.read<float>();
            float tint[4]; plc.bytes(tint, sizeof(tint));
            const uint32_t wpCount = plc.read<uint32_t>();
            const float yaw = plc.read<float>();
            Require(model < modelCount && clip < 3 && wpCount >= 1 && std::isfinite(yaw) && std::isfinite(phase), "valid actor header");
            Require(tint[3] > 0.8f && tint[3] < 1.2f, "realistic height scale");
            std::vector<float> wps(size_t(wpCount) * 3);
            plc.bytes(wps.data(), wps.size() * sizeof(float));
            for (float v : wps) Require(std::isfinite(v), "finite waypoint");
            if (wpCount >= 2 && speed > 0.0f) ++walkers;
        }
        plc.end();
        Require(walkers >= 4, "at least 4 patrolling walkers");

        std::cout << "PASS character_checks: models=" << modelCount << " verts=" << totalVerts
                  << " actors=" << actorCount << " walkers=" << walkers
                  << " worstRestErr=" << worstRestErr << " worstLoopErr=" << worstLoopErr << "\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << "\n";
        return 1;
    }
}
