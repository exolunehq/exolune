// Scans.cpp - see Scans.h.
#include "Scans.h"
#include "GpuHelpers.h"
#include <wincodec.h>
#include <algorithm>
#include <cmath>

#pragma comment(lib, "windowscodecs.lib")

using Microsoft::WRL::ComPtr;

namespace
{
// The scans: the sand, and the bedded rock's tile, a cliff face photographed head-on. Each scan, of real width `width`
// (m), is laid on its material's tile of `tile` m, its heights scaled with it. Poly Haven gives no height scale:
// `metresPerUnit` is ours, 3 cm of relief over 2.5 m for the sand and gravel; for the cliff, the slopes' deviation the
// universal rule takes for rock, STONE_SLOPE_SIGMA. tile and heightRange as in Materials.hlsli. A scan carries the
// wavelengths under `keep` (m) only: the sand's longer ones, repeated from one copy of the tile to the next, showed as
// an even camouflage from 10 m; the cliff keeps them all, its fractures and flutes of 1 to 12 m being the point.
// `saturation`: how much of the scan's own hue variations its colour factor keeps, the rest following its brightness:
// the strata give the cliff its hues.
struct Scan { UINT slice; const wchar_t* name; double width, tile, metresPerUnit, heightRange, keep, saturation; };
const Scan kScans[] = {
    { 0, L"sandy_gravel_02", 2.53, 64.0 / 24.0, 0.05, 0.06, 0.5, 1.0 }, // MATERIAL_SAND, SAND_TILE
    { 1, L"marble_cliff_04", 12.7, 64.0 / 5.0, 1.2, 0.6, 64.0 / 5.0, 0.3 }, // MATERIAL_ROCK, ROCK_TILE
    { 6, L"marble_cliff_05", 20.0, 64.0 / 3.0, 2.4, 0.6, 64.0 / 3.0, 0.3 }, // MATERIAL_ROCK_TOP, ROCK_TOP_TILE: the same marble, top-down
};

// Low-pass of a size x size image of `channels` interleaved channels, around the tile: three box blurs of width
// `width` texels per axis, close to a Gaussian of deviation width / 2.
std::vector<double> Blur(const std::vector<double>& image, UINT size, UINT channels, UINT width)
{
    std::vector<double> a = image, b(image.size());
    for (UINT pass = 0; pass < 6; ++pass) {
        const size_t step = pass % 2 ? size_t(size) * channels : channels, line = pass % 2 ? channels : size_t(size) * channels;
        for (UINT l = 0; l < size; ++l)
            for (UINT c = 0; c < channels; ++c) {
                const size_t start = l * line + c;
                double sum = 0.0;
                for (UINT k = 0; k < width; ++k) sum += a[start + ((k + size - width / 2) % size) * step];
                for (UINT i = 0; i < size; ++i) {
                    b[start + i * step] = sum / width;
                    sum += a[start + ((i + width - width / 2) % size) * step] - a[start + ((i + size - width / 2) % size) * step];
                }
            }
        a.swap(b);
    }
    return a;
}

// Reads a square image with WIC, in a pixel format that keeps its values as stored: colour, 8-bit sRGB, to linear
// rgb; height, 16-bit grey, to [0, 1]. Reduced to size x size by averaging, its side a multiple of size, and
// flipped: the image's top lies at the tile's far y, which climbs the cliffs.
bool ReadScan(IWICImagingFactory* wic, const std::wstring& path, bool color, UINT size, std::vector<double>& out)
{
    ComPtr<IWICBitmapDecoder> decoder;
    ComPtr<IWICBitmapFrameDecode> frame;
    ComPtr<IWICFormatConverter> converter;
    UINT w = 0, h = 0;
    if (FAILED(wic->CreateDecoderFromFilename(path.c_str(), nullptr, GENERIC_READ, WICDecodeMetadataCacheOnDemand, &decoder))
        || FAILED(decoder->GetFrame(0, &frame)) || FAILED(frame->GetSize(&w, &h)) || w != h || w % size != 0
        || FAILED(wic->CreateFormatConverter(&converter))
        || FAILED(converter->Initialize(frame.Get(), color ? GUID_WICPixelFormat32bppRGBA : GUID_WICPixelFormat16bppGray,
                                        WICBitmapDitherTypeNone, nullptr, 0.0, WICBitmapPaletteTypeCustom)))
        return false;
    const UINT stride = color ? 4 * w : 2 * w, channels = color ? 3 : 1, k = w / size;
    std::vector<BYTE> pixels(size_t(stride) * h);
    if (FAILED(converter->CopyPixels(nullptr, stride, UINT(pixels.size()), pixels.data())))
        return false;
    double linear[256];
    for (int v = 0; v < 256; ++v)
        linear[v] = v <= 10 ? v / (255.0 * 12.92) : std::pow((v / 255.0 + 0.055) / 1.055, 2.4);
    out.assign(size_t(size) * size * channels, 0.0);
    for (UINT y = 0; y < h; ++y)
        for (UINT x = 0; x < w; ++x) {
            double* o = &out[(size_t(size - 1 - y / k) * size + x / k) * channels];
            const BYTE* p = &pixels[size_t(y) * stride + (color ? 4 : 2) * x];
            for (UINT c = 0; c < channels; ++c)
                o[c] += (color ? linear[p[c]] : (p[0] | p[1] << 8) / 65535.0) / (k * k);
        }
    return true;
}

}

// Written as MaterialGenerator.hlsl would: colour factor / 4, of mean 1, and no cavity; slope * 0.25 + 0.5 by centred
// differences around the tile, and height in m over the slice's height range.
std::wstring LoadScans(ID3D12Device* device, ID3D12GraphicsCommandList* list, ID3D12Resource* const materials[2],
                       UINT size, UINT mips, const std::wstring& folder, std::vector<ComPtr<ID3D12Resource>>& uploads)
{
    const std::wstring root = folder.empty() ? FindAbove(L"scans") : folder;
    std::wstring missing;
    ComPtr<IWICImagingFactory> wic;
    CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&wic))))
        return L"WIC";
    for (const Scan& s : kScans) {
        const std::wstring base = root + L"\\" + s.name + L"\\" + s.name;
        std::vector<double> rgb, height;
        if (!ReadScan(wic.Get(), base + L"_diff_2k.jpg", true, size, rgb) || !ReadScan(wic.Get(), base + L"_disp_2k.png", false, size, height)) {
            missing += missing.empty() ? s.name : std::wstring(L", ") + s.name;
            continue;
        }
        const size_t n = size_t(size) * size;
        const double texel = s.tile / size, metres = s.metresPerUnit * s.tile / s.width;
        // The high-pass: a Gaussian of deviation keep / 5.3 halves the power at wavelength keep; none when keep is the
        // tile. Then the means, after it: each channel's factor has a mean of exactly 1 over the tile, and the biome
        // gives the hue.
        const UINT width = 2 * UINT(s.keep / 5.3 / texel) + 1;
        const std::vector<double> lowColor = s.keep < s.tile ? Blur(rgb, size, 3, width) : std::vector<double>(rgb.size(), 1.0);
        const std::vector<double> lowHeight = s.keep < s.tile ? Blur(height, size, 1, width) : std::vector<double>(height.size(), 0.0);
        double mean[3] = {}, meanHeight = 0.0;
        for (size_t i = 0; i < n; ++i) {
            for (int c = 0; c < 3; ++c) mean[c] += (rgb[3 * i + c] /= std::max(lowColor[3 * i + c], 1e-6)) / n;
            meanHeight += (height[i] -= lowHeight[i]) / n;
        }
        const double meanLum = 0.2126 * mean[0] + 0.7152 * mean[1] + 0.0722 * mean[2];
        auto h = [&](UINT x, UINT y) { return (height[size_t(y % size) * size + x % size] - meanHeight) * metres; };
        std::vector<double> mip[2] = { std::vector<double>(4 * n), std::vector<double>(4 * n) };
        for (UINT y = 0; y < size; ++y)
            for (UINT x = 0; x < size; ++x) {
                const size_t i = size_t(y) * size + x;
                const double lum = (0.2126 * rgb[3 * i] + 0.7152 * rgb[3 * i + 1] + 0.0722 * rgb[3 * i + 2]) / meanLum;
                for (int c = 0; c < 3; ++c)
                    mip[0][4 * i + c] = 0.25 * (lum + s.saturation * (rgb[3 * i + c] / mean[c] - lum));
                mip[0][4 * i + 3] = 1.0;
                mip[1][4 * i] = 0.25 * (h(x + 1, y) - h(x + size - 1, y)) / (2.0 * texel) + 0.5;
                mip[1][4 * i + 1] = 0.25 * (h(x, y + 1) - h(x, y + size - 1)) / (2.0 * texel) + 0.5;
                mip[1][4 * i + 2] = h(x, y) / s.heightRange + 0.5;
                mip[1][4 * i + 3] = 0.0;
            }
        for (UINT t = 0; t < 2; ++t) {
            const D3D12_RESOURCE_DESC desc = materials[t]->GetDesc();
            std::vector<D3D12_PLACED_SUBRESOURCE_FOOTPRINT> footprints(mips);
            UINT64 bytes = 0;
            device->GetCopyableFootprints(&desc, s.slice * mips, mips, 0, footprints.data(), nullptr, nullptr, &bytes);
            uploads.push_back(CreateBuffer(device, bytes, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ));
            BYTE* mapped = nullptr;
            CD3DX12_RANGE noRead(0, 0);
            uploads.back()->Map(0, &noRead, reinterpret_cast<void**>(&mapped));
            std::vector<double> level = mip[t];
            for (UINT m = 0, side = size; m < mips; ++m, side /= 2) {
                if (m > 0) { // each mip averages 2 x 2 texels of the previous one
                    std::vector<double> next(size_t(side) * side * 4);
                    for (UINT y = 0; y < side; ++y)
                        for (UINT x = 0; x < side; ++x)
                            for (UINT c = 0; c < 4; ++c)
                                next[(size_t(y) * side + x) * 4 + c] = 0.25 * (level[(size_t(2 * y) * 2 * side + 2 * x) * 4 + c]
                                    + level[(size_t(2 * y) * 2 * side + 2 * x + 1) * 4 + c] + level[(size_t(2 * y + 1) * 2 * side + 2 * x) * 4 + c]
                                    + level[(size_t(2 * y + 1) * 2 * side + 2 * x + 1) * 4 + c]);
                    level.swap(next);
                }
                for (UINT y = 0; y < side; ++y)
                    for (UINT x = 0; x < side * 4; ++x)
                        mapped[footprints[m].Offset + size_t(y) * footprints[m].Footprint.RowPitch + x] =
                            BYTE(std::min(std::max(level[size_t(y) * side * 4 + x], 0.0), 1.0) * 255.0 + 0.5);
                const CD3DX12_TEXTURE_COPY_LOCATION to(materials[t], s.slice * mips + m), from(uploads.back().Get(), footprints[m]);
                list->CopyTextureRegion(&to, 0, 0, 0, &from, nullptr);
            }
            uploads.back()->Unmap(0, nullptr);
        }
    }
    return missing;
}
