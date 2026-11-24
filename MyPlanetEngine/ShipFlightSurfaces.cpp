// Sleeved airfoil and hinged brake panels in the existing ship pack's metre frame.
#include "Ship.h"
#include <algorithm>
#include <array>
#include <cmath>

using namespace DirectX;

namespace {
constexpr unsigned Rings = 9, Sections = 24;
constexpr float BrakeRoot = .22f, BrakeTip = .90f;

struct Vertex {
    XMFLOAT3 position, normal;
    XMFLOAT4 tangent;
    XMFLOAT2 uv, detailUv;
    float pose;
};
static_assert(sizeof(Vertex) == 60, "ShipVertex layout");

struct Material {
    XMFLOAT4 color;
    XMFLOAT3 emission;
    float metal, roughness, normalScale, occlusion;
    uint32_t mode, doubleSided;
    int32_t image[5] = {-1, -1, -1, -1, -1};
    uint32_t uv[5] = {};
    uint32_t role;
};
static_assert(sizeof(Material) == 96, "ShipMaterial layout");

float Chord(const FlightSurfaceLayout& s, float span) {
    return s.chord * (1 - .75f * span * span);
}

XMFLOAT3 BrakeHinge(const FlightSurfaceLayout& s, float side, float span) {
    return {side * (s.x + s.span * span), s.y + s.sweep * span + .13f * Chord(s, span),
            s.z + .07f * span + s.thickness * (.91f - .31f * span)};
}

XMFLOAT3 SectionPoint(const FlightSurfaceLayout& s, float side, float t, float angle, bool brake) {
    const float span = brake ? BrakeRoot + (BrakeTip - BrakeRoot) * t : t;
    const float chord = Chord(s, span);
    const float roundTip = std::sqrt(1 - .98f * std::pow(t, 14.0f));
    const float ca = std::cos(angle), sa = std::sin(angle);
    if (brake) {
        const XMFLOAT3 hinge = BrakeHinge(s, side, span);
        return {hinge.x, hinge.y + chord * .16f * (1 + ca * roundTip),
                hinge.z + .023f * sa * roundTip};
    }
    return {side * (s.x + s.span * span), s.y + s.sweep * span + .5f * chord * ca * roundTip,
            s.z + .07f * span + s.thickness * (1 - .36f * span) * sa * roundTip};
}

XMMATRIX HingeRotation(FXMVECTOR pivot, const XMMATRIX& rotation) {
    return XMMatrixTranslationFromVector(-pivot) * rotation * XMMatrixTranslationFromVector(pivot);
}
}

void Ship::BuildFlightSurfaces() {
    const FlightSurfaceLayout& s = mProfile.surfaces;
    if (HasTransportRig() || s.span <= 0 || mFlightFittings.brakeAngle > 0) return;
    const bool shuttle = mProfile.model == ShipModel::Navette;
    const uint32_t firstMaterial = uint32_t(mModes.size());
    const Material materials[] = {
        {shuttle ? XMFLOAT4(.28f, .29f, .30f, 1) : XMFLOAT4(.23f, .25f, .27f, 1), {},
         .78f, .29f, 1, 1, 0, 0, {-1, -1, -1, -1, -1}, {}, 0},
        {{.14f, .17f, .19f, 1}, {},
         .83f, .27f, 1, 1, 0, 0, {-1, -1, -1, -1, -1}, {}, 0},
    };
    for (const Material& material : materials) {
        const auto* bytes = reinterpret_cast<const uint8_t*>(&material);
        mMaterialBytes.insert(mMaterialBytes.end(), bytes, bytes + sizeof(material));
        mModes.push_back(material.mode);
        mRoles.push_back(material.role);
    }

    for (unsigned part = 0; part < 4; ++part) {
        const float side = part % 2 == 0 ? 1.0f : -1.0f;
        const bool brake = part >= 2;
        const float pose = float(SHIP_PACK_POSES + 1 + part);
        std::array<Vertex, Rings * Sections + 2> vertices = {};
        for (unsigned ring = 0; ring < Rings; ++ring)
            for (unsigned edge = 0; edge < Sections; ++edge) {
                const float t = float(ring) / (Rings - 1);
                const float a = XM_2PI * float(edge) / Sections;
                Vertex& v = vertices[ring * Sections + edge];
                v.position = SectionPoint(s, side, t, a, brake);
                const XMFLOAT3 p0 = SectionPoint(s, side, std::max(0.0f, t - .002f), a, brake);
                const XMFLOAT3 p1 = SectionPoint(s, side, std::min(1.0f, t + .002f), a, brake);
                const XMFLOAT3 p2 = SectionPoint(s, side, t, a - .005f, brake);
                const XMFLOAT3 p3 = SectionPoint(s, side, t, a + .005f, brake);
                const XMVECTOR along = XMVector3Normalize(XMLoadFloat3(&p1) - XMLoadFloat3(&p0));
                const XMVECTOR around = XMLoadFloat3(&p3) - XMLoadFloat3(&p2);
                XMStoreFloat3(&v.normal, XMVector3Normalize(XMVector3Cross(around, along) * side));
                XMStoreFloat4(&v.tangent, XMVectorSetW(along, 1));
                v.pose = pose;
            }
        for (unsigned end = 0; end < 2; ++end) {
            Vertex& cap = vertices[Rings * Sections + end];
            const float t = float(end);
            const XMFLOAT3 a = SectionPoint(s, side, t, 0, brake), b = SectionPoint(s, side, t, XM_PI, brake);
            cap.position = {a.x, .5f * (a.y + b.y), .5f * (a.z + b.z)};
            cap.normal = {side * (end ? 1.0f : -1.0f), 0, 0};
            cap.tangent = {0, 1, 0, 1};
            cap.pose = pose;
        }
        const uint32_t base = uint32_t(mVertexBytes.size() / sizeof(Vertex)), first = uint32_t(mIndices.size());
        const auto* bytes = reinterpret_cast<const uint8_t*>(vertices.data());
        mVertexBytes.insert(mVertexBytes.end(), bytes, bytes + sizeof(vertices));
        auto triangle = [&](uint32_t a, uint32_t b, uint32_t c) {
            mIndices.insert(mIndices.end(), {base + a, base + (side > 0 ? b : c), base + (side > 0 ? c : b)});
        };
        for (uint32_t edge = 0; edge < Sections; ++edge) {
            const uint32_t next = (edge + 1) % Sections;
            for (uint32_t ring = 0; ring + 1 < Rings; ++ring) {
                const uint32_t row = ring * Sections;
                triangle(row + edge, row + next, row + edge + Sections);
                triangle(row + next, row + next + Sections, row + edge + Sections);
            }
            triangle(Rings * Sections, next, edge);
            triangle(Rings * Sections + 1, (Rings - 1) * Sections + edge, (Rings - 1) * Sections + next);
        }
        mDraws.push_back({first, uint32_t(mIndices.size()) - first, firstMaterial + uint32_t(brake)});
    }
}

void Ship::SetFlightSurfaces(float wings, float airbrakes) {
    const FlightSurfaceLayout& s = mProfile.surfaces;
    if (s.span <= 0) return;
    for (unsigned wing = 0; wing < 2; ++wing) {
        const float side = wing == 0 ? 1.0f : -1.0f;
        const float folded = 1 - wings;
        XMMATRIX sleeve, flap;
        if (mFlightFittings.brakeAngle > 0) {
            const auto& fit = mFlightFittings;
            const XMVECTOR mirrored = XMVectorSet(side, 1, 1, 0);
            const XMVECTOR pivot = XMLoadFloat3(&fit.wingPivot) * mirrored;
            const XMVECTOR brakePivot = XMLoadFloat3(&fit.brakePivot) * mirrored;
            const XMVECTOR brakeAxis = XMLoadFloat3(&fit.brakeAxis) * mirrored;
            // In FLW2 the shared nacelle skin carries the travel in vertex space.
            sleeve = fit.foldedAngle > 0 ? HingeRotation(pivot, XMMatrixRotationZ(side * fit.foldedAngle * folded))
                                         : XMMatrixIdentity();
            const float clearance = std::max(0.0f, std::min(1.0f, (wings - .28f) / .44f));
            flap = HingeRotation(brakePivot, XMMatrixRotationAxis(brakeAxis, side * fit.brakeAngle * airbrakes * clearance)) * sleeve;
        } else {
            const XMVECTOR mount = XMVectorSet(side * s.x, s.y, s.z, 0);
            const float scale = 1 - .44f * folded;
            sleeve = HingeRotation(mount, XMMatrixScaling(scale, scale, scale)
                   * XMMatrixRotationZ(side * .50f * folded)) * XMMatrixTranslation(-side * s.retraction * folded, 0, 0);
            const XMFLOAT3 hinge = BrakeHinge(s, side, BrakeRoot);
            const XMFLOAT3 end = BrakeHinge(s, side, BrakeTip);
            const XMVECTOR root = XMLoadFloat3(&hinge);
            const XMVECTOR axis = XMVector3Normalize(XMLoadFloat3(&end) - root);
            flap = HingeRotation(root, XMMatrixRotationAxis(axis, side * 1.08f * airbrakes * wings)) * sleeve;
        }
        XMStoreFloat4x4(&mConstants->pose[SHIP_PACK_POSES + wing], XMMatrixTranspose(sleeve));
        XMStoreFloat4x4(&mConstants->pose[SHIP_PACK_POSES + 2 + wing], XMMatrixTranspose(flap));
    }
}
