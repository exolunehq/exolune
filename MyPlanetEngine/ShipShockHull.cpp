// Build the two supports of the external shock layer from the selected VSX, once per load.
// Gas bridges the recesses between panels, engines and the canopy. The inner convex
// support encloses them, and a parallel offset of its planes rounds the bow.
#include "Ship.h"
#include "GpuHelpers.h"
#include <algorithm>
#include <cmath>
#include <cstring>

using namespace DirectX;

namespace {
    constexpr int HullSide = 48;
    constexpr float Probe = 0.80f; // normal distance between supports, in metres

    float Dot(const XMFLOAT3& a, const XMFLOAT3& b) { return a.x*b.x + a.y*b.y + a.z*b.z; }

    // Direct3D's cube-array order and image coordinates (+u right, +v down).
    XMFLOAT3 CubeRay(int face, int x, int y, int side)
    {
        const float u = (2.0f*x + 1.0f)/side - 1.0f, v = (2.0f*y + 1.0f)/side - 1.0f;
        const float l = 1.0f/std::sqrt(1.0f + u*u + v*v);
        switch (face) {
        case 0: return {l, -v*l, -u*l};
        case 1: return {-l, -v*l, u*l};
        case 2: return {u*l, l, v*l};
        case 3: return {u*l, -l, -v*l};
        case 4: return {u*l, -v*l, l};
        default: return {-u*l, -v*l, -l};
        }
    }

    int CubeBin(const XMFLOAT3& p, int side)
    {
        const float x = std::fabs(p.x), y = std::fabs(p.y), z = std::fabs(p.z);
        float u, v, w;
        int face;
        if (x >= y && x >= z) { face = p.x >= 0 ? 0 : 1; w = x; u = face == 0 ? -p.z : p.z; v = -p.y; }
        else if (y >= z)      { face = p.y >= 0 ? 2 : 3; w = y; u = p.x; v = face == 2 ? p.z : -p.z; }
        else                  { face = p.z >= 0 ? 4 : 5; w = z; u = face == 4 ? p.x : -p.x; v = -p.y; }
        if (w < 1.e-7f) return 0;
        const int col = std::min(side-1, int((u/w + 1.0f)*0.5f*side));
        const int row = std::min(side-1, int((v/w + 1.0f)*0.5f*side));
        return (face*side + row)*side + col;
    }

}

XMFLOAT4 Ship::CreateShockHull(ID3D12Device* device, ID3D12GraphicsCommandList* list)
{
    // The bounds of each angular bin let a plane skip thousands of interior points
    // while still retaining the exact extremum of a small nose, wing or fin.
    constexpr int bins = 24;
    struct Bin { XMFLOAT3 farthest = {}, lo = {}, hi = {}; std::vector<XMFLOAT3> points; };
    std::vector<Bin> groups(6*bins*bins);
    std::vector<bool> visited(mVertexBytes.size()/60);
    XMFLOAT3 bounds = {};
    for (const Draw& draw : mDraws) {
        if (mProfile.sceneReflections ? mRoles[draw.material] != 10 : mModes[draw.material] == 1) continue;
        for (uint32_t i = draw.first; i < draw.first + draw.count; ++i) {
            const uint32_t id = mIndices[i];
            if (visited[id]) continue;
            visited[id] = true;
            XMFLOAT3 p;
            std::memcpy(&p, mVertexBytes.data() + size_t(id)*60, sizeof(p));
            p.y -= mProfile.centreY;
            p.z -= mProfile.centreZ;
            Bin& bin = groups[CubeBin(p, bins)];
            if (bin.points.empty()) bin.lo = bin.hi = p;
            bin.points.push_back(p);
            if (Dot(p,p) > Dot(bin.farthest,bin.farthest)) bin.farthest = p;
            bin.lo = {std::min(bin.lo.x,p.x), std::min(bin.lo.y,p.y), std::min(bin.lo.z,p.z)};
            bin.hi = {std::max(bin.hi.x,p.x), std::max(bin.hi.y,p.y), std::max(bin.hi.z,p.z)};
            bounds.x = std::max(bounds.x, std::fabs(p.x));
            bounds.y = std::max(bounds.y, std::fabs(p.y));
            bounds.z = std::max(bounds.z, std::fabs(p.z));
        }
    }

    struct Plane { XMFLOAT3 normal; float inverse, roundedInverse; };
    constexpr int planeSide = 9; // includes the six cardinal planes
    std::vector<Plane> planes;
    for (int f = 0; f < 6; ++f) for (int j = 0; j < planeSide; ++j) for (int i = 0; i < planeSide; ++i) {
        const XMFLOAT3 n = CubeRay(f, i, j, planeSide);
        float support = 0.0f;
        for (const auto& bin : groups) support = std::max(support, Dot(bin.farthest,n));
        for (const auto& bin : groups) {
            if (bin.points.empty()) continue;
            const XMFLOAT3 corner = {n.x >= 0 ? bin.hi.x : bin.lo.x, n.y >= 0 ? bin.hi.y : bin.lo.y, n.z >= 0 ? bin.hi.z : bin.lo.z};
            if (Dot(corner,n) <= support) continue;
            for (const auto& p : bin.points) support = std::max(support, Dot(p,n));
        }
        support = std::max(support, 0.08f) + 0.03f;
        planes.push_back({n, 1.0f/support, 1.0f/(support + Probe)});
    }

    // A unit ray leaves a convex body at 1/max(dot(ray, normal)/support).
    // The second distance gives the local conversion of radial to normal metres.
    std::vector<XMFLOAT4> pixels(6*HullSide*HullSide);
    for (int f = 0; f < 6; ++f) for (int y = 0; y < HullSide; ++y) for (int x = 0; x < HullSide; ++x) {
        const XMFLOAT3 ray = CubeRay(f, x, y, HullSide);
        float nearest = 0.0f, rounded = 0.0f;
        XMFLOAT3 normal = {};
        for (const Plane& plane : planes) {
            const float d = Dot(plane.normal, ray);
            nearest = std::max(nearest, d*plane.inverse);
            if (d*plane.roundedInverse > rounded) { rounded = d*plane.roundedInverse; normal = plane.normal; }
        }
        // A Cartesian vector carries both direction and radius; hardware filtering
        // remains continuous at the cube edges and at either pole of the ship.
        pixels[(f*HullSide + y)*HullSide + x] = {1.0f/nearest, normal.x/rounded, normal.y/rounded, normal.z/rounded};
    }

    const auto desc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R32G32B32A32_FLOAT, HullSide, HullSide, 6, 1);
    const CD3DX12_HEAP_PROPERTIES heap(D3D12_HEAP_TYPE_DEFAULT);
    Check(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_COPY_DEST,
                                         nullptr, IID_PPV_ARGS(&mShockHull)), "Ship shock hull creation failed.");
    UINT64 bytes;
    D3D12_PLACED_SUBRESOURCE_FOOTPRINT layout[6];
    device->GetCopyableFootprints(&desc, 0, 6, 0, layout, nullptr, nullptr, &bytes);
    mUploads.push_back(CreateBuffer(device, bytes, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ));
    uint8_t* mapped;
    const CD3DX12_RANGE noRead(0, 0);
    Check(mUploads.back()->Map(0, &noRead, reinterpret_cast<void**>(&mapped)), "Ship shock hull upload failed.");
    for (int f = 0; f < 6; ++f) {
        for (int y = 0; y < HullSide; ++y)
            std::memcpy(mapped + layout[f].Offset + size_t(y)*layout[f].Footprint.RowPitch,
                        &pixels[(f*HullSide+y)*HullSide], HullSide*sizeof(XMFLOAT4));
        const CD3DX12_TEXTURE_COPY_LOCATION dst(mShockHull.Get(), f), src(mUploads.back().Get(), layout[f]);
        list->CopyTextureRegion(&dst, 0, 0, 0, &src, nullptr);
    }
    mUploads.back()->Unmap(0, nullptr);
    D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
    srv.Format = desc.Format;
    srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURECUBE;
    srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    srv.TextureCube.MipLevels = 1;
    device->CreateShaderResourceView(mShockHull.Get(), &srv, Cpu(MaxImages + 10));
    return {bounds.x + 1.65f, bounds.y + 1.65f, bounds.z + 1.65f, Probe};
}
