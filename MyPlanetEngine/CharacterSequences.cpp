// CharacterSequences.cpp - Choreographed scripted character sequences driven by Gameplay state.
#include "CharactersInternal.h"
#include <cmath>
#include <fstream>
#include <sstream>

using namespace DirectX;
using namespace CharactersDetail;

void Characters::LoadSequences(const std::wstring& folder, uint32_t modelCount) {
    mBoardingOrigin = {};
    mBoardingActorCount = 0;

    std::wstring seqPath = folder + L"\\sequences\\shuttle_boarding.txt";
    if (GetFileAttributesW(seqPath.c_str()) == INVALID_FILE_ATTRIBUTES)
        seqPath = folder + L"\\boarding.txt";
    if (GetFileAttributesW(seqPath.c_str()) == INVALID_FILE_ATTRIBUTES) return;

    std::ifstream bf(seqPath, std::ios::binary);
    std::string line;
    while (std::getline(bf, line)) {
        if (line.size() >= 3 && line.compare(0, 3, "\xEF\xBB\xBF") == 0) line.erase(0, 3);
        const size_t first = line.find_first_not_of(" \t\r\n");
        if (first == std::string::npos || line[first] == '#') continue;
        line = line.substr(first);
        if (line.compare(0, 4, "PARK") == 0) {
            std::istringstream ps(line.substr(4));
            double px = 0, py = 0, pz = 0, yawDeg = 0;
            if (ps >> px >> py >> pz >> yawDeg)
                mBoardingOrigin = { true, px, py, pz, yawDeg * XM_PI / 180.0 };
            continue;
        }
        const size_t bar = line.find('|');
        if (line.compare(0, 5, "ACTOR") == 0 && bar != std::string::npos) {
            std::istringstream hs(line.substr(5, bar - 5));
            uint32_t mdl = 0, wClip = 0, sClip = 3;
            float delay = 0.0f, spd = 1.25f, syawDeg = -90.0f;
            int pilotFlag = 0;
            if (!(hs >> mdl >> wClip >> sClip >> delay >> spd >> syawDeg >> pilotFlag)) continue;
            if (mdl >= modelCount || wClip >= ClipCount || sClip >= ClipCount) continue;

            std::vector<XMFLOAT3> wps;
            std::istringstream ws(line.substr(bar + 1));
            std::string seg;
            while (std::getline(ws, seg, ';')) {
                std::istringstream cs(seg);
                float x = 0, y = 0, z = 0;
                if (cs >> x >> y >> z) wps.push_back({ x, y, z });
            }
            if (wps.size() < 3) continue;

            const size_t idx = mActors.size();
            Actor a;
            a.model = mdl;
            a.clip = wClip;
            a.waitClip = wClip;
            a.seatClip = sClip;
            a.speed = std::max(spd, 0.3f);
            a.phase = std::fmod(float(idx) * 0.19f, 1.0f);
            a.tint = { 1.0f, 1.0f, 1.0f, 1.0f };
            a.waypoints = std::move(wps);
            a.isSequence = true;
            a.sequenceId = Gameplay::SequenceId::ShuttleBoarding;
            a.isPilot = (pilotFlag != 0);
            a.startDelay = delay;
            a.seatYaw = syawDeg * float(XM_PI / 180.0);
            a.pathLength = 0.0;
            // Walk segments stop at waypoints[size - 2]; waypoints.back() is the seated anchor.
            for (size_t w = 0; w + 2 < a.waypoints.size(); ++w) {
                const auto& p0 = a.waypoints[w];
                const auto& p1 = a.waypoints[w + 1];
                const double d = std::sqrt(double(p1.x - p0.x) * (p1.x - p0.x)
                                         + double(p1.y - p0.y) * (p1.y - p0.y)
                                         + double(p1.z - p0.z) * (p1.z - p0.z));
                a.pathLength += d;
            }
            const double idleDur = std::max<double>(mModels[a.model].clips[0]->duration(), 1e-4);
            a.idleTime = std::fmod(double(idx) * 0.73, idleDur);
            const auto& wAnim = *(mModels[a.model].clips[a.waitClip] ? mModels[a.model].clips[a.waitClip] : mModels[a.model].clips[0]);
            a.clipTime = std::fmod(double(idx) * 0.61, std::max<double>(wAnim.duration(), 1e-4));
            a.yaw = std::atan2(a.waypoints[1].y - a.waypoints[0].y, a.waypoints[1].x - a.waypoints[0].x);
            a.walkWeight = 0.0f;
            a.curSpeed = 0.0f;
            a.dstVertexOffset = mTotalSkinnedVerts;
            a.boneBaseOffset = mTotalBones;
            mTotalSkinnedVerts += mModels[a.model].vertexCount;
            mTotalBones += mJointCount;
            a.prevBones.resize(mJointCount);
            a.blinkTimer = 1.2f + std::fmod(float(idx) * 1.13f, 3.6f);
            a.blinkPhase = -1.0f;
            mActors.push_back(std::move(a));
            mImpl->contexts.push_back(std::make_unique<ozz::animation::SamplingJob::Context>(mModels[mdl].skeleton->num_joints()));
            mImpl->idleContexts.push_back(std::make_unique<ozz::animation::SamplingJob::Context>(mModels[mdl].skeleton->num_joints()));
            ++mBoardingActorCount;
        }
    }
}

bool Characters::HasSequence(Gameplay::SequenceId id) const {
    return id == Gameplay::SequenceId::ShuttleBoarding && mBoardingActorCount > 0;
}

Characters::SequenceAnchor Characters::SequenceOrigin(Gameplay::SequenceId id) const {
    return id == Gameplay::SequenceId::ShuttleBoarding ? mBoardingOrigin : SequenceAnchor{};
}

Characters::SequenceProgress Characters::SequenceState(Gameplay::SequenceId id) const {
    SequenceProgress prog = {};
    for (const Actor& a : mActors) {
        if (!a.isSequence || a.sequenceId != id) continue;
        ++prog.total;
        if (a.boardPhase == 3 && a.sitBlend >= 0.99f) ++prog.done;
    }
    return prog;
}

void Characters::ResetSequence(Gameplay::SequenceId id) {
    for (Actor& a : mActors) {
        if (!a.isSequence || a.sequenceId != id) continue;
        a.boardPhase = 0;
        a.boardDist = 0.0;
        a.walkWeight = 0.0f;
        a.curSpeed = 0.0f;
        a.sitBlend = 0.0f;
        a.walkCycle = 0.0;
        a.hasPrev = false;
        a.aimBlend = 0.0f;
        a.smoothPelvisY = 0.0f;
        a.yaw = std::atan2(a.waypoints[1].y - a.waypoints[0].y, a.waypoints[1].x - a.waypoints[0].x);
    }
}

void Characters::UpdateSequenceActor(size_t i, double dt, bool historyValid, const Vec3d& camPos,
                                     const Vec3d& faceX, const Vec3d& faceY, const Vec3d& faceZ,
                                     FXMMATRIX viewProj, const SequenceFrame& seq,
                                     double& minDist2, XMFLOAT3& clusterSum, UINT& nearCount) {
    Actor& a = mActors[i];
    const Model& m = mModels[a.model];

    if (seq.phase == Gameplay::SequencePhase::Dormant || !seq.shuttleValid) {
        a.hasPrev = false;
        const XMMATRIX hideModel = XMMatrixScaling(0.0f, 0.0f, 0.0f);
        XMStoreFloat4x4(&mInstancePtr[i].currModel, hideModel);
        XMStoreFloat4x4(&mInstancePtr[i].prevClipModel, hideModel);
        mInstancePtr[i].tint = a.tint;
        mInstancePtr[i].meta = { m.firstVertex, m.vertexCount, a.dstVertexOffset, a.boneBaseOffset };
        return;
    }

    auto toFace = [&](const Vec3d& v) {
        return XMVectorSet(float(Dot(v, faceX)), float(Dot(v, faceY)), float(Dot(v, faceZ)), 0.0f);
    };

    const ozz::animation::Animation& idleAnim = *m.clips[0];
    const ozz::animation::Animation& walkAnim = *(m.clips[1] ? m.clips[1] : m.clips[0]);
    const double idleDur = std::max<double>(idleAnim.duration(), 1e-4);
    const size_t soaCount = size_t(m.skeleton->num_soa_joints());

    auto sampleClip = [&](uint32_t clipIdx, ozz::animation::SamplingJob::Context* ctx, double tSec,
                          ozz::vector<ozz::math::SoaTransform>& dst) {
        const ozz::animation::Animation& cAnim = *(m.clips[clipIdx] ? m.clips[clipIdx] : m.clips[0]);
        const double cDur = std::max<double>(cAnim.duration(), 1e-4);
        ozz::animation::SamplingJob sj;
        sj.animation = &cAnim;
        sj.context = ctx;
        sj.ratio = float(std::fmod(std::max(0.0, tSec), cDur) / cDur);
        sj.output = ozz::span<ozz::math::SoaTransform>(dst.data(), soaCount);
        sj.Run();
    };
    auto blendLocals = [&](float weightB) {
        ozz::animation::BlendingJob::Layer layers[2];
        layers[0].transform = ozz::span<const ozz::math::SoaTransform>(mImpl->localsA.data(), soaCount);
        layers[0].weight = 1.0f - weightB;
        layers[1].transform = ozz::span<const ozz::math::SoaTransform>(mImpl->localsB.data(), soaCount);
        layers[1].weight = weightB;
        ozz::animation::BlendingJob blend;
        blend.threshold = 0.1f;
        blend.layers = ozz::make_span(layers);
        blend.rest_pose = m.skeleton->joint_rest_poses();
        blend.output = ozz::span<ozz::math::SoaTransform>(mImpl->locals.data(), soaCount);
        blend.Run();
    };
    auto runLtm = [&]() {
        ozz::animation::LocalToModelJob ltmJob;
        ltmJob.skeleton = m.skeleton.get();
        ltmJob.input = ozz::span<const ozz::math::SoaTransform>(mImpl->locals.data(), size_t(m.skeleton->num_soa_joints()));
        ltmJob.output = ozz::span<ozz::math::Float4x4>(mImpl->models.data(), size_t(m.skeleton->num_joints()));
        ltmJob.Run();
    };

    const auto& standEnd = a.waypoints[a.waypoints.size() - 2];
    const auto& seatEnd = a.waypoints.back();
    double sx = a.waypoints[0].x, sy = a.waypoints[0].y, sz = a.waypoints[0].z;

    if (a.boardPhase == 0) {
        a.clipTime = std::fmod(a.clipTime + dt, std::max<double>(m.clips[a.waitClip]->duration(), 1e-4));
        a.idleTime = std::fmod(a.idleTime + dt, idleDur);
        const double tyaw = std::atan2(double(a.waypoints[1].y) - sy, double(a.waypoints[1].x) - sx);
        a.yaw = float(tyaw);
        sampleClip(a.waitClip, mImpl->contexts[i].get(), a.clipTime, mImpl->locals);
        if (seq.phase == Gameplay::SequencePhase::Running && seq.clock >= double(a.startDelay)) {
            a.boardPhase = 1;
            a.boardDist = 0.0;
            a.walkWeight = 0.0f;
            a.walkCycle = 0.0;
        }
    } else if (a.boardPhase == 1) {
        a.walkWeight = std::min(1.0f, a.walkWeight + float(dt) * 2.2f);
        const float walkEaseB = a.walkWeight * a.walkWeight * (3.0f - 2.0f * a.walkWeight);
        // Measure current Y to step cleanly up the 8-riser airstair at natural climb speed.
        double remProbe = a.boardDist;
        double curYProbe = a.waypoints[0].y;
        for (size_t w = 0; w + 2 < a.waypoints.size(); ++w) {
            const auto& p0 = a.waypoints[w];
            const auto& p1 = a.waypoints[w + 1];
            const double seg3 = std::sqrt(double(p1.x - p0.x) * (p1.x - p0.x)
                                          + double(p1.y - p0.y) * (p1.y - p0.y)
                                          + double(p1.z - p0.z) * (p1.z - p0.z));
            if (remProbe <= seg3 || w + 3 == a.waypoints.size()) {
                const double t = seg3 > 1e-6 ? ClampD(remProbe / seg3, 0.0, 1.0) : 0.0;
                curYProbe = p0.y + (p1.y - p0.y) * t;
                break;
            }
            remProbe -= seg3;
        }
        const float stairFactor = (curYProbe >= 3.30 && curYProbe <= 6.00) ? 0.65f : 1.0f;
        a.curSpeed = a.speed * walkEaseB * stairFactor;
        const double stepM = double(a.curSpeed) * dt;
        a.boardDist = std::min(a.pathLength, a.boardDist + stepM);
        const double effStride = double(m.strideMeters) * std::max(double(a.tint.w), 0.5);
        a.walkCycle = std::fmod(a.walkCycle + stepM / effStride, 1.0);
        a.idleTime = std::fmod(a.idleTime + dt, idleDur);

        double rem = a.boardDist;
        for (size_t w = 0; w + 2 < a.waypoints.size(); ++w) {
            const auto& p0 = a.waypoints[w];
            const auto& p1 = a.waypoints[w + 1];
            const double dx = double(p1.x) - p0.x, dy = double(p1.y) - p0.y, dz = double(p1.z) - p0.z;
            const double seg3 = std::sqrt(dx * dx + dy * dy + dz * dz);
            if (rem <= seg3 || w + 3 == a.waypoints.size()) {
                const double t = seg3 > 1e-6 ? ClampD(rem / seg3, 0.0, 1.0) : 0.0;
                sx = p0.x + dx * t;
                sy = p0.y + dy * t;
                sz = p0.z + dz * t;
                if (std::hypot(dx, dy) > 1e-4) {
                    const double tyaw = std::atan2(dy, dx);
                    double diff = tyaw - double(a.yaw);
                    while (diff > XM_PI) diff -= 2.0 * XM_PI;
                    while (diff < -XM_PI) diff += 2.0 * XM_PI;
                    if (!a.hasPrev) a.yaw = float(tyaw);
                    else a.yaw = float(double(a.yaw) + diff * (1.0 - std::exp(-dt * 9.0)));
                }
                break;
            }
            rem -= seg3;
        }
        if (walkEaseB < 0.999f) {
            sampleClip(0, mImpl->idleContexts[i].get(), a.idleTime, mImpl->localsA);
            ozz::animation::SamplingJob sjWalk;
            sjWalk.animation = &walkAnim;
            sjWalk.context = mImpl->contexts[i].get();
            sjWalk.ratio = float(a.walkCycle);
            sjWalk.output = ozz::span<ozz::math::SoaTransform>(mImpl->localsB.data(), soaCount);
            sjWalk.Run();
            blendLocals(walkEaseB);
        } else {
            ozz::animation::SamplingJob sjWalk;
            sjWalk.animation = &walkAnim;
            sjWalk.context = mImpl->contexts[i].get();
            sjWalk.ratio = float(a.walkCycle);
            sjWalk.output = ozz::span<ozz::math::SoaTransform>(mImpl->locals.data(), soaCount);
            sjWalk.Run();
        }
        if (a.boardDist >= a.pathLength - 1e-4) a.boardPhase = 2;
    } else if (a.boardPhase == 2) {
        sx = standEnd.x; sy = standEnd.y; sz = standEnd.z;
        a.walkWeight = std::max(0.0f, a.walkWeight - float(dt) * 3.2f);
        const float walkEaseB = a.walkWeight * a.walkWeight * (3.0f - 2.0f * a.walkWeight);
        a.idleTime = std::fmod(a.idleTime + dt, idleDur);
        double diff = double(a.seatYaw) - double(a.yaw);
        while (diff > XM_PI) diff -= 2.0 * XM_PI;
        while (diff < -XM_PI) diff += 2.0 * XM_PI;
        a.yaw = float(double(a.yaw) + diff * (1.0 - std::exp(-dt * 8.5)));

        if (walkEaseB > 0.001f) {
            sampleClip(0, mImpl->idleContexts[i].get(), a.idleTime, mImpl->localsA);
            ozz::animation::SamplingJob sjWalk;
            sjWalk.animation = &walkAnim;
            sjWalk.context = mImpl->contexts[i].get();
            sjWalk.ratio = float(a.walkCycle);
            sjWalk.output = ozz::span<ozz::math::SoaTransform>(mImpl->localsB.data(), soaCount);
            sjWalk.Run();
            blendLocals(walkEaseB);
        } else {
            sampleClip(0, mImpl->idleContexts[i].get(), a.idleTime, mImpl->locals);
        }
        if (std::fabs(diff) < 0.14 && a.walkWeight < 0.25f) {
            a.boardPhase = 3;
            a.sitBlend = 0.0f;
            a.clipTime = std::fmod(double(i) * 0.85, std::max<double>((m.clips[a.seatClip] ? m.clips[a.seatClip] : m.clips[0])->duration(), 1e-4));
        }
    } else {
        a.sitBlend = std::min(1.0f, a.sitBlend + float(dt) / 0.85f);
        const float sEase = a.sitBlend * a.sitBlend * (3.0f - 2.0f * a.sitBlend);
        sx = double(standEnd.x) + (double(seatEnd.x) - double(standEnd.x)) * double(sEase);
        sy = double(standEnd.y) + (double(seatEnd.y) - double(standEnd.y)) * double(sEase);
        sz = double(standEnd.z) + (double(seatEnd.z) - double(standEnd.z)) * double(sEase);
        double diff = double(a.seatYaw) - double(a.yaw);
        while (diff > XM_PI) diff -= 2.0 * XM_PI;
        while (diff < -XM_PI) diff += 2.0 * XM_PI;
        a.yaw = float(double(a.yaw) + diff * (1.0 - std::exp(-dt * 12.0)));

        a.idleTime = std::fmod(a.idleTime + dt, idleDur);
        const double sDur = std::max<double>((m.clips[a.seatClip] ? m.clips[a.seatClip] : m.clips[0])->duration(), 1e-4);
        a.clipTime = std::fmod(a.clipTime + dt, sDur);
        if (sEase < 0.999f) {
            sampleClip(0, mImpl->idleContexts[i].get(), a.idleTime, mImpl->localsA);
            sampleClip(a.seatClip, mImpl->contexts[i].get(), a.clipTime, mImpl->localsB);
            blendLocals(sEase);
        } else {
            sampleClip(a.seatClip, mImpl->contexts[i].get(), a.clipTime, mImpl->locals);
        }
    }

    runLtm();

    // Keep pilot boots cleanly resting above the cockpit floor / rudder pedals on the lower pilot sled seat.
    if (a.isPilot && a.boardPhase == 3 && a.sitBlend > 0.01f && m.ik.thighL >= 0 && m.ik.calfL >= 0
        && m.ik.footL >= 0 && m.ik.thighR >= 0 && m.ik.calfR >= 0 && m.ik.footR >= 0) {
        const float sEase = a.sitBlend * a.sitBlend * (3.0f - 2.0f * a.sitBlend);
        auto raiseFoot = [&](int thigh, int calf, int foot) {
            float col3[4];
            ozz::math::StorePtrU(mImpl->models[size_t(foot)].cols[3], col3);
            ozz::animation::IKTwoBoneJob ik;
            ik.target = ozz::math::simd_float4::Load(col3[0], col3[1] + 0.070f * sEase, col3[2] + 0.025f * sEase, 0.0f);
            ik.mid_axis = ozz::math::simd_float4::Load(-1.0f, 0.0f, 0.0f, 0.0f);
            ik.pole_vector = ozz::math::simd_float4::z_axis();
            ik.soften = 0.97f;
            ik.weight = sEase;
            ik.start_joint = &mImpl->models[size_t(thigh)];
            ik.mid_joint = &mImpl->models[size_t(calf)];
            ik.end_joint = &mImpl->models[size_t(foot)];
            ozz::math::SimdQuaternion scQ, mcQ;
            ik.start_joint_correction = &scQ;
            ik.mid_joint_correction = &mcQ;
            if (ik.Run()) {
                MultiplySoaQuaternion(mImpl->locals, thigh, scQ);
                MultiplySoaQuaternion(mImpl->locals, calf, mcQ);
            }
        };
        raiseFoot(m.ik.thighL, m.ik.calfL, m.ik.footL);
        raiseFoot(m.ik.thighR, m.ik.calfR, m.ik.footR);
        runLtm();
    }

    const double cYawB = std::cos(double(a.yaw)), sYawB = std::sin(double(a.yaw));
    const Vec3d fwdB = seq.left * cYawB + seq.back * sYawB;
    const Vec3d leftB = seq.back * cYawB - seq.left * sYawB;
    const Vec3d upB = seq.up;
    float scB = a.tint.w;
    const Vec3d worldPos = seq.pos + seq.left * sx + seq.back * sy + seq.up * sz;
    const Vec3d rel = worldPos - camPos;
    const double d2 = Dot(rel, rel);
    if (seq.cockpitCamera && a.isPilot && d2 < 0.85 * 0.85) scB = 0.0f;
    if (scB > 0.0f) minDist2 = std::min(minDist2, d2);

    const float aimAllow = (a.boardPhase == 0 || (a.boardPhase == 3 && !a.isPilot)) ? 0.50f : 0.0f;
    if (m.ik.neck >= 0 && m.ik.head >= 0 && (aimAllow > 0.01f || a.aimBlend > 0.01f) && scB > 0.0f) {
        float headPos[4];
        ozz::math::StorePtrU(mImpl->models[size_t(m.ik.head)].cols[3], headPos);
        XMFLOAT3 targetLocal = { 0.0f, headPos[1], 3.0f };
        float desiredBlend = 0.0f;
        const Vec3d toCam = camPos - worldPos;
        const double camDist = std::sqrt(Dot(toCam, toCam));
        if (aimAllow > 0.01f && camDist > 0.7 && camDist < 6.5) {
            const double localZ = Dot(toCam, fwdB) / double(scB);
            const double localX = Dot(toCam, leftB) / double(scB);
            const double localY = Dot(toCam, upB) / double(scB);
            const double horiz = std::hypot(localX, localZ);
            if (localZ > 0.25 && std::atan2(std::fabs(localX), localZ) < 0.95 && horiz > 0.5) {
                const float clampedY = float(ClampD(localY, double(headPos[1]) - horiz * 0.35, double(headPos[1]) + horiz * 0.35));
                targetLocal = { float(localX), clampedY, float(localZ) };
                desiredBlend = float(ClampD((6.5 - camDist) / 2.2, 0.0, 1.0)) * aimAllow;
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
            const ozz::math::SimdFloat4 aimTarget = ozz::math::simd_float4::Load(a.smoothAimLocal.x, a.smoothAimLocal.y, a.smoothAimLocal.z, 0.0f);
            const int chain[2] = { m.ik.neck, m.ik.head };
            const float weights[2] = { 0.35f * a.aimBlend, 0.65f * a.aimBlend };
            for (int k = 0; k < 2; ++k) {
                ozz::animation::IKAimJob aim;
                aim.target = aimTarget;
                aim.forward = ozz::math::simd_float4::z_axis();
                aim.up = ozz::math::simd_float4::y_axis();
                aim.pole_vector = ozz::math::simd_float4::y_axis();
                aim.offset = (k == 1) ? ozz::math::simd_float4::Load(0.0f, 0.05f, 0.08f, 0.0f) : ozz::math::simd_float4::zero();
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

    if (m.ik.eyelidL >= 0 && m.ik.eyelidR >= 0 && a.hasPrev) {
        if (a.blinkPhase >= 0.0f) {
            a.blinkPhase += float(dt);
            const float closeDur = 0.070f, holdDur = 0.025f, openDur = 0.115f;
            const float totalDur = closeDur + holdDur + openDur;
            float bAmt = 0.0f;
            if (a.blinkPhase < closeDur) { const float u = a.blinkPhase / closeDur; bAmt = u * u * (3.0f - 2.0f * u); }
            else if (a.blinkPhase < closeDur + holdDur) { bAmt = 1.0f; }
            else if (a.blinkPhase < totalDur) { const float u = 1.0f - (a.blinkPhase - closeDur - holdDur) / openDur; bAmt = u * u * (3.0f - 2.0f * u); }
            else { a.blinkPhase = -1.0f; a.blinkTimer = 3.0f + std::fmod(float(a.idleTime * 1.7 + double(i) * 0.83), 2.6f); }
            if (bAmt > 0.005f) {
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
        XMVectorScale(toFace(leftB), scB),
        XMVectorScale(toFace(upB), scB),
        XMVectorScale(toFace(fwdB), scB),
        XMVectorSetW(toFace(rel), 1.0f));
    const XMMATRIX currClip = currModel * viewProj;
    const XMMATRIX prevClip = (a.hasPrev && historyValid) ? XMLoadFloat4x4(&a.prevClipModel) : currClip;

    XMStoreFloat4x4(&mInstancePtr[i].currModel, XMMatrixTranspose(currModel));
    XMStoreFloat4x4(&mInstancePtr[i].prevClipModel, XMMatrixTranspose(prevClip));
    mInstancePtr[i].tint = a.tint;
    mInstancePtr[i].meta = { m.firstVertex, m.vertexCount, a.dstVertexOffset, a.boneBaseOffset };

    XMStoreFloat4x4(&a.prevClipModel, currClip);
    a.hasPrev = true;

    if (scB > 0.0f && d2 < 80.0 * 80.0) {
        XMFLOAT3 relF;
        XMStoreFloat3(&relF, toFace(rel));
        clusterSum.x += relF.x; clusterSum.y += relF.y; clusterSum.z += relF.z;
        ++nearCount;
    }
}
