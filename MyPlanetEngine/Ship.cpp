// Ship.cpp - see Ship.h.
#include "Ship.h"
#include "GpuHelpers.h"
#include <wincodec.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>

using Microsoft::WRL::ComPtr;
using namespace DirectX;

namespace
{
    template <class T> T Read(const std::vector<uint8_t>& data, size_t& at)
    {
        if (at + sizeof(T) > data.size()) throw std::runtime_error("Ship pack truncated.");
        T value;
        std::memcpy(&value, data.data() + at, sizeof(T));
        at += sizeof(T);
        return value;
    }

    // A PNG from memory to RGBA8, by the Windows Imaging Component.
    void DecodePng(IWICImagingFactory* factory, const std::vector<uint8_t>& png, UINT& width, UINT& height, std::vector<uint8_t>& rgba)
    {
        ComPtr<IWICStream> stream;
        Check(factory->CreateStream(&stream), "WIC stream creation failed.");
        Check(stream->InitializeFromMemory(const_cast<BYTE*>(png.data()), (DWORD)png.size()), "WIC stream failed.");
        ComPtr<IWICBitmapDecoder> decoder;
        Check(factory->CreateDecoderFromStream(stream.Get(), nullptr, WICDecodeMetadataCacheOnDemand, &decoder), "Ship image unreadable.");
        ComPtr<IWICBitmapFrameDecode> frame;
        Check(decoder->GetFrame(0, &frame), "Ship image frame unreadable.");
        ComPtr<IWICFormatConverter> converter;
        Check(factory->CreateFormatConverter(&converter), "WIC converter creation failed.");
        Check(converter->Initialize(frame.Get(), GUID_WICPixelFormat32bppRGBA, WICBitmapDitherTypeNone, nullptr, 0.0,
                                    WICBitmapPaletteTypeCustom), "Ship image conversion failed.");
        Check(converter->GetSize(&width, &height), "Ship image size unreadable.");
        rgba.resize(size_t(width) * height * 4);
        Check(converter->CopyPixels(nullptr, width * 4, (UINT)rgba.size(), rgba.data()), "Ship image copy failed.");
    }

    // The next mip, 2 x 2 texels averaged. ponytail: averages the sRGB codes, a little dark on contrasted images; in
    // linear light if it shows.
    std::vector<uint8_t> HalfImage(const std::vector<uint8_t>& src, UINT width, UINT height)
    {
        const UINT w = std::max(width / 2, 1u), h = std::max(height / 2, 1u);
        std::vector<uint8_t> dst(size_t(w) * h * 4);
        for (UINT y = 0; y < h; ++y)
            for (UINT x = 0; x < w; ++x)
                for (UINT c = 0; c < 4; ++c) {
                    const UINT x0 = std::min(2 * x, width - 1), x1 = std::min(2 * x + 1, width - 1);
                    const UINT y0 = std::min(2 * y, height - 1), y1 = std::min(2 * y + 1, height - 1);
                    const UINT sum = src[(size_t(y0) * width + x0) * 4 + c] + src[(size_t(y0) * width + x1) * 4 + c]
                                   + src[(size_t(y1) * width + x0) * 4 + c] + src[(size_t(y1) * width + x1) * 4 + c];
                    dst[(size_t(y) * w + x) * 4 + c] = uint8_t((sum + 2) / 4);
                }
        return dst;
    }

    XMMATRIX LightFrame(const XMFLOAT3& towards, const ShipProfile& profile, float radius)
    {
        const XMVECTOR d = XMVector3Normalize(XMLoadFloat3(&towards));
        const XMVECTOR centre = XMVectorSet(0.0f, profile.centreY, profile.centreZ, 1.0f);
        const XMVECTOR up = std::fabs(towards.z) < 0.9f ? XMVectorSet(0, 0, 1, 0) : XMVectorSet(0, 1, 0, 0);
        return XMMatrixLookToLH(centre + d * 20.0f, -d, up)
             * XMMatrixOrthographicLH(2.0f * radius, 2.0f * radius, 0.1f, 40.0f);
    }
}

Ship::Ship()
{
    wchar_t model[32] = {};
    const DWORD size = GetEnvironmentVariableW(L"MYPLANETENGINE_MODELE_VAISSEAU", model, _countof(model));
    if (size == 0) return; // The executable alone starts with the fighter.
    if (size < _countof(model) && _wcsicmp(model, L"classique") == 0) mProfile = ClassicShip;
    else if (size < _countof(model) && _wcsicmp(model, L"navigateur") == 0) mProfile = NavigatorShip;
    else if (size < _countof(model) && _wcsicmp(model, L"navette") == 0) mProfile = ShuttleShip;
    else if (size >= _countof(model) || _wcsicmp(model, L"chasseur") != 0)
        throw std::runtime_error("MYPLANETENGINE_MODELE_VAISSEAU must be chasseur, classique, navigateur or navette.");
}

bool Ship::Load(const std::wstring& path)
{
    std::ifstream file(path, std::ios::binary);
    if (!file) return false;
    const std::vector<uint8_t> data((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    if (data.size() < 32 || std::memcmp(data.data(), "VSX1", 4) != 0) throw std::runtime_error("Not a ship pack (VSX1).");
    size_t at = 4;
    const uint32_t version = Read<uint32_t>(data, at);
    if (version != 2 && version != 3 && !(version == 4 && mProfile.model == ShipModel::Navette)) throw std::runtime_error("Ship pack version not supported.");
    const uint32_t vertices = Read<uint32_t>(data, at), indices = Read<uint32_t>(data, at), draws = Read<uint32_t>(data, at);
    const uint32_t materials = Read<uint32_t>(data, at), images = Read<uint32_t>(data, at);
    if (images > MaxImages) throw std::runtime_error("Ship pack has more images than Ship::MaxImages.");
    const size_t vertexBytes = size_t(vertices) * 60, materialSize = version == 2 ? 92 : 96;
    if (at + vertexBytes + size_t(indices) * 4 > data.size()) throw std::runtime_error("Ship pack truncated.");
    mVertexBytes.assign(data.begin() + at, data.begin() + at + vertexBytes);
    at += vertexBytes;
    mIndices.resize(indices);
    std::memcpy(mIndices.data(), data.data() + at, size_t(indices) * 4);
    at += size_t(indices) * 4;
    for (uint32_t i = 0; i < draws; ++i) {
        Draw d;
        d.first = Read<uint32_t>(data, at); d.count = Read<uint32_t>(data, at); d.material = Read<uint32_t>(data, at);
        mDraws.push_back(d);
    }
    if (at + materials * materialSize > data.size()) throw std::runtime_error("Ship pack truncated.");
    // VSX2's original material order encoded the screen roles. Expand it in memory to VSX3's layout;
    // the classic asset and its generator remain unchanged on disk.
    mMaterialBytes.resize(size_t(materials) * 96, 0);
    for (uint32_t m = 0; m < materials; ++m) {
        uint8_t* material = mMaterialBytes.data() + size_t(m) * 96;
        std::memcpy(material, data.data() + at + size_t(m) * materialSize, materialSize);
        if (version == 2) {
            const uint32_t role = m >= 13 && m <= 18 ? m - 12 : 0;
            std::memcpy(material + 92, &role, 4);
        }
        uint32_t mode;
        std::memcpy(&mode, material + 11 * 4, 4);
        mModes.push_back(mode);
        uint32_t role;
        std::memcpy(&role, material + 92, 4);
        mRoles.push_back(role);
    }
    at += materials * materialSize;
    for (uint32_t i = 0; i < images; ++i) {
        Image image;
        image.srgb = Read<uint32_t>(data, at) != 0;
        const uint32_t bytes = Read<uint32_t>(data, at);
        if (at + bytes > data.size()) throw std::runtime_error("Ship pack truncated.");
        image.png.assign(data.begin() + at, data.begin() + at + bytes);
        at += bytes;
        mImages.push_back(std::move(image));
    }
    const uint32_t pivotCount = Read<uint32_t>(data, at);
    if (version == 4) {
        mProfile.pivotCount = 2;
        mProfile.surfaces = {}; // The transport exhausts issue from its two fitted side grilles.
    }
    else if (mProfile.model == ShipModel::Navette) { mProfile.eyeAhead=3.47f; mProfile.eyeUp=-.84f; }
    if (pivotCount != mProfile.pivotCount) throw std::runtime_error("Ship pack does not match the selected profile.");
    for (uint32_t i = 0; i < pivotCount; ++i) pivots[i] = Read<Pivot>(data, at);
    if (version == 4) ReadTransport(data, at);
    else if (mProfile.model == ShipModel::Navette) ReadShuttleControls(data, at);
    mLoaded = true;
    return true;
}

void Ship::ReadTransport(const std::vector<uint8_t>& data, size_t& at)
{
    static_assert(sizeof(RigidKey)==28, "ANI1 position and xyzw quaternion");
    if (Read<uint32_t>(data, at)!=0x31494e41 || Read<uint32_t>(data, at)!=mTransportClips.size())
        throw std::runtime_error("Missing transport clips.");
    std::array<bool, SHIP_POSE_COUNT> used{};
    auto key = [&]() {
        auto value = Read<RigidKey>(data,at);
        const float norm = XMVectorGetX(XMVector4LengthSq(XMLoadFloat4(&value.rotation)));
        if (!(std::abs(norm-1)<.0005f && XMVectorGetX(XMVector3LengthSq(XMLoadFloat3(&value.translation)))<400))
            throw std::runtime_error("Invalid transport rigid key.");
        return value;
    };
    for (auto& clip : mTransportClips) {
        const unsigned count=Read<uint32_t>(data,at), frames=Read<uint32_t>(data,at), fps=Read<uint32_t>(data,at);
        if (!count || count>SHIP_POSE_COUNT || frames<2 || frames>1000 || fps!=24)
            throw std::runtime_error("Invalid transport clip size.");
        for (unsigned i=0; i<count; ++i) {
            const unsigned slot=Read<uint32_t>(data,at);
            if (slot<=SHIP_LEGACY_POSES || slot>SHIP_POSE_COUNT || used[slot-1])
                throw std::runtime_error("Invalid transport pose slot.");
            used[slot-1]=true;
            const RigidKey bind=key();
            RigidTrack track{};
            track.slot=slot-1;
            const XMMATRIX rest=XMMatrixRotationQuaternion(XMLoadFloat4(&bind.rotation)) *
                                XMMatrixTranslationFromVector(XMLoadFloat3(&bind.translation));
            XMStoreFloat4x4(&track.inverseBind,XMMatrixInverse(nullptr,rest));
            track.keys.reserve(frames);
            for (unsigned frame=0; frame<frames; ++frame) track.keys.push_back(key());
            clip.push_back(std::move(track));
        }
    }
    for (auto& nozzle : mNozzles) {
        nozzle=Read<Nozzle>(data,at);
        const float image=nozzle.aperture.x;
        const float tiles=nozzle.widthAxis.w;
        if (!((tiles==0 || (tiles>=2 && tiles<=128 && tiles==std::floor(tiles))) &&
              image>=1 && image<=mImages.size() && image==std::floor(image) && !mImages[size_t(image)-1].srgb &&
              nozzle.mouthWidth.w>0 && nozzle.axisHeight.w>0 && nozzle.aperture.y>0 &&
              nozzle.aperture.z>=0 && nozzle.aperture.z<Radius && nozzle.aperture.w>=0 && nozzle.aperture.w<2*Radius))
            throw std::runtime_error("Invalid transport outlet.");
    }
    uint32_t section = Read<uint32_t>(data, at);
    if (section == 0x31534352) { // RCS1, one port-side record per mirrored pair
        if (Read<uint32_t>(data,at) != mPorts.size()) throw std::runtime_error("Invalid transport exhaust layout.");
        for (auto& port : mPorts) {
            port = Read<ExhaustPort>(data,at);
            if (!(port.mouthRadius.x > 0 && port.mouthRadius.w > 0 && port.mouthRadius.w < .5f &&
                  XMVectorGetX(XMVector3Length(XMLoadFloat4(&port.mouthRadius))) < 8 &&
                  std::abs(XMVectorGetX(XMVector3LengthSq(XMLoadFloat4(&port.axis)))-1) < .001f))
                throw std::runtime_error("Invalid transport exhaust port.");
        }
        mProfile.jetCount = 2 + 2 * SHIP_TRANSPORT_PORT_PAIRS;
        section = Read<uint32_t>(data, at);
    }
    if (section != 0x32505553) throw std::runtime_error("Missing transport supports.");
    const unsigned hulls=Read<uint32_t>(data,at);
    if (!hulls || hulls>SHIP_POSE_COUNT+1) throw std::runtime_error("Invalid transport supports.");
    for (unsigned i=0; i<hulls; ++i) {
        SupportHull hull{};
        hull.slot=Read<uint32_t>(data,at);
        const unsigned count=Read<uint32_t>(data,at);
        if (hull.slot>SHIP_POSE_COUNT || !count || count>65536) throw std::runtime_error("Invalid support hull.");
        hull.points.reserve(count);
        for (unsigned j=0;j<count;++j) hull.points.push_back(Read<XMFLOAT3>(data,at));
        mTransportBounds.push_back(std::move(hull));
    }
    ReadPane(data,at);
}

XMMATRIX Ship::TransportMatrix(const RigidTrack& track, double phase)
{
    const size_t last=track.keys.size()-1;
    const double time=std::max(0.0,std::min(1.0,phase))*last;
    const size_t frame=size_t(time);
    const auto& a=track.keys[frame];
    const auto& b=track.keys[std::min(frame+1,last)];
    const float t=float(time-frame);
    const XMVECTOR q=XMQuaternionSlerp(XMLoadFloat4(&a.rotation),XMLoadFloat4(&b.rotation),t);
    const XMVECTOR p=XMVectorLerp(XMLoadFloat3(&a.translation),XMLoadFloat3(&b.translation),t);
    return XMLoadFloat4x4(&track.inverseBind)*XMMatrixRotationQuaternion(q)*XMMatrixTranslationFromVector(p);
}

float Ship::TransportDepth(XMFLOAT3 up, const TransportEquipment& state) const
{
    // Lowest point along local gravity, including the real pad positions throughout retraction.
    const XMVECTOR vertical=XMLoadFloat3(&up);
    std::array<XMMATRIX, SHIP_POSE_COUNT+1> transforms;
    transforms.fill(XMMatrixIdentity());
    for (size_t i=0;i<mTransportClips.size();++i) {
        const double phase=i==TransportEquipment::Gear ? 1-state.position[i] : state.position[i];
        for (const auto& track : mTransportClips[i]) transforms[track.slot+1]=TransportMatrix(track,phase);
    }
    float depth=.2f;
    for (const auto& hull : mTransportBounds) {
        const auto& transform=transforms[hull.slot];
        XMFLOAT3 axis;
        XMStoreFloat3(&axis,XMVector3TransformNormal(vertical,XMMatrixTranspose(transform)));
        const float offset=XMVectorGetX(XMVector3Dot(transform.r[3],vertical));
        for (const auto& p : hull.points)
            depth=std::max(depth,-(axis.x*p.x+axis.y*p.y+axis.z*p.z+offset));
    }
    return depth;
}

void Ship::SetTransportPose(const TransportEquipment& state)
{
    for (size_t i=0; i<mTransportClips.size(); ++i) {
        const double phase=i==TransportEquipment::Gear ? 1-state.position[i] : state.position[i];
        for (const RigidTrack& track : mTransportClips[i]) {
            const XMMATRIX delta=TransportMatrix(track,phase);
            XMStoreFloat4x4(&mConstants->pose[track.slot],XMMatrixTranspose(delta));
        }
    }
}

void Ship::ReadShuttleControls(const std::vector<uint8_t>& data, size_t& at)
{
    // LGR1 stores three legs and closed hull bounds. The flight pack keeps the gear in its closed pose.
    if (Read<uint32_t>(data, at) != 0x3152474cU) throw std::runtime_error("Missing shuttle gear data.");
    struct Gear { float legAngle, doorAngle; XMFLOAT3 sole; };
    for (int i = 0; i < 3; ++i) {
        const Gear leg = Read<Gear>(data, at);
        if (!(leg.legAngle > 0 && leg.legAngle < XM_PI && leg.doorAngle > 0 && leg.doorAngle < XM_PI &&
              XMVectorGetX(XMVector3Length(XMLoadFloat3(&leg.sole))) < Radius))
            throw std::runtime_error("Invalid shuttle gear data.");
    }
    const XMFLOAT3 low = Read<XMFLOAT3>(data, at), high = Read<XMFLOAT3>(data, at);
    if (!(low.x < 0 && low.y < 0 && low.z < 0 && high.x > 0 && high.y > 0 && high.z > 0 &&
          std::max({-low.x, -low.y, -low.z, high.x, high.y, high.z}) <= Radius))
        throw std::runtime_error("Invalid shuttle hull bounds.");

    const uint32_t layout = Read<uint32_t>(data, at);
    const bool fitted = layout == 0x3354454aU; // JET3 fits the emitting gaps and their different depths.
    const bool tilted = fitted || layout == 0x3254454aU; // JET2 adds an authored width axis to JET1.
    if ((!tilted && layout != 0x3154454aU) || Read<uint32_t>(data, at) != _countof(mNozzles))
        throw std::runtime_error("Invalid shuttle exhaust data.");
    for (Nozzle& nozzle : mNozzles) {
        nozzle.mouthWidth = Read<XMFLOAT4>(data, at);
        nozzle.axisHeight = Read<XMFLOAT4>(data, at);
        const XMVECTOR axis = XMLoadFloat4(&nozzle.axisHeight);
        if (!(XMVectorGetX(XMVector3Length(XMLoadFloat4(&nozzle.mouthWidth))) < Radius &&
              std::abs(XMVectorGetX(XMVector3Length(axis)) - 1) < .0001f &&
              nozzle.mouthWidth.w > 0 && nozzle.mouthWidth.w < Radius &&
              nozzle.axisHeight.w > 0 && nozzle.axisHeight.w < Radius))
            throw std::runtime_error("Invalid shuttle exhaust dimensions.");
        if (tilted) {
            nozzle.widthAxis = Read<XMFLOAT4>(data, at);
            const XMVECTOR width = XMLoadFloat4(&nozzle.widthAxis);
            if (!(std::abs(XMVectorGetX(XMVector3Length(width)) - 1) < .0001f &&
                  std::abs(XMVectorGetX(XMVector3Dot(width, axis))) < .0001f))
                throw std::runtime_error("Invalid shuttle exhaust width axis.");
        } else {
            const XMVECTOR pole = std::abs(nozzle.axisHeight.z) < .9f ? g_XMIdentityR2 : g_XMIdentityR0;
            XMStoreFloat4(&nozzle.widthAxis, XMVector3Normalize(XMVector3Cross(axis, pole)));
        }
        nozzle.aperture = {};
        if (fitted) {
            nozzle.aperture = Read<XMFLOAT4>(data, at);
            const float slot = nozzle.aperture.x;
            if (!(slot >= 1 && slot <= float(mImages.size()) && slot == std::floor(slot) &&
                  !mImages[size_t(slot) - 1].srgb && nozzle.aperture.y > 0 && nozzle.aperture.y < Radius))
                throw std::runtime_error("Invalid turbine aperture chart.");
        }
    }
    if (Read<uint32_t>(data, at) != 0x31524854U) throw std::runtime_error("Missing shuttle throttle data.");
    throttleStops = Read<XMFLOAT2>(data, at);
    if (!(throttleStops.x > -XM_PIDIV2 && throttleStops.x < 0 && throttleStops.y > 0 && throttleStops.y < XM_PIDIV2))
        throw std::runtime_error("Invalid shuttle throttle data.");
    if (at == data.size()) return; // The original film packet ends after THR1.

    const uint32_t surfaces = Read<uint32_t>(data, at);
    FlightFittings fit = {};
    if (surfaces == 0x31574c46U) { // FLW1, rigid variable-sweep wings.
        fit = Read<FlightFittings>(data, at);
        if (!(fit.wingPivot.x > 0 && fit.brakePivot.x > fit.wingPivot.x &&
              XMVectorGetX(XMVector3Length(XMLoadFloat3(&fit.wingPivot))) < Radius &&
              fit.foldedAngle > 0 && fit.foldedAngle < XM_PIDIV2))
            throw std::runtime_error("Invalid shuttle wing pivot.");
    } else if (surfaces == 0x32574c46U) { // FLW2, the original nacelle skin extends transversely.
        fit.brakePivot = Read<XMFLOAT3>(data, at);
        fit.brakeAngle = Read<float>(data, at);
        fit.brakeAxis = Read<XMFLOAT3>(data, at);
        ReadLipTravel(data, at);
    } else {
        throw std::runtime_error("Unknown flight-surface trailer.");
    }
    if (!(fit.brakePivot.x > 0 && XMVectorGetX(XMVector3Length(XMLoadFloat3(&fit.brakePivot))) < Radius &&
          fit.brakeAngle > 0 && fit.brakeAngle < XM_PIDIV2 &&
          std::abs(XMVectorGetX(XMVector3Length(XMLoadFloat3(&fit.brakeAxis))) - 1.0f) < 1.e-4f))
        throw std::runtime_error("Invalid fitted brake hinge.");
    mFlightFittings = fit;
    if (at == data.size()) return;

    ReadPane(data, at);
}

void Ship::ReadPane(const std::vector<uint8_t>& data, size_t& at)
{
    constexpr size_t samples = SHUTTLE_PANE_COLUMNS * SHUTTLE_PANE_ROWS;
    constexpr size_t bytes = samples * sizeof(XMFLOAT4);
    if (Read<uint32_t>(data, at) != 0x31525457U || data.size() - at != bytes)
        throw std::runtime_error("Invalid shuttle canopy chart.");
    mFittedPane.resize(samples);
    std::memcpy(mFittedPane.data(), data.data() + at, bytes);
    at += bytes;
    for (const XMFLOAT4& sample : mFittedPane) {
        const float radius = XMVectorGetX(XMVector3Length(XMLoadFloat4(&sample)));
        if (!(radius > .15f && radius < Radius + 1 && std::abs(sample.w) < 8.0f))
            throw std::runtime_error("Invalid shuttle canopy sample.");
    }
    // The last row stores the actual lower glass edge at each azimuth, in chart metres.
    // Extend the end of the rail through columns beyond the aperture.
    std::vector<XMFLOAT4> rail(SHUTTLE_PANE_COLUMNS);
    int first = -1, last = -1;
    for (int x = 0; x < SHUTTLE_PANE_COLUMNS; ++x) {
        for (int y = 1; y < SHUTTLE_PANE_ROWS; ++y) {
            const float below = mFittedPane[(y - 1) * SHUTTLE_PANE_COLUMNS + x].w;
            const float above = mFittedPane[y * SHUTTLE_PANE_COLUMNS + x].w;
            if (below > 0 || above <= 0) continue;
            const float row = y - 1 + below / (below - above);
            const float chartX = (float(x) / (SHUTTLE_PANE_COLUMNS - 1) - .5f) * SHUTTLE_WATER_WIDTH * SHUTTLE_WATER_TEXEL;
            const float chartY = SHUTTLE_WATER_Y + row * SHUTTLE_WATER_HEIGHT * SHUTTLE_WATER_TEXEL / (SHUTTLE_PANE_ROWS - 1);
            rail[x] = {chartX, chartY, 0, 0};
            if (first < 0) first = x;
            for (int j = last + 1; j < x; ++j) rail[j] = last < 0 ? rail[x] : rail[last];
            last = x;
            break;
        }
    }
    if (first < 0) throw std::runtime_error("No lower edge in the fitted canopy chart.");
    std::fill(rail.begin() + last + 1, rail.end(), rail[last]);
    mFittedPane.insert(mFittedPane.end(), rail.begin(), rail.end());
    mProfile.water = { SHUTTLE_WATER_WIDTH, SHUTTLE_WATER_HEIGHT, SHUTTLE_WATER_Y, SHUTTLE_WATER_TEXEL };
}

void Ship::ReadLipTravel(const std::vector<uint8_t>& data, size_t& at)
{
    const uint32_t count = Read<uint32_t>(data, at);
    const size_t vertices = mVertexBytes.size() / 60;
    if (!count || count > vertices || count > (1u << 24) ||
        (data.size() - at) / (sizeof(uint32_t) + sizeof(XMFLOAT4)) < count)
        throw std::runtime_error("Invalid nacelle travel count.");
    mLipTravel.resize(count);
    for (uint32_t i = 0; i < count; ++i) {
        const uint32_t id = Read<uint32_t>(data, at);
        const auto v = Read<XMFLOAT4>(data, at);
        if (!(id < vertices && std::abs(v.x) < Radius && v.y >= -.001f &&
              std::isfinite(v.y) && std::isfinite(v.z) && std::isfinite(v.w)))
            throw std::runtime_error("Invalid nacelle displacement.");
        uint8_t* poseBytes = mVertexBytes.data() + size_t(id) * 60 + 56;
        float pose;
        std::memcpy(&pose, poseBytes, sizeof(pose));
        if (pose != 0.0f) throw std::runtime_error("Nacelle travel must reference a unique fixed vertex.");
        // Only the GPU copy uses negative pose indices. The packed rest mesh
        // keeps its original rig, including its separate brake hinge poses.
        pose = -float(i+1);
        std::memcpy(poseBytes, &pose, sizeof(pose));
        mLipTravel[i] = v;
    }
}

// Fit the panoramic field to the loaded chrome mesh, once. Each ray meets the tangent
// plane at its closest sampled vertex. Four intervals per cabin sector and fine
// elevation samples follow the raised equatorial rib between the seal and crown.
void Ship::FitFieldToHull(FieldRadii& radius) const
{
    XMVECTOR rays[SHIP_FIELD_COLUMNS][SHIP_FIELD_ROWS];
    float nearest[SHIP_FIELD_COLUMNS][SHIP_FIELD_ROWS] = {};
    for (int col = 0; col < SHIP_FIELD_COLUMNS; ++col) {
        const float azimuth = SHIP_FIELD_HALF_ANGLE * (2.0f * col / (SHIP_FIELD_COLUMNS - 1) - 1.0f);
        for (int row = 0; row < SHIP_FIELD_ROWS; ++row) {
            const float elevation = SHIP_FIELD_FLOOR + row * SHIP_FIELD_ELEVATION_STEP;
            rays[col][row] = XMVectorSet(std::sin(azimuth) * std::cos(elevation), -std::cos(azimuth) * std::cos(elevation),
                                         std::sin(elevation), 0.0f);
        }
    }
    std::vector<bool> visited(mVertexBytes.size() / 60);
    for (const Draw& draw : mDraws) {
        if (mRoles[draw.material] != 10) continue;
        for (uint32_t i = draw.first; i < draw.first + draw.count; ++i) {
            const uint32_t id = mIndices[i];
            if (visited[id]) continue;
            visited[id] = true;
            const uint8_t* vertex = mVertexBytes.data() + size_t(id) * 60;
            XMFLOAT3 position, normal;
            std::memcpy(&position, vertex, sizeof(position));
            if (position.y >= 0.0f) continue;
            const float azimuth = std::atan2(position.x, -position.y);
            const int mapped = int(std::lround((azimuth / SHIP_FIELD_HALF_ANGLE + 1.0f) * (SHIP_FIELD_COLUMNS - 1) * 0.5f));
            const int col = std::max(0, std::min(mapped, SHIP_FIELD_COLUMNS - 1));
            const float elevation = std::atan2(position.z, std::sqrt(position.x * position.x + position.y * position.y));
            const int band = int(std::lround((elevation - SHIP_FIELD_FLOOR) / SHIP_FIELD_ELEVATION_STEP));
            std::memcpy(&normal, vertex + sizeof(position), sizeof(normal));
            const XMVECTOR p = XMLoadFloat3(&position), n = XMLoadFloat3(&normal), dir = XMVector3Normalize(p);
            for (int row = std::max(0, band - 1); row <= std::min(band + 1, SHIP_FIELD_ROWS - 1); ++row) {
                const XMVECTOR ray = rays[col][row];
                const float alignment = XMVectorGetX(XMVector3Dot(dir, ray));
                if (alignment <= nearest[col][row]) continue;
                const float incidence = XMVectorGetX(XMVector3Dot(n, ray));
                if (std::fabs(incidence) < 0.10f) continue;
                const float distance = XMVectorGetX(XMVector3Dot(p, n)) / incidence;
                if (distance <= 0.0f) continue;
                nearest[col][row] = alignment;
                radius[col][row] = distance;
            }
        }
    }
}

D3D12_CPU_DESCRIPTOR_HANDLE Ship::Cpu(UINT i) const
{
    D3D12_CPU_DESCRIPTOR_HANDLE h = mHeap->GetCPUDescriptorHandleForHeapStart();
    h.ptr += SIZE_T(mBase + i) * mStride;
    return h;
}

D3D12_GPU_DESCRIPTOR_HANDLE Ship::Gpu(UINT i) const
{
    D3D12_GPU_DESCRIPTOR_HANDLE h = mHeap->GetGPUDescriptorHandleForHeapStart();
    h.ptr += UINT64(mBase + i) * mStride;
    return h;
}

void Ship::Initialize(ID3D12Device* device, ID3D12GraphicsCommandList* list, ID3D12DescriptorHeap* srvHeap, UINT descriptorBase,
                      UINT width, UINT height, DXGI_FORMAT hdrFormat, DXGI_FORMAT sunFormat, ID3D12Resource* sceneDepth)
{
    mHeap = srvHeap;
    mBase = descriptorBase;
    mStride = device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);

    // The overlay: cleared to "no glass", alpha 1, every frame.
    {
        const float none[4] = { 0.0f, 0.0f, 0.0f, 1.0f };
        const CD3DX12_CLEAR_VALUE clear(OverlayFormat, none);
        const CD3DX12_HEAP_PROPERTIES heap(D3D12_HEAP_TYPE_DEFAULT);
        const auto desc = CD3DX12_RESOURCE_DESC::Tex2D(OverlayFormat, width, height, 1, 1, 1, 0, D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET);
        Check(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_RENDER_TARGET, &clear,
                                              IID_PPV_ARGS(&mOverlay)), "Ship overlay creation failed.");
        D3D12_DESCRIPTOR_HEAP_DESC rtv = { D3D12_DESCRIPTOR_HEAP_TYPE_RTV, 1, D3D12_DESCRIPTOR_HEAP_FLAG_NONE, 0 };
        Check(device->CreateDescriptorHeap(&rtv, IID_PPV_ARGS(&mRtvHeap)), "Ship RTV heap creation failed.");
        device->CreateRenderTargetView(mOverlay.Get(), nullptr, mRtvHeap->GetCPUDescriptorHandleForHeapStart());
        device->CreateShaderResourceView(mOverlay.Get(), nullptr, Cpu(MaxImages + 2));
    }
    if (!mLoaded) return;

    // The pack's buffers, through upload buffers kept until the initialisation's list has run.
    auto upload = [&](const void* bytes, size_t size, Resource& target, D3D12_RESOURCE_FLAGS flags = D3D12_RESOURCE_FLAG_NONE) {
        target = CreateBuffer(device, size, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COPY_DEST, flags);
        mUploads.push_back(CreateBuffer(device, size, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ));
        void* mapped = nullptr;
        const CD3DX12_RANGE noRead(0, 0);
        Check(mUploads.back()->Map(0, &noRead, &mapped), "Ship upload map failed.");
        std::memcpy(mapped, bytes, size);
        mUploads.back()->Unmap(0, nullptr);
        list->CopyResource(target.Get(), mUploads.back().Get());
    };
    // Use an explicitly addressed read-only buffer for the fit. A dynamic subscript
    // into a large cbuffer can otherwise expand into a very large driver shader.
    FieldRadii field = {};
    if (mProfile.sceneReflections) FitFieldToHull(field);
    upload(field, sizeof(field), mFieldRadii);
    if (mFittedPane.empty()) {
        const XMFLOAT4 unused = {0, 0, 1, -1};
        upload(&unused, sizeof(unused), mPaneChart);
    } else {
        upload(mFittedPane.data(), mFittedPane.size() * sizeof(XMFLOAT4), mPaneChart);
    }
    const XMFLOAT4 noTravel = {};
    if (mLipTravel.empty()) upload(&noTravel, sizeof(noTravel), mLipBuffer);
    else upload(mLipTravel.data(), mLipTravel.size() * sizeof(XMFLOAT4), mLipBuffer);
    const XMFLOAT4 shockBounds = CreateShockHull(device, list);
    BuildFlightSurfaces();
    upload(mVertexBytes.data(), mVertexBytes.size(), mVertices);
    upload(mIndices.data(), mIndices.size() * 4, mIndexBuffer);
    upload(mMaterialBytes.data(), mMaterialBytes.size(), mMaterials);
    mSceneDepth = sceneDepth;
    D3D12_SHADER_RESOURCE_VIEW_DESC depthView = {};
    depthView.Format = DXGI_FORMAT_R32_FLOAT;
    depthView.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
    depthView.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    depthView.Texture2D.MipLevels = 1;
    device->CreateShaderResourceView(sceneDepth, &depthView, Cpu(MaxImages + 11));
    // Two more float4 slots contain the indirect particle and atlas Dispatch arguments.
    const float clearWeather[20] = {0,0,0,0, 0,0,0,0, 0,1,1,0};
    upload(clearWeather, sizeof(clearWeather), mWeather, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mIndexView = { mIndexBuffer->GetGPUVirtualAddress(), UINT(mIndices.size() * 4), DXGI_FORMAT_R32_UINT };

    // The images, with their mips; colour and emission in sRGB, the others as data.
    ComPtr<IWICImagingFactory> factory;
    CoInitializeEx(nullptr, COINIT_MULTITHREADED); // S_FALSE or RPC_E_CHANGED_MODE when COM is already on: fine
    Check(CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&factory)), "WIC factory failed.");
    std::vector<CD3DX12_RESOURCE_BARRIER> toRead;
    for (size_t i = 0; i < mImages.size(); ++i) {
        UINT w = 0, h = 0;
        std::vector<uint8_t> level;
        DecodePng(factory.Get(), mImages[i].png, w, h, level);
        UINT mips = 1;
        while ((std::max(w, h) >> mips) > 0) ++mips;
        const DXGI_FORMAT format = mImages[i].srgb ? DXGI_FORMAT_R8G8B8A8_UNORM_SRGB : DXGI_FORMAT_R8G8B8A8_UNORM;
        const auto desc = CD3DX12_RESOURCE_DESC::Tex2D(format, w, h, 1, UINT16(mips));
        const CD3DX12_HEAP_PROPERTIES heap(D3D12_HEAP_TYPE_DEFAULT);
        Check(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_COPY_DEST, nullptr,
                                              IID_PPV_ARGS(&mTextures[i])), "Ship texture creation failed.");
        std::vector<D3D12_PLACED_SUBRESOURCE_FOOTPRINT> footprints(mips);
        std::vector<UINT> rows(mips);
        std::vector<UINT64> rowBytes(mips);
        UINT64 total = 0;
        device->GetCopyableFootprints(&desc, 0, mips, 0, footprints.data(), rows.data(), rowBytes.data(), &total);
        mUploads.push_back(CreateBuffer(device, total, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ));
        uint8_t* mapped = nullptr;
        const CD3DX12_RANGE noRead(0, 0);
        Check(mUploads.back()->Map(0, &noRead, reinterpret_cast<void**>(&mapped)), "Ship texture upload map failed.");
        UINT lw = w, lh = h;
        for (UINT m = 0; m < mips; ++m) {
            for (UINT y = 0; y < rows[m]; ++y)
                std::memcpy(mapped + footprints[m].Offset + size_t(y) * footprints[m].Footprint.RowPitch,
                            level.data() + size_t(y) * lw * 4, size_t(lw) * 4);
            const CD3DX12_TEXTURE_COPY_LOCATION to(mTextures[i].Get(), m), from(mUploads.back().Get(), footprints[m]);
            list->CopyTextureRegion(&to, 0, 0, 0, &from, nullptr);
            if (m + 1 < mips) { level = HalfImage(level, lw, lh); lw = std::max(lw / 2, 1u); lh = std::max(lh / 2, 1u); }
        }
        mUploads.back()->Unmap(0, nullptr);
        device->CreateShaderResourceView(mTextures[i].Get(), nullptr, Cpu(UINT(i)));
        toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mTextures[i].Get(), D3D12_RESOURCE_STATE_COPY_DEST,
                                                              D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE));
    }
    // Unused image slots still need a valid view: the first image again.
    D3D12_SHADER_RESOURCE_VIEW_DESC nullImage = {};
    nullImage.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    nullImage.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
    nullImage.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    nullImage.Texture2D.MipLevels = 1;
    for (size_t i = mImages.size(); i < MaxImages; ++i)
        device->CreateShaderResourceView(mTextures[0].Get(), mImages.empty() ? &nullImage : nullptr, Cpu(UINT(i)));
    const D3D12_RESOURCE_STATES readable = D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE;
    toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mVertices.Get(), D3D12_RESOURCE_STATE_COPY_DEST, readable));
    toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mIndexBuffer.Get(), D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_INDEX_BUFFER));
    toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mMaterials.Get(), D3D12_RESOURCE_STATE_COPY_DEST, readable));
    toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mFieldRadii.Get(), D3D12_RESOURCE_STATE_COPY_DEST, readable));
    toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mPaneChart.Get(), D3D12_RESOURCE_STATE_COPY_DEST, readable));
    toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mLipBuffer.Get(), D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE));
    toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mShockHull.Get(), D3D12_RESOURCE_STATE_COPY_DEST, readable));
    // The opaque pass already reads last frame's weather, including on the first draw.
    toRead.push_back(CD3DX12_RESOURCE_BARRIER::Transition(mWeather.Get(), D3D12_RESOURCE_STATE_COPY_DEST,
                                                          readable | D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT));
    list->ResourceBarrier(UINT(toRead.size()), toRead.data());

    // The canopy's water: its drops and their merges, zero (no drop alive), and its map and film, written by the compute
    // passes, read by the glass.
    {
        const D3D12_RESOURCE_FLAGS uav = D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS;
        mDrops = CreateBuffer(device, DropCount * 32, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COMMON, uav);
        // The last word reports any surviving drop to the following weather dispatch.
        mGathered = CreateBuffer(device, (DropCount + 1) * 4, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COMMON, uav);
        const CD3DX12_HEAP_PROPERTIES heap(D3D12_HEAP_TYPE_DEFAULT);
        const DXGI_FORMAT formats[2] = { DXGI_FORMAT_R32_UINT, DXGI_FORMAT_R32_FLOAT };
        Resource* maps[2] = { &mWaterMap, &mWaterFilm };
        for (UINT k = 0; k < 2; ++k) {
            const auto desc = CD3DX12_RESOURCE_DESC::Tex2D(formats[k], mProfile.water.width, mProfile.water.height, 1, 1, 1, 0, uav);
            Check(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                                                  nullptr, IID_PPV_ARGS(maps[k]->ReleaseAndGetAddressOf())), "Ship water map creation failed.");
            device->CreateUnorderedAccessView(maps[k]->Get(), nullptr, nullptr, Cpu(MaxImages + 4 + k));
            device->CreateShaderResourceView(maps[k]->Get(), nullptr, Cpu(MaxImages + 7 + k));
        }
        D3D12_UNORDERED_ACCESS_VIEW_DESC buffer = {};
        buffer.Format = DXGI_FORMAT_UNKNOWN;
        buffer.ViewDimension = D3D12_UAV_DIMENSION_BUFFER;
        buffer.Buffer.NumElements = DropCount;
        buffer.Buffer.StructureByteStride = 32;
        device->CreateUnorderedAccessView(mDrops.Get(), nullptr, &buffer, Cpu(MaxImages + 3));
        buffer.Buffer.StructureByteStride = 4;
        buffer.Buffer.NumElements = DropCount + 1;
        device->CreateUnorderedAccessView(mGathered.Get(), nullptr, &buffer, Cpu(MaxImages + 6));
    }

    // The two shadow maps: depth, read as floats.
    D3D12_DESCRIPTOR_HEAP_DESC dsv = { D3D12_DESCRIPTOR_HEAP_TYPE_DSV, 2, D3D12_DESCRIPTOR_HEAP_FLAG_NONE, 0 };
    Check(device->CreateDescriptorHeap(&dsv, IID_PPV_ARGS(&mDsvHeap)), "Ship DSV heap creation failed.");
    mDsvStride = device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_DSV);
    for (UINT k = 0; k < 2; ++k) {
        const CD3DX12_CLEAR_VALUE clear(DXGI_FORMAT_D32_FLOAT, 1.0f, 0);
        const CD3DX12_HEAP_PROPERTIES heap(D3D12_HEAP_TYPE_DEFAULT);
        const auto desc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R32_TYPELESS, ShadowSize, ShadowSize, 1, 1, 1, 0,
                                                       D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL);
        Check(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_DEPTH_WRITE, &clear,
                                              IID_PPV_ARGS(&mShadowMaps[k])), "Ship shadow map creation failed.");
        D3D12_DEPTH_STENCIL_VIEW_DESC view = {};
        view.Format = DXGI_FORMAT_D32_FLOAT;
        view.ViewDimension = D3D12_DSV_DIMENSION_TEXTURE2D;
        D3D12_CPU_DESCRIPTOR_HANDLE h = mDsvHeap->GetCPUDescriptorHandleForHeapStart();
        h.ptr += SIZE_T(k) * mDsvStride;
        device->CreateDepthStencilView(mShadowMaps[k].Get(), &view, h);
        D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
        srv.Format = DXGI_FORMAT_R32_FLOAT;
        srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
        srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        srv.Texture2D.MipLevels = 1;
        device->CreateShaderResourceView(mShadowMaps[k].Get(), &srv, Cpu(MaxImages + k));
    }

    mConstantsBuffer = CreateBuffer(device, (sizeof(Constants) + 255) & ~255u, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
    const CD3DX12_RANGE noRead(0, 0);
    Check(mConstantsBuffer->Map(0, &noRead, reinterpret_cast<void**>(&mConstants)), "Ship constants map failed.");
    *mConstants = {};
    mConstants->shockBounds = shockBounds;
    mConstants->options.z = float(mProfile.model);
    mConstants->waterLayout = { float(mProfile.water.width), float(mProfile.water.height), mProfile.water.originY, mProfile.water.texel };
    const auto& surfaces = mProfile.surfaces;
    mConstants->retroOutlet = { surfaces.retroX, surfaces.retroY, surfaces.retroZ, 0 };
    mConstants->supportOutlet = { surfaces.supportX, surfaces.supportY, surfaces.supportZ, surfaces.supportSpacing };
    std::copy_n(mNozzles, _countof(mNozzles), mConstants->nozzles);
    std::copy(mPorts.begin(), mPorts.end(), mConstants->ports);
    for (auto& pose : mConstants->pose) XMStoreFloat4x4(&pose, XMMatrixIdentity());

    // One root signature for every pass: frame constants (b0), the ship's (b3), the draw's (b2), its vertices and
    // materials, the atmosphere tables, the climate map, the planet map, the images and shadow maps, the weather state,
    // the composite image for the glass's refraction, the clouds' frame (b1) and textures, for the weather, then the
    // water's UAVs (u1-u4) and its map and film for the glass (t48, t49), and the terrain's mesh for the weather (t50).
    CD3DX12_DESCRIPTOR_RANGE luts(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 3, 1), climate(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 10),
        planetMap(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 29),
        composite(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 47), planet(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 4, 24),
        water(D3D12_DESCRIPTOR_RANGE_TYPE_UAV, 4, 1), waterRead(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 2, 48);
    CD3DX12_DESCRIPTOR_RANGE shockHull(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 52), sceneDepthRead(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 53);
    const CD3DX12_DESCRIPTOR_RANGE images[] = {
        CD3DX12_DESCRIPTOR_RANGE(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, MaxImages, 64),
        CD3DX12_DESCRIPTOR_RANGE(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 2, 44)
    };
    CD3DX12_ROOT_PARAMETER params[22];
    params[0].InitAsConstantBufferView(0);
    params[1].InitAsConstantBufferView(3);
    params[2].InitAsConstants(4, 2);
    params[3].InitAsShaderResourceView(30);
    params[4].InitAsShaderResourceView(31);
    params[5].InitAsDescriptorTable(1, &luts);
    params[6].InitAsDescriptorTable(1, &climate);
    params[7].InitAsDescriptorTable(1, &planetMap);
    params[8].InitAsDescriptorTable(_countof(images), images);
    params[9].InitAsShaderResourceView(46);
    params[10].InitAsUnorderedAccessView(0);
    params[11].InitAsDescriptorTable(1, &composite);
    params[12].InitAsConstantBufferView(1);
    params[13].InitAsDescriptorTable(1, &planet);
    params[14].InitAsDescriptorTable(1, &water);
    params[15].InitAsDescriptorTable(1, &waterRead);
    params[16].InitAsShaderResourceView(50);
    params[17].InitAsShaderResourceView(51);
    params[18].InitAsDescriptorTable(1, &shockHull);
    params[19].InitAsDescriptorTable(1, &sceneDepthRead, D3D12_SHADER_VISIBILITY_PIXEL);
    params[20].InitAsShaderResourceView(54);
    params[21].InitAsShaderResourceView(55, 0, D3D12_SHADER_VISIBILITY_VERTEX);
    CD3DX12_STATIC_SAMPLER_DESC samplers[6] = {
        CD3DX12_STATIC_SAMPLER_DESC(0, D3D12_FILTER_MIN_MAG_MIP_LINEAR, D3D12_TEXTURE_ADDRESS_MODE_CLAMP,
                                    D3D12_TEXTURE_ADDRESS_MODE_CLAMP, D3D12_TEXTURE_ADDRESS_MODE_CLAMP),
        CD3DX12_STATIC_SAMPLER_DESC(1, D3D12_FILTER_ANISOTROPIC),
        CD3DX12_STATIC_SAMPLER_DESC(4, D3D12_FILTER_COMPARISON_MIN_MAG_LINEAR_MIP_POINT, D3D12_TEXTURE_ADDRESS_MODE_CLAMP,
                                    D3D12_TEXTURE_ADDRESS_MODE_CLAMP, D3D12_TEXTURE_ADDRESS_MODE_CLAMP, 0.0f, 1,
                                    D3D12_COMPARISON_FUNC_LESS_EQUAL),
        CD3DX12_STATIC_SAMPLER_DESC(5, D3D12_FILTER_ANISOTROPIC),
        CD3DX12_STATIC_SAMPLER_DESC(2, D3D12_FILTER_MIN_MAG_MIP_LINEAR), // the clouds' noise, wrapping
        CD3DX12_STATIC_SAMPLER_DESC(3, D3D12_FILTER_MIN_MAG_MIP_LINEAR, D3D12_TEXTURE_ADDRESS_MODE_WRAP, // their weather map
                                    D3D12_TEXTURE_ADDRESS_MODE_CLAMP, D3D12_TEXTURE_ADDRESS_MODE_CLAMP) };
    mRoot = CreateRootSignature(device, CD3DX12_ROOT_SIGNATURE_DESC(_countof(params), params, 6, samplers));

    const ComPtr<ID3DBlob> vs = LoadShader(L"ShipVertex.cso"), shadowVs = LoadShader(L"ShipShadow.cso"),
        ps = LoadShader(L"ShipPixel.cso"), glassPs = LoadShader(L"ShipGlass.cso"), weatherCs = LoadShader(L"ShipWeather.cso");
    D3D12_GRAPHICS_PIPELINE_STATE_DESC desc = {};
    desc.pRootSignature = mRoot.Get();
    desc.VS = CD3DX12_SHADER_BYTECODE(vs.Get());
    desc.PS = CD3DX12_SHADER_BYTECODE(ps.Get());
    desc.RasterizerState = CD3DX12_RASTERIZER_DESC(D3D12_DEFAULT);
    desc.RasterizerState.CullMode = D3D12_CULL_MODE_NONE;
    desc.BlendState = CD3DX12_BLEND_DESC(D3D12_DEFAULT);
    desc.DepthStencilState = CD3DX12_DEPTH_STENCIL_DESC(D3D12_DEFAULT);
    desc.DepthStencilState.DepthFunc = D3D12_COMPARISON_FUNC_GREATER; // reversed Z, as the scene
    desc.SampleMask = UINT_MAX;
    desc.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
    desc.NumRenderTargets = 2;
    desc.RTVFormats[0] = hdrFormat;
    desc.RTVFormats[1] = sunFormat;
    desc.DSVFormat = DXGI_FORMAT_D32_FLOAT;
    desc.SampleDesc.Count = 1;
    Check(device->CreateGraphicsPipelineState(&desc, IID_PPV_ARGS(&mOpaquePSO)), "Ship PSO creation failed.");

    // Reflective opaque skins read the complete world, then write their own overlay and the scene depth.
    const ComPtr<ID3DBlob> reflectionPs = LoadShader(L"ShipReflection.cso");
    D3D12_GRAPHICS_PIPELINE_STATE_DESC reflection = desc;
    reflection.PS = CD3DX12_SHADER_BYTECODE(reflectionPs.Get());
    reflection.NumRenderTargets = 1;
    reflection.RTVFormats[0] = OverlayFormat;
    reflection.RTVFormats[1] = DXGI_FORMAT_UNKNOWN;
    Check(device->CreateGraphicsPipelineState(&reflection, IID_PPV_ARGS(&mReflectionPSO)), "Ship reflection PSO creation failed.");

    // The shadow maps: standard Z, nearer is smaller, a slope-scaled bias against acne.
    D3D12_GRAPHICS_PIPELINE_STATE_DESC shadow = desc;
    shadow.VS = CD3DX12_SHADER_BYTECODE(shadowVs.Get());
    shadow.PS = {};
    shadow.NumRenderTargets = 0;
    shadow.RTVFormats[0] = shadow.RTVFormats[1] = DXGI_FORMAT_UNKNOWN;
    shadow.DepthStencilState.DepthFunc = D3D12_COMPARISON_FUNC_LESS;
    shadow.RasterizerState.DepthBias = 200;
    shadow.RasterizerState.SlopeScaledDepthBias = 2.0f;
    Check(device->CreateGraphicsPipelineState(&shadow, IID_PPV_ARGS(&mShadowPSO)), "Ship shadow PSO creation failed.");
    if (mProfile.model == ShipModel::Navette) {
        const auto mask = LoadShader(L"ShipShadowMask.cso");
        shadow.PS = CD3DX12_SHADER_BYTECODE(mask.Get());
        Check(device->CreateGraphicsPipelineState(&shadow, IID_PPV_ARGS(&mMaskedShadowPSO)), "Ship masked shadow PSO creation failed.");
    }

    // The glass: screen = smoothed * alpha + rgb, layer after layer, depth tested against the scene, not written.
    D3D12_GRAPHICS_PIPELINE_STATE_DESC glass = desc;
    glass.PS = CD3DX12_SHADER_BYTECODE(glassPs.Get());
    glass.NumRenderTargets = 1;
    glass.RTVFormats[0] = OverlayFormat;
    glass.RTVFormats[1] = DXGI_FORMAT_UNKNOWN;
    glass.DepthStencilState.DepthWriteMask = D3D12_DEPTH_WRITE_MASK_ZERO;
    D3D12_RENDER_TARGET_BLEND_DESC& blend = glass.BlendState.RenderTarget[0];
    blend.BlendEnable = TRUE;
    blend.SrcBlend = D3D12_BLEND_ONE;
    blend.DestBlend = D3D12_BLEND_SRC_ALPHA;
    blend.BlendOp = D3D12_BLEND_OP_ADD;
    blend.SrcBlendAlpha = D3D12_BLEND_ZERO;
    blend.DestBlendAlpha = D3D12_BLEND_SRC_ALPHA;
    blend.BlendOpAlpha = D3D12_BLEND_OP_ADD;
    Check(device->CreateGraphicsPipelineState(&glass, IID_PPV_ARGS(&mGlassPSO)), "Ship glass PSO creation failed.");

    const ComPtr<ID3DBlob> entryVs = LoadShader(L"ShipEntryParticleVertex.cso"), entryPs = LoadShader(L"ShipEntryParticlePixel.cso");
    D3D12_GRAPHICS_PIPELINE_STATE_DESC entry = glass;
    entry.VS = CD3DX12_SHADER_BYTECODE(entryVs.Get());
    entry.PS = CD3DX12_SHADER_BYTECODE(entryPs.Get());
    Check(device->CreateGraphicsPipelineState(&entry, IID_PPV_ARGS(&mEntryParticlesPSO)), "Ship entry particle PSO creation failed.");

    // Jets and entry gas march through boxes up to the opaque surface read as an SRV.
    const ComPtr<ID3DBlob> plumeVs = LoadShader(L"ShipPlumeVertex.cso"), plumePs = LoadShader(L"ShipPlumePixel.cso");
    D3D12_GRAPHICS_PIPELINE_STATE_DESC plume = glass;
    plume.VS = CD3DX12_SHADER_BYTECODE(plumeVs.Get());
    plume.PS = CD3DX12_SHADER_BYTECODE(plumePs.Get());
    plume.DepthStencilState.DepthEnable = FALSE;
    plume.DSVFormat = DXGI_FORMAT_UNKNOWN;
    Check(device->CreateGraphicsPipelineState(&plume, IID_PPV_ARGS(&mPlumePSO)), "Ship plume PSO creation failed.");

    const ComPtr<ID3DBlob> volumeVs = LoadShader(L"ShipEntryVolumeVertex.cso"), volumePs = LoadShader(L"ShipEntryVolumePixel.cso");
    D3D12_GRAPHICS_PIPELINE_STATE_DESC volume = plume;
    volume.VS = CD3DX12_SHADER_BYTECODE(volumeVs.Get());
    volume.PS = CD3DX12_SHADER_BYTECODE(volumePs.Get());
    volume.DSVFormat = DXGI_FORMAT_UNKNOWN; // read the physical depth as an SRV, including the Navigator's late hull
    volume.BlendState.RenderTarget[0].DestBlend = D3D12_BLEND_SRC1_ALPHA;
    Check(device->CreateGraphicsPipelineState(&volume, IID_PPV_ARGS(&mEntryVolumePSO)), "Ship entry volume PSO creation failed.");

    D3D12_COMPUTE_PIPELINE_STATE_DESC compute = {};
    compute.pRootSignature = mRoot.Get();
    compute.CS = CD3DX12_SHADER_BYTECODE(weatherCs.Get());
    Check(device->CreateComputePipelineState(&compute, IID_PPV_ARGS(&mWeatherPSO)), "Ship weather PSO creation failed.");
    const wchar_t* waterShaders[3] = { L"ShipWaterMove.cso", L"ShipWaterClear.cso", L"ShipWaterSplat.cso" };
    for (UINT k = 0; k < 3; ++k) {
        const ComPtr<ID3DBlob> cs = LoadShader(waterShaders[k]);
        compute.CS = CD3DX12_SHADER_BYTECODE(cs.Get());
        Check(device->CreateComputePipelineState(&compute, IID_PPV_ARGS(&mWaterPSO[k])), "Ship water PSO creation failed.");
    }
    mReady = true;
}

void Ship::SetLights(const XMFLOAT3& sun, const XMFLOAT3& up)
{
    XMStoreFloat4x4(&mConstants->shadow[0], XMMatrixTranspose(LightFrame(sun, mProfile, EnvelopeRadius())));
    XMStoreFloat4x4(&mConstants->shadow[1], XMMatrixTranspose(LightFrame(up, mProfile, EnvelopeRadius())));
}

void Ship::Bind(ID3D12GraphicsCommandList* list, const Tables& t, bool compute) const
{
    if (compute) {
        list->SetComputeRootSignature(mRoot.Get());
        list->SetComputeRootConstantBufferView(0, t.frame);
        list->SetComputeRootConstantBufferView(1, mConstantsBuffer->GetGPUVirtualAddress());
        list->SetComputeRootShaderResourceView(3, mVertices->GetGPUVirtualAddress());
        list->SetComputeRootShaderResourceView(4, mMaterials->GetGPUVirtualAddress());
        list->SetComputeRootDescriptorTable(5, t.luts);
        list->SetComputeRootDescriptorTable(6, Gpu(MaxImages + 9));
        list->SetComputeRootDescriptorTable(7, t.planetMap);
        list->SetComputeRootDescriptorTable(8, Gpu(0));
        list->SetComputeRootUnorderedAccessView(10, mWeather->GetGPUVirtualAddress());
        list->SetComputeRootDescriptorTable(11, t.composite);
        list->SetComputeRootShaderResourceView(16, t.terrain);
        list->SetComputeRootShaderResourceView(20, mPaneChart->GetGPUVirtualAddress());
        list->SetComputeRootConstantBufferView(12, t.cloudFrame);
        list->SetComputeRootDescriptorTable(13, t.cloudTextures);
        return;
    }
    list->SetGraphicsRootSignature(mRoot.Get());
    list->SetGraphicsRootConstantBufferView(0, t.frame);
    list->SetGraphicsRootConstantBufferView(1, mConstantsBuffer->GetGPUVirtualAddress());
    list->SetGraphicsRootShaderResourceView(3, mVertices->GetGPUVirtualAddress());
    list->SetGraphicsRootShaderResourceView(4, mMaterials->GetGPUVirtualAddress());
    list->SetGraphicsRootDescriptorTable(5, t.luts);
    list->SetGraphicsRootDescriptorTable(6, Gpu(MaxImages + 9));
    list->SetGraphicsRootDescriptorTable(7, t.planetMap);
    list->SetGraphicsRootDescriptorTable(8, Gpu(0));
    list->SetGraphicsRootShaderResourceView(9, mWeather->GetGPUVirtualAddress());
    list->SetGraphicsRootShaderResourceView(17, mFieldRadii->GetGPUVirtualAddress());
    list->SetGraphicsRootShaderResourceView(20, mPaneChart->GetGPUVirtualAddress());
    list->SetGraphicsRootShaderResourceView(21, mLipBuffer->GetGPUVirtualAddress());
    list->SetGraphicsRootDescriptorTable(11, t.composite);
    list->SetGraphicsRootDescriptorTable(15, Gpu(MaxImages + 7));
    list->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    list->IASetIndexBuffer(&mIndexView);
}

void Ship::DrawShadows(ID3D12GraphicsCommandList* list, const Tables& t)
{
    if (mShadowsReadable) {
        const CD3DX12_RESOURCE_BARRIER toWrite[2] = {
            CD3DX12_RESOURCE_BARRIER::Transition(mShadowMaps[0].Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_DEPTH_WRITE),
            CD3DX12_RESOURCE_BARRIER::Transition(mShadowMaps[1].Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_DEPTH_WRITE) };
        list->ResourceBarrier(2, toWrite);
    }
    Bind(list, t, false);
    const CD3DX12_VIEWPORT viewport(0.0f, 0.0f, float(ShadowSize), float(ShadowSize));
    const CD3DX12_RECT scissor(0, 0, LONG(ShadowSize), LONG(ShadowSize));
    list->RSSetViewports(1, &viewport);
    list->RSSetScissorRects(1, &scissor);
    for (UINT k = 0; k < 2; ++k) {
        D3D12_CPU_DESCRIPTOR_HANDLE dsv = mDsvHeap->GetCPUDescriptorHandleForHeapStart();
        dsv.ptr += SIZE_T(k) * mDsvStride;
        list->OMSetRenderTargets(0, nullptr, FALSE, &dsv);
        list->ClearDepthStencilView(dsv, D3D12_CLEAR_FLAG_DEPTH, 1.0f, 0, 0, nullptr);
        list->SetGraphicsRoot32BitConstant(2, k, 1);
        list->SetPipelineState(mShadowPSO.Get());
        for (const Draw& d : mDraws)
            if (mModes[d.material] == 0 && VisibleInView(d))
                list->DrawIndexedInstanced(d.count, 1, d.first, 0, 0);
        if (mMaskedShadowPSO) {
            list->SetPipelineState(mMaskedShadowPSO.Get());
            for (const Draw& d : mDraws)
                if (mModes[d.material] == 3 && VisibleInView(d)) {
                    list->SetGraphicsRoot32BitConstant(2, d.material, 0);
                    list->DrawIndexedInstanced(d.count, 1, d.first, 0, 0);
                }
        }
    }
    const CD3DX12_RESOURCE_BARRIER toRead[2] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mShadowMaps[0].Get(), D3D12_RESOURCE_STATE_DEPTH_WRITE, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mShadowMaps[1].Get(), D3D12_RESOURCE_STATE_DEPTH_WRITE, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE) };
    list->ResourceBarrier(2, toRead);
    mShadowsReadable = true;
}

void Ship::DrawOpaque(ID3D12GraphicsCommandList* list, const Tables& t)
{
    // An opaque exterior hides the whole cabin. Leave all ship geometry out of its scene-reflection source.
    if (mProfile.sceneReflections && mConstants->options.y < 0.5f) return;
    Bind(list, t, false);
    list->SetPipelineState(mOpaquePSO.Get());
    for (const Draw& d : mDraws)
        if ((mModes[d.material] == 0 || mModes[d.material] == 3) && VisibleInView(d) &&
            !(mProfile.sceneReflections && mRoles[d.material] == 10)) {
            list->SetGraphicsRoot32BitConstant(2, d.material, 0);
            list->DrawIndexedInstanced(d.count, 1, d.first, 0, 0);
        }
}

void Ship::UpdateWeather(ID3D12GraphicsCommandList* list, const Tables& t, ID3D12CommandSignature* dispatch)
{
    const D3D12_RESOURCE_STATES weatherRead = D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE
        | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT;
    const auto toUav = CD3DX12_RESOURCE_BARRIER::Transition(mWeather.Get(), weatherRead, D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    list->ResourceBarrier(1, &toUav);
    Bind(list, t, true);
    // Reset the contents on first use and teleports, independently of resource states.
    static_assert(DropCount % 64 == 0);
    const UINT waterControl[2] = {mResetSurfaceWeather ? 1u : 0u, DropCount / 64};
    list->SetComputeRoot32BitConstants(2, 2, waterControl, 2);
    list->SetComputeRootDescriptorTable(14, Gpu(MaxImages + 3));
    list->SetPipelineState(mWeatherPSO.Get());
    list->Dispatch(1, 1, 1);
    const auto uavDone = CD3DX12_RESOURCE_BARRIER::UAV(nullptr);
    list->ResourceBarrier(1, &uavDone);
    const auto weatherToRead = CD3DX12_RESOURCE_BARRIER::Transition(mWeather.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS, weatherRead);
    list->ResourceBarrier(1, &weatherToRead);
    list->SetComputeRootShaderResourceView(9, mWeather->GetGPUVirtualAddress());

    // The canopy's water (ShipWater.hlsli): move the drops, clear the map, draw them into it; the glass then reads it.
    const D3D12_RESOURCE_STATES read = D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE;
    if (mWaterReadable) {
        const CD3DX12_RESOURCE_BARRIER toWrite[2] = {
            CD3DX12_RESOURCE_BARRIER::Transition(mWaterMap.Get(), read, D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
            CD3DX12_RESOURCE_BARRIER::Transition(mWaterFilm.Get(), read, D3D12_RESOURCE_STATE_UNORDERED_ACCESS) };
        list->ResourceBarrier(2, toWrite);
    }
    // Weather writes zero groups for a dry atlas, including after the last drop and film evaporate.
    const UINT64 particleArgs = 3 * sizeof(XMFLOAT4), atlasArgs = 4 * sizeof(XMFLOAT4);
    list->SetPipelineState(mWaterPSO[0].Get());
    list->ExecuteIndirect(dispatch, 1, mWeather.Get(), particleArgs, nullptr, 0);
    list->ResourceBarrier(1, &uavDone);
    list->SetPipelineState(mWaterPSO[1].Get());
    list->ExecuteIndirect(dispatch, 1, mWeather.Get(), atlasArgs, nullptr, 0);
    list->ResourceBarrier(1, &uavDone);
    list->SetPipelineState(mWaterPSO[2].Get());
    list->ExecuteIndirect(dispatch, 1, mWeather.Get(), particleArgs, nullptr, 0);
    const CD3DX12_RESOURCE_BARRIER toRead[3] = {
        CD3DX12_RESOURCE_BARRIER::UAV(mGathered.Get()),
        CD3DX12_RESOURCE_BARRIER::Transition(mWaterMap.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS, read),
        CD3DX12_RESOURCE_BARRIER::Transition(mWaterFilm.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS, read) };
    list->ResourceBarrier(3, toRead);
    mWaterReadable = true;
    mResetSurfaceWeather = false;
}

void Ship::ClearOverlay(ID3D12GraphicsCommandList* list)
{
    const float none[4] = { 0.0f, 0.0f, 0.0f, 1.0f };
    list->ClearRenderTargetView(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), none, 0, nullptr);
}

void Ship::DrawGlass(ID3D12GraphicsCommandList* list, const Tables& t, D3D12_CPU_DESCRIPTOR_HANDLE dsv)
{
    const D3D12_CPU_DESCRIPTOR_HANDLE rtv = mRtvHeap->GetCPUDescriptorHandleForHeapStart();
    list->OMSetRenderTargets(1, &rtv, FALSE, &dsv);
    Bind(list, t, false);
    const bool cockpit = mConstants->options.y > 0.5f;
    const bool hot = mConstants->airflow.w > 0.002f && mConstants->options.w > 1.e-9f && mConstants->air.x > 12.0f;
    auto drawOptics = [&]() {
        if (mProfile.sceneReflections) {
            list->SetPipelineState(cockpit ? mGlassPSO.Get() : mReflectionPSO.Get());
            for (const Draw& d : mDraws)
                if (mModes[d.material] == 0 && mRoles[d.material] == 10) {
                    list->SetGraphicsRoot32BitConstant(2, d.material, 0);
                    list->DrawIndexedInstanced(d.count, 1, d.first, 0, 0);
                }
            return;
        }
        list->SetPipelineState(mGlassPSO.Get());
        for (uint32_t mode : { 2u, 1u }) // the canopy, then the combiner under it
            for (const Draw& d : mDraws)
                if (mModes[d.material] == mode) {
                    list->SetGraphicsRoot32BitConstant(2, d.material, 0);
                    list->DrawIndexedInstanced(d.count, 1, d.first, 0, 0);
                }
    };
    // To the outside eye the skin is beyond the near gas. To the pilot it is
    // in front of the gas and the physical cabin masks the aperture.
    if (!cockpit) drawOptics();
    const bool manoeuvring = mProfile.surfaces.span > 0 && !cockpit &&
        (mConstants->airframe.z > .01f || mConstants->supportExhaust.w > .01f);
    const bool transport = HasTransportRig();
    const float trimLift = transport ? std::max(mConstants->automation.w, -mConstants->thrust.z) : std::abs(mConstants->thrust.z);
    const float puffs = std::max({std::abs(mConstants->thrust.y), trimLift, std::abs(mConstants->thrust.w),
                                  std::abs(mConstants->turn.x), std::abs(mConstants->turn.y)});
    const bool attitudePlumes = mProfile.jetCount > 2 && !cockpit &&
        (puffs > .01f || (transport && mConstants->airframe.z > .01f));
    const bool plumes = mProfile.jetCount && (mConstants->thrust.x > .01f || attitudePlumes || manoeuvring);
    if (hot || plumes) {
        list->OMSetRenderTargets(1, &rtv, FALSE, nullptr);
        const auto toRead = CD3DX12_RESOURCE_BARRIER::Transition(mSceneDepth.Get(), D3D12_RESOURCE_STATE_DEPTH_WRITE, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
        list->ResourceBarrier(1, &toRead);
        list->SetGraphicsRootDescriptorTable(19, Gpu(MaxImages + 11));
        if (hot) {
            list->SetGraphicsRootDescriptorTable(13, t.cloudTextures);
            list->SetGraphicsRootDescriptorTable(18, Gpu(MaxImages + 10));
            list->SetPipelineState(mEntryVolumePSO.Get());
            list->DrawInstanced(36, 1, 0, 0);
        }
        if (plumes) {
            list->SetPipelineState(mPlumePSO.Get());
            const UINT count = transport && !attitudePlumes ? 2 : mProfile.jetCount;
            list->DrawInstanced(36, count + (manoeuvring ? SHIP_MANOEUVRING_JETS : 0), 0, 0);
        }
        const auto toDepth = CD3DX12_RESOURCE_BARRIER::Transition(mSceneDepth.Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_DEPTH_WRITE);
        list->ResourceBarrier(1, &toDepth);
        list->OMSetRenderTargets(1, &rtv, FALSE, &dsv);
    }
    if (cockpit) drawOptics();
    if (hot) {
        list->SetPipelineState(mEntryParticlesPSO.Get());
        list->DrawInstanced(6, 256, 0, 0); // one depth-tested short streak per live slot, no simulation buffer
    }
}

void Ship::OverlayToRead(ID3D12GraphicsCommandList* list)
{
    const auto b = CD3DX12_RESOURCE_BARRIER::Transition(mOverlay.Get(), D3D12_RESOURCE_STATE_RENDER_TARGET, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
    list->ResourceBarrier(1, &b);
}

void Ship::OverlayToTarget(ID3D12GraphicsCommandList* list)
{
    const auto b = CD3DX12_RESOURCE_BARRIER::Transition(mOverlay.Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_RENDER_TARGET);
    list->ResourceBarrier(1, &b);
}
