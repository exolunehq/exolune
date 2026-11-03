#include "PlanetFoliage.h"
#include "GpuHelpers.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cwchar>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <DirectXPackedVector.h>
using Microsoft::WRL::ComPtr;
namespace {
// The leaves' self-shadowing: the strength of the visibilities precomputed in the models (docs/vegetation-planetaire.md).
constexpr float VolumeStrength = 0.65f;

std::string Utf8(const std::wstring& text) {
    const int count = WideCharToMultiByte(CP_UTF8, 0, text.data(), int(text.size()), nullptr, 0, nullptr, nullptr);
    std::string utf8(count > 0 ? size_t(count) : 0, '\0');
    if (count > 0) WideCharToMultiByte(CP_UTF8, 0, text.data(), int(text.size()), &utf8[0], count, nullptr, nullptr);
    return utf8;
}

std::vector<unsigned char> Read(const std::wstring& path) {
    std::ifstream f(path, std::ios::binary | std::ios::ate);
    if (!f) throw std::runtime_error("Foliage asset missing or inaccessible: " + Utf8(path));
    const auto n = f.tellg();
    if (n <= 0) throw std::runtime_error("Empty foliage asset.");
    std::vector<unsigned char> bytes(static_cast<size_t>(n));
    f.seekg(0); f.read(reinterpret_cast<char*>(bytes.data()), bytes.size());
    if (!f) throw std::runtime_error("Foliage asset read failed.");
    return bytes;
}
template<class T> T Field(const std::vector<unsigned char>& b, size_t offset) {
    if (offset + sizeof(T) > b.size()) throw std::runtime_error("Truncated foliage asset header.");
    T value; memcpy(&value, b.data() + offset, sizeof(value)); return value;
}
// Choose the nearest attainable coverage at the alpha-test threshold.
float CoverageScale(const float* pixels, size_t count, size_t stride, double target) {
    if (target <= 0) return 0.0f;
    auto coverage = [&](float scale) {
        size_t hits = 0;
        for (size_t i = 0; i < count; ++i) if (pixels[i*stride+3] * scale >= 0.5f) ++hits;
        return double(hits) / double(count);
    };
    float lo=0, hi=256;
    for (int i=0;i<20;++i) {
        const float mid=(lo+hi)*0.5f;
        if (coverage(mid)<target) lo=mid; else hi=mid;
    }
    return std::abs(coverage(lo)-target) <= std::abs(coverage(hi)-target) ? lo : hi;
}
float LinearF(float c) { return c <= 0.04045f ? c / 12.92f : std::pow((c + 0.055f) / 1.055f, 2.4f); }
unsigned char ByteF(float c) { return static_cast<unsigned char>(std::round(std::max(0.0f,std::min(c,1.0f))*255.0f)); }
unsigned char SRGBByte(float c) {
    c=std::max(0.0f,std::min(c,1.0f));
    return ByteF(c <= 0.0031308f ? 12.92f*c : 1.055f*std::pow(c,1.0f/2.4f)-0.055f);
}
struct MeshLevel {
    UINT width, height;
    std::vector<unsigned char> maps[3];
};
// The intermediate samples are alpha-premultiplied in linear space; coverage adjustment
// is applied only to the stored alpha, never fed into the next level.
std::vector<MeshLevel> MeshPyramid(const unsigned char* color, const unsigned char* material,
                                   UINT atlasWidth, UINT height, UINT slices) {
    const UINT width=atlasWidth/slices;
    std::vector<MeshLevel> levels;
    for (UINT w=width,h=height;; w=std::max(w/2,1u),h=std::max(h/2,1u)) {
        MeshLevel level; level.width=w; level.height=h;
        for (auto& map:level.maps) map.resize(size_t(slices)*w*h*4);
        levels.push_back(std::move(level));
        if (w==1 && h==1) break;
    }
    const size_t atlasBytes=size_t(atlasWidth)*height*4;
    for (UINT slice=0;slice<slices;++slice) {
        UINT w=width,h=height;
        std::vector<float> pixels(size_t(w)*h*10);
        size_t baseHits=0;
        for (UINT y=0;y<h;++y) for (UINT x=0;x<w;++x) {
            const size_t source=(size_t(y)*atlasWidth+slice*w+x)*4;
            const float a=color[source+3]/255.0f; if (a>=0.5f) ++baseHits;
            float* dst=pixels.data()+(size_t(y)*w+x)*10;
            for (int k=0;k<3;++k) dst[k]=LinearF(color[source+k]/255.0f)*a;
            dst[3]=a;
            for (int k=0;k<3;++k) {
                const float n=material ? (material[source+k]/255.0f*2.0f-1.0f) : (k==2 ? 1.0f : 0.0f);
                const float mask=material ? material[atlasBytes+source+k]/255.0f : 1.0f;
                dst[4+k]=n*a; dst[7+k]=mask*a;
            }
        }
        const double target=double(baseHits)/double(size_t(w)*h);
        for (UINT mip=0;mip<levels.size();++mip) {
            MeshLevel& level=levels[mip];
            const size_t count=size_t(w)*h, sliceOffset=size_t(slice)*count*4;
            const float scale=mip ? CoverageScale(pixels.data(),count,10,target) : 1.0f;
            std::vector<UINT> queue; queue.reserve(count);
            std::vector<unsigned char> visited(count,0);
            unsigned char* out[3] = {level.maps[0].data()+sliceOffset,level.maps[1].data()+sliceOffset,level.maps[2].data()+sliceOffset};
            for (size_t i=0;i<count;++i) {
                const float* p=pixels.data()+i*10; const float a=p[3];
                out[0][i*4+3]=ByteF(a*scale); out[1][i*4+3]=out[2][i*4+3]=255;
                if (a<=1e-12f) continue;
                const float nx=p[4]/a,ny=p[5]/a,nz=p[6]/a;
                const float length=std::sqrt(nx*nx+ny*ny+nz*nz);
                for (int k=0;k<3;++k) {
                    out[0][i*4+k]=SRGBByte(p[k]/a);
                    const float n=length>1e-12f ? p[4+k]/a/length : (k==2 ? 1.0f : 0.0f);
                    out[1][i*4+k]=ByteF(n*0.5f+0.5f);
                    out[2][i*4+k]=ByteF(p[7+k]/a);
                }
                visited[i]=1; queue.push_back(UINT(i));
            }
            // Dilate RGB into alpha-zero texels, including across wrap seams.
            for (size_t head=0;head<queue.size();++head) {
                const UINT from=queue[head], x=from%w, y=from/w;
                const UINT neighbours[4]={y*w+(x+1)%w,y*w+(x+w-1)%w,((y+1)%h)*w+x,((y+h-1)%h)*w+x};
                for (UINT to:neighbours) if (!visited[to]) {
                    visited[to]=1; queue.push_back(to);
                    for (UINT map=0;map<3;++map) for (UINT k=0;k<3;++k) out[map][size_t(to)*4+k]=out[map][size_t(from)*4+k];
                }
            }
            if (mip+1==levels.size()) break;
            const UINT nw=std::max(w/2,1u),nh=std::max(h/2,1u);
            std::vector<float> next(size_t(nw)*nh*10,0.0f);
            for (UINT y=0;y<nh;++y) for (UINT x=0;x<nw;++x) for (UINT dy=0;dy<2;++dy) for (UINT dx=0;dx<2;++dx) {
                const UINT sx=std::min(x*2+dx,w-1),sy=std::min(y*2+dy,h-1);
                const float* src=pixels.data()+(size_t(sy)*w+sx)*10; float* dst=next.data()+(size_t(y)*nw+x)*10;
                for (int k=0;k<10;++k) dst[k]+=src[k]*0.25f;
            }
            pixels=std::move(next); w=nw; h=nh;
        }
    }
    return levels;
}
// Each level contains linear colour/coverage and normal/depth, all premultiplied.
struct ImpostorLevel {
    UINT width, height;
    std::vector<float> pixels; // eight floats per texel, view-major
};
std::vector<ImpostorLevel> ImpostorPyramid(const unsigned char* source, UINT viewCount, UINT width, UINT height) {
    const size_t basePixels = size_t(viewCount) * width * height;
    std::vector<ImpostorLevel> levels;
    levels.push_back({ width, height, std::vector<float>(basePixels * 8) });
    const auto linear = [](float v) { return v <= 0.04045f ? v / 12.92f : std::pow((v + 0.055f) / 1.055f, 2.4f); };
    for (size_t i = 0; i < basePixels; ++i) {
        const unsigned char* c = source + i * 4;
        float* dst = levels[0].pixels.data() + i * 8;
        const float alpha = c[3] / 255.0f;
        for (int k = 0; k < 3; ++k) dst[k] = linear(c[k] / 255.0f) * alpha;
        dst[3] = alpha;
        float nd[4]; memcpy(nd, source + basePixels * 4 + i * 16, sizeof(nd));
        for (int k = 0; k < 4; ++k) dst[4 + k] = nd[k] * alpha;
    }
    while (width > 1 || height > 1) {
        const UINT nextWidth = std::max(width / 2, 1u), nextHeight = std::max(height / 2, 1u);
        ImpostorLevel next{ nextWidth, nextHeight, std::vector<float>(size_t(viewCount) * nextWidth * nextHeight * 8) };
        const auto& prev = levels.back().pixels;
        for (UINT view = 0; view < viewCount; ++view) for (UINT y = 0; y < nextHeight; ++y) for (UINT x = 0; x < nextWidth; ++x) {
            float* dst = next.pixels.data() + ((size_t(view) * nextHeight + y) * nextWidth + x) * 8;
            for (UINT dy = 0; dy < 2; ++dy) for (UINT dx = 0; dx < 2; ++dx) {
                const UINT sx = std::min(x * 2 + dx, width - 1), sy = std::min(y * 2 + dy, height - 1);
                const float* src = prev.data() + ((size_t(view) * height + sy) * width + sx) * 8;
                for (int k = 0; k < 8; ++k) dst[k] += src[k] * 0.25f;
            }
        }
        levels.push_back(std::move(next)); width = nextWidth; height = nextHeight;
    }
    return levels;
}
// Both input planes are view-major, unassociated RGBA8. Filter with the exact
// impostor alpha, and adjust coverage only while uploading, just like colour/ND.
std::vector<ImpostorLevel> ImpostorLightPyramid(const unsigned char* source, const unsigned char* colour,
                                                 UINT views, UINT width, UINT height) {
    const size_t count=size_t(views)*width*height;
    std::vector<ImpostorLevel> levels;
    levels.push_back({width,height,std::vector<float>(count*8)});
    for (size_t i=0;i<count;++i) {
        const float alpha=colour[i*4+3]/255.0f;
        for (UINT channel=0;channel<2;++channel) for (UINT k=0;k<4;++k)
            levels[0].pixels[i*8+channel*4+k]=source[channel*count*4+i*4+k]*(alpha/255.0f);
    }
    while (width>1 || height>1) {
        const UINT nw=std::max(width/2,1u),nh=std::max(height/2,1u);
        ImpostorLevel next{nw,nh,std::vector<float>(size_t(views)*nw*nh*8)};
        const auto& previous=levels.back().pixels;
        for (UINT view=0;view<views;++view) for (UINT y=0;y<nh;++y) for (UINT x=0;x<nw;++x)
            for (UINT dy=0;dy<2;++dy) for (UINT dx=0;dx<2;++dx) {
                const UINT sx=std::min(2*x+dx,width-1),sy=std::min(2*y+dy,height-1);
                const float* a=previous.data()+((size_t(view)*height+sy)*width+sx)*8;
                float* b=next.pixels.data()+((size_t(view)*nh+y)*nw+x)*8;
                for (UINT k=0;k<8;++k) b[k]+=0.25f*a[k];
            }
        levels.push_back(std::move(next)); width=nw; height=nh;
    }
    return levels;
}
}


void PlanetFoliage::Initialize(ID3D12Device* device, ID3D12GraphicsCommandList* list, const std::wstring& root, DXGI_FORMAT hdr,
                               DXGI_FORMAT sun, DXGI_FORMAT depth, D3D12_CPU_DESCRIPTOR_HANDLE impostorCpu,
                               D3D12_GPU_DESCRIPTOR_HANDLE impostorGpu,int testLod) {
    // The models' folders: the two trees, then the shrubs in the catalogue's order, two per climate.
    std::wstring folders[MaxModels] = { L"game_fir", L"game_broadleaf" };
    std::vector<UINT> leafMasks(MaxModels,2u); leafMasks[1]=1u;
    std::ifstream community(root+L"/biomes.txt");
    if (community) {
        std::string magic,name,extra; UINT count=0;
        if (!(community>>magic>>count) || !((magic=="FOLBIO01" && count==29u) || (magic=="FOLBIO02" && count==31u) || (magic=="FOLBIO03" && count==91u)))
            throw std::runtime_error("Invalid biome catalogue header.");
        mArtDirected=magic=="FOLBIO02" || magic=="FOLBIO03";mGeneratedBank=magic=="FOLBIO03";
        mDiverse=true; mModelCount=count;
        for (UINT id=0;id<count;++id) {
            UINT group=0;
            if (!(community>>name>>group>>leafMasks[id]) || group!=FoliageModelSpecies(id) || name.empty() ||
                name.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_")!=std::string::npos)
                throw std::runtime_error("Invalid biome model record.");
            folders[id]=std::wstring(name.begin(),name.end()); mModelNames.push_back(name);
        }
        if (community>>extra) throw std::runtime_error("Unexpected biome catalogue data.");
    } else
    {
        std::ifstream manifest(root+L"/shrubs.txt"); std::string magic, name, extra; UINT families=0, variants=0;
        if (!manifest) throw std::runtime_error("Plant catalogue missing: " + Utf8(root));
        if (!(manifest>>magic>>families>>variants) || magic!="FOLSHR01" || families!=6 || variants!=2)
            throw std::runtime_error("Invalid shrub catalogue header.");
        const char* familyNames[6]={"boreal","desert","steppe","montane","temperate","tropical"};
        for (UINT family=0;family<6;++family) for (UINT variant=0;variant<2;++variant) {
            const std::string expected=std::string("shrub_")+familyNames[family]+"_"+std::to_string(variant);
            if (!(manifest>>name) || name!=expected) throw std::runtime_error("Invalid shrub catalogue order or folder.");
            folders[2+family*2+variant]=std::wstring(name.begin(),name.end());
        }
        if (manifest>>extra) throw std::runtime_error("Unexpected shrub catalogue data.");
    }
    auto upload = [&](Resource& target, const void* data, size_t bytes) {
        if (!bytes) throw std::runtime_error("Empty planetary foliage buffer.");
        target = CreateBuffer(device, bytes, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COPY_DEST);
        Resource staging = CreateBuffer(device, bytes, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
        void* mapped = nullptr; CD3DX12_RANGE none(0,0);
        Check(staging->Map(0,&none,&mapped), "Planetary foliage staging map failed.");
        memcpy(mapped,data,bytes); staging->Unmap(0,nullptr);
        list->CopyBufferRegion(target.Get(),0,staging.Get(),0,bytes);
        auto barrier = CD3DX12_RESOURCE_BARRIER::Transition(target.Get(), D3D12_RESOURCE_STATE_COPY_DEST,
            D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_INDEX_BUFFER);
        list->ResourceBarrier(1,&barrier); mUploads.push_back(staging);
    };
    const UINT descriptorSize = device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
    auto detailMaps=[&](Detail& detail,const unsigned char* maps,UINT resolution,UINT materials,UINT modelId,UINT level) {
        const size_t atlasBytes=size_t(resolution)*resolution*materials*4;
        const auto levels=MeshPyramid(maps,maps+atlasBytes,resolution*materials,resolution,materials);
        const UINT mipCount=UINT(levels.size()),subresources=materials*mipCount;
        UINT64 bytes=0;
        for (UINT channel=0;channel<3;++channel) {
            const DXGI_FORMAT format=channel==0?DXGI_FORMAT_R8G8B8A8_UNORM_SRGB:DXGI_FORMAT_R8G8B8A8_UNORM;
            const auto desc=CD3DX12_RESOURCE_DESC::Tex2D(format,resolution,resolution,UINT16(materials),UINT16(mipCount));
            const auto hp=CD3DX12_HEAP_PROPERTIES(D3D12_HEAP_TYPE_DEFAULT);
            Check(device->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&detail.maps[channel])),"Foliage LOD texture allocation failed.");
            std::vector<D3D12_PLACED_SUBRESOURCE_FOOTPRINT> footprints(subresources);UINT64 uploadBytes=0;
            device->GetCopyableFootprints(&desc,0,subresources,0,footprints.data(),nullptr,nullptr,&uploadBytes);
            Resource staging=CreateBuffer(device,uploadBytes,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
            unsigned char* mapped=nullptr;CD3DX12_RANGE none(0,0);Check(staging->Map(0,&none,reinterpret_cast<void**>(&mapped)),"Foliage LOD texture staging failed.");
            for (UINT slice=0;slice<materials;++slice) for (UINT mip=0;mip<mipCount;++mip) {
                const UINT sub=mip+slice*mipCount;const auto& image=levels[mip];const size_t row=size_t(image.width)*4,offset=size_t(slice)*image.width*image.height*4;
                for (UINT y=0;y<image.height;++y) memcpy(mapped+footprints[sub].Offset+size_t(y)*footprints[sub].Footprint.RowPitch,image.maps[channel].data()+offset+size_t(y)*row,row);
                CD3DX12_TEXTURE_COPY_LOCATION target(detail.maps[channel].Get(),sub),source(staging.Get(),footprints[sub]);list->CopyTextureRegion(&target,0,0,0,&source,nullptr);
            }
            staging->Unmap(0,nullptr);auto ready=CD3DX12_RESOURCE_BARRIER::Transition(detail.maps[channel].Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);list->ResourceBarrier(1,&ready);mUploads.push_back(staging);
            D3D12_SHADER_RESOURCE_VIEW_DESC view={};view.Format=format;view.ViewDimension=D3D12_SRV_DIMENSION_TEXTURE2DARRAY;view.Shader4ComponentMapping=D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;view.Texture2DArray.MipLevels=mipCount;view.Texture2DArray.ArraySize=materials;
            device->CreateShaderResourceView(detail.maps[channel].Get(),&view,CD3DX12_CPU_DESCRIPTOR_HANDLE(impostorCpu,(modelId*FOLIAGE_MESH_LODS+level)*7+2+channel,descriptorSize));
            for (const auto& image:levels) bytes+=UINT64(materials)*image.width*image.height*4;
        }
        detail.textureSize=resolution;return bytes;
    };
    for (UINT modelId=0; modelId<mModelCount; ++modelId) {
        const UINT species=FoliageModelSpecies(modelId);
        mImpostorTables[modelId][0] = CD3DX12_GPU_DESCRIPTOR_HANDLE(impostorGpu, modelId * FOLIAGE_MESH_LODS * 7, descriptorSize);
        // Keep a valid texture table even where a model has no precomputed light.
        D3D12_SHADER_RESOURCE_VIEW_DESC nullSrv = {};
        nullSrv.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;
        nullSrv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2DARRAY;
        nullSrv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        nullSrv.Texture2DArray.MipLevels = 1; nullSrv.Texture2DArray.ArraySize = 1;
        for (UINT channel = 0; channel < 7; ++channel) {
            nullSrv.Format = channel == 2 ? DXGI_FORMAT_R8G8B8A8_UNORM_SRGB : channel < 2 ? DXGI_FORMAT_R16G16B16A16_FLOAT : DXGI_FORMAT_R8G8B8A8_UNORM;
            device->CreateShaderResourceView(nullptr, &nullSrv, CD3DX12_CPU_DESCRIPTOR_HANDLE(impostorCpu, modelId * FOLIAGE_MESH_LODS * 7 + channel, descriptorSize));
        }
        nullSrv.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;
        Model& model = mModel[modelId];
        UINT shared=modelId;
        for (UINT previous=0;previous<modelId;++previous)
            if (folders[previous]==folders[modelId] && leafMasks[previous]==leafMasks[modelId] && FoliageModelSpecies(previous)==species) { shared=previous;break; }
        if (shared<modelId) {
            model=mModel[shared];model.meshBytes=0;model.proxyBytes=0;
            const float heights[6]={.65f,.85f,.60f,.30f,1.0f,1.15f};
            model.meshSettings.volumeParams[2]=model.proxySettings.volumeParams[2]=species==2 && modelId<14?heights[(modelId-2)/2]:1.0f;
            for (UINT level=0;level<FOLIAGE_MESH_LODS;++level) {
                mImpostorTables[modelId][level]=CD3DX12_GPU_DESCRIPTOR_HANDLE(impostorGpu,(modelId*FOLIAGE_MESH_LODS+level)*7,descriptorSize);
                device->CopyDescriptorsSimple(7,CD3DX12_CPU_DESCRIPTOR_HANDLE(impostorCpu,(modelId*FOLIAGE_MESH_LODS+level)*7,descriptorSize),CD3DX12_CPU_DESCRIPTOR_HANDLE(impostorCpu,(shared*FOLIAGE_MESH_LODS+level)*7,descriptorSize),D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
            }
            continue;
        }
        const std::wstring folder = root + L"/" + folders[modelId] + L"/";
        const auto mesh = Read(folder + L"mesh.bin");
        if (mesh.size()<52 || memcmp(mesh.data(),"FOLMESH1",8)) throw std::runtime_error("Invalid planetary foliage mesh.");
        const UINT vertices=Field<UINT>(mesh,8), indices=Field<UINT>(mesh,12), texWidth=Field<UINT>(mesh,16),
                   texHeight=Field<UINT>(mesh,20), materials=Field<UINT>(mesh,24);
        const size_t vertexBytes=size_t(vertices)*36, indexBytes=size_t(indices)*4, atlasOffset=52+vertexBytes+indexBytes;
        if (!vertices || !indices || !materials || !texWidth || !texHeight || atlasOffset>mesh.size() ||
            size_t(texWidth) > (mesh.size()-atlasOffset)/4/texHeight) throw std::runtime_error("Truncated planetary foliage mesh.");
        const size_t atlasBytes = size_t(texWidth)*texHeight*4;
        std::vector<unsigned char> material;
        const std::wstring materialPath = folder + L"material.bin";
        const DWORD materialAttributes = GetFileAttributesW(materialPath.c_str());
        if (materialAttributes != INVALID_FILE_ATTRIBUTES) {
            if (materialAttributes & FILE_ATTRIBUTE_DIRECTORY) throw std::runtime_error("Invalid planetary foliage material file.");
            material = Read(materialPath);
            if (material.size() < 16 || memcmp(material.data(), "FOLMAT01", 8) ||
                Field<UINT>(material,8) != texWidth || Field<UINT>(material,12) != texHeight ||
                atlasBytes > (material.size()-16)/2 || material.size()-16 != atlasBytes*2 || atlasBytes > UINT_MAX/3)
                throw std::runtime_error("Invalid planetary foliage material atlas.");
        } else {
            const DWORD error = GetLastError();
            if (error != ERROR_FILE_NOT_FOUND && error != ERROR_PATH_NOT_FOUND)
                throw std::runtime_error("Cannot inspect planetary foliage material file.");
        }
        model.meshIndexCount=indices;
        Settings& ms=model.meshSettings;
        ms.width=texWidth; ms.height=texHeight; ms.materialCount=materials; ms.species=species;
        ms.reserved=leafMasks[modelId];
        ms.crown=species==0 ? 0.3f : species==1 ? 0.45f : 1.1f;
        const float shrubHeights[6]={0.65f,0.85f,0.60f,0.30f,1.0f,1.15f};
        ms.volumeParams[0]=VolumeStrength; ms.volumeParams[1]=0.06f;
        ms.volumeParams[2]=species==2 && modelId<14 ? shrubHeights[(modelId-2)/2] : 1.0f;
        ms.flags = material.empty() ? 0u : 1u;
        const std::wstring formPath=folder+L"form.bin";
        if (GetFileAttributesW(formPath.c_str())!=INVALID_FILE_ATTRIBUTES) {
            const auto form=Read(formPath);
            if (form.size()!=24 || memcmp(form.data(),"FOLFORM1",8)) throw std::runtime_error("Invalid rooted plant form.");
            memcpy(ms.rootForm,form.data()+8,16);
            for (float f:ms.rootForm) if (!std::isfinite(f) || f<=0) throw std::runtime_error("Invalid plant form dimensions.");
            ms.flags|=32u;
        }
        memcpy(ms.boundsMin,mesh.data()+28,12); memcpy(ms.boundsMax,mesh.data()+40,12);
        { // the mesh, near the camera
            upload(model.meshVertices,mesh.data()+52,vertexBytes);
            upload(model.meshIndices,mesh.data()+52+vertexBytes,indexBytes);
            { // Les triangles en ordre inverse, pour la couleur en profondeur égale : à profondeur égale, le dernier triangle
              // ombré reste, et c'est le premier dessiné, celui que le test strict garde en profondeur (DrawRepresentation).
                std::vector<UINT> reversed(indices);
                memcpy(reversed.data(),mesh.data()+52+vertexBytes,indexBytes);
                for (UINT t=0;t<indices/3/2;++t) for (UINT k=0;k<3;++k) std::swap(reversed[3*t+k],reversed[indices-3*(t+1)+k]);
                upload(model.meshIndicesReversed,reversed.data(),indexBytes);
                model.meshReversedView={model.meshIndicesReversed->GetGPUVirtualAddress(),UINT(indexBytes),DXGI_FORMAT_R32_UINT};
            }
            const std::wstring lightPath=folder+L"lighting.bin";
            const DWORD lightAttr=GetFileAttributesW(lightPath.c_str());
            if (lightAttr!=INVALID_FILE_ATTRIBUTES) {
                if (lightAttr&FILE_ATTRIBUTE_DIRECTORY) throw std::runtime_error("Invalid foliage vertex lighting file.");
                const auto light=Read(lightPath);
                if (light.size()!=16+size_t(vertices)*32 || memcmp(light.data(),"FOLLIT01",8) ||
                    Field<UINT>(light,8)!=vertices || Field<UINT>(light,12)!=8)
                    throw std::runtime_error("Invalid foliage vertex lighting data.");
                upload(model.meshLighting,light.data()+16,light.size()-16);
                model.meshBytes+=light.size()-16; ms.flags|=8u;
            } else if (GetLastError()!=ERROR_FILE_NOT_FOUND && GetLastError()!=ERROR_PATH_NOT_FOUND)
                throw std::runtime_error("Cannot inspect foliage vertex lighting file.");
            if (!model.meshLighting) {
                // Le SRV racine n'a pas de borne : il doit couvrir chaque sommet,
                // même si le shader n'utilise pas les visibilités neutres.
                std::vector<float> neutral(size_t(vertices)*8,1.0f);
                for (size_t vertex=0;vertex<vertices;++vertex) neutral[vertex*8+7]=0.0f;
                upload(model.meshLighting,neutral.data(),neutral.size()*sizeof(float));
                model.meshBytes+=neutral.size()*sizeof(float);
            }
            model.meshBytes+=vertexBytes+indexBytes;
            if (texWidth % materials || materials > D3D12_REQ_TEXTURE2D_ARRAY_AXIS_DIMENSION ||
                texWidth/materials > D3D12_REQ_TEXTURE2D_U_OR_V_DIMENSION || texHeight > D3D12_REQ_TEXTURE2D_U_OR_V_DIMENSION)
                throw std::runtime_error("Invalid planetary foliage material tile dimensions.");
            const auto levels=MeshPyramid(mesh.data()+atlasOffset,material.empty() ? nullptr : material.data()+16,texWidth,texHeight,materials);
            const UINT mipCount=UINT(levels.size()), subresources=materials*mipCount;
            for (UINT channel=0;channel<3;++channel) {
                const DXGI_FORMAT format=channel==0 ? DXGI_FORMAT_R8G8B8A8_UNORM_SRGB : DXGI_FORMAT_R8G8B8A8_UNORM;
                const auto desc=CD3DX12_RESOURCE_DESC::Tex2D(format,texWidth/materials,texHeight,UINT16(materials),UINT16(mipCount));
                const auto hp=CD3DX12_HEAP_PROPERTIES(D3D12_HEAP_TYPE_DEFAULT);
                Check(device->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,
                    IID_PPV_ARGS(&model.meshMaps[channel])),"Planetary foliage mesh texture allocation failed.");
                std::vector<D3D12_PLACED_SUBRESOURCE_FOOTPRINT> footprints(subresources); UINT64 uploadBytes=0;
                device->GetCopyableFootprints(&desc,0,subresources,0,footprints.data(),nullptr,nullptr,&uploadBytes);
                Resource staging=CreateBuffer(device,uploadBytes,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
                unsigned char* mapped=nullptr; CD3DX12_RANGE none(0,0);
                Check(staging->Map(0,&none,reinterpret_cast<void**>(&mapped)),"Planetary foliage mesh staging map failed.");
                for (UINT slice=0;slice<materials;++slice) for (UINT mip=0;mip<mipCount;++mip) {
                    const UINT subresource=mip+slice*mipCount; const MeshLevel& level=levels[mip];
                    const size_t rowBytes=size_t(level.width)*4, offset=size_t(slice)*level.width*level.height*4;
                    for (UINT y=0;y<level.height;++y)
                        memcpy(mapped+footprints[subresource].Offset+size_t(y)*footprints[subresource].Footprint.RowPitch,
                               level.maps[channel].data()+offset+size_t(y)*rowBytes,rowBytes);
                    CD3DX12_TEXTURE_COPY_LOCATION dst(model.meshMaps[channel].Get(),subresource),src(staging.Get(),footprints[subresource]);
                    list->CopyTextureRegion(&dst,0,0,0,&src,nullptr);
                }
                staging->Unmap(0,nullptr);
                auto barrier=CD3DX12_RESOURCE_BARRIER::Transition(model.meshMaps[channel].Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
                list->ResourceBarrier(1,&barrier); mUploads.push_back(staging);
                D3D12_SHADER_RESOURCE_VIEW_DESC srv=nullSrv; srv.Format=format;
                srv.Texture2DArray.MipLevels=mipCount; srv.Texture2DArray.ArraySize=materials;
                device->CreateShaderResourceView(model.meshMaps[channel].Get(),&srv,CD3DX12_CPU_DESCRIPTOR_HANDLE(impostorCpu,modelId*FOLIAGE_MESH_LODS*7+2+channel,descriptorSize));
                for (const auto& level:levels) model.meshBytes+=UINT64(materials)*level.width*level.height*4;
            }
            model.meshView={model.meshIndices->GetGPUVirtualAddress(),UINT(indexBytes),DXGI_FORMAT_R32_UINT};
        }
        // Geometry-only LODs share L0's textures, bounds, pivot and material mask.
        const std::wstring lodPath=folder+L"lods.bin";
        const bool hasLods=GetFileAttributesW(lodPath.c_str())!=INVALID_FILE_ATTRIBUTES;
        if (hasLods) {
            const auto data=Read(lodPath);
            if (data.size()<16 || memcmp(data.data(),"FOLLOD02",8) || Field<UINT>(data,12)!=vertices)
                throw std::runtime_error("Invalid foliage LOD header.");
            model.levelCount=Field<UINT>(data,8);
            if (model.levelCount<1 || model.levelCount>FOLIAGE_MESH_LODS || !(ms.flags&8u))
                throw std::runtime_error("Invalid foliage LOD count or missing source lighting.");
            size_t at=16;
            auto take=[&](size_t bytes) {
                if (at>data.size() || bytes>data.size()-at) throw std::runtime_error("Truncated foliage LOD data.");
                const unsigned char* pointer=data.data()+at;at+=bytes;return pointer;
            };
            auto finite=[&](const unsigned char* pointer,size_t count) {
                for (size_t i=0;i<count;++i) { float f;memcpy(&f,pointer+i*4,4);if (!std::isfinite(f)) throw std::runtime_error("Non-finite foliage LOD vertex."); }
            };
            const auto extra=take(size_t(vertices)*64);finite(extra,size_t(vertices)*16);
            upload(model.extra,extra,size_t(vertices)*64);model.meshBytes+=UINT64(vertices)*64;ms.flags|=64u;
            for (UINT level=1;level<model.levelCount;++level) {
                const auto header=take(12);UINT nv=0,ni=0,resolution=0;memcpy(&nv,header,4);memcpy(&ni,header+4,4);memcpy(&resolution,header+8,4);
                if (!nv || nv>2000000 || !ni || ni>16000000 || ni%3) throw std::runtime_error("Invalid foliage LOD dimensions.");
                const auto verts=take(size_t(nv)*36),indicesData=take(size_t(ni)*4),light=take(size_t(nv)*32),extras=take(size_t(nv)*64);
                finite(verts,size_t(nv)*9);finite(light,size_t(nv)*8);finite(extras,size_t(nv)*16);
                std::vector<UINT> reversed(ni);memcpy(reversed.data(),indicesData,size_t(ni)*4);
                for (UINT index:reversed) if (index>=nv) throw std::runtime_error("Foliage LOD index out of range.");
                Detail detail;detail.indexCount=ni;
                upload(detail.vertices,verts,size_t(nv)*36);upload(detail.indices,indicesData,size_t(ni)*4);
                for (UINT t=0;t<ni/3/2;++t) for (UINT k=0;k<3;++k) std::swap(reversed[3*t+k],reversed[ni-3*(t+1)+k]);
                upload(detail.reversed,reversed.data(),size_t(ni)*4);upload(detail.lighting,light,size_t(nv)*32);upload(detail.extra,extras,size_t(nv)*64);
                detail.view={detail.indices->GetGPUVirtualAddress(),ni*4,DXGI_FORMAT_R32_UINT};
                detail.reverseView={detail.reversed->GetGPUVirtualAddress(),ni*4,DXGI_FORMAT_R32_UINT};
                if (resolution) {
                    if (resolution>2048 || (resolution&(resolution-1))) throw std::runtime_error("Invalid foliage LOD texture size.");
                    const auto maps=take(size_t(resolution)*resolution*materials*12);
                    model.meshBytes+=detailMaps(detail,maps,resolution,materials,modelId,level);
                }
                model.meshBytes+=UINT64(nv)*132+UINT64(ni)*8;model.details.push_back(std::move(detail));
            }
            if (at!=data.size()) throw std::runtime_error("Unexpected trailing foliage LOD data.");
        } else {
            std::vector<float> neutral(size_t(vertices)*16,0.0f);
            for (UINT v=0;v<vertices;++v) for (UINT k=0;k<4;++k) neutral[size_t(v)*16+k]=1;
            upload(model.extra,neutral.data(),neutral.size()*4);model.meshBytes+=neutral.size()*4;
        }
        ms.lodForm[1]=float(model.levelCount|(testLod>=0?((UINT(std::min(testLod,int(model.levelCount)-1))+1u)<<8):0u));
        const auto proxy=Read(folder + L"impostor.bin");
        Settings& ps=model.proxySettings; ps=ms; ps.flags &= ~8u;
        { // the impostor, far away
            if (proxy.size()<52 || memcmp(proxy.data(),"FOLIMP01",8)) throw std::runtime_error("Invalid planetary foliage impostor.");
            ps.viewsX=Field<UINT>(proxy,8); ps.viewsY=Field<UINT>(proxy,12); ps.width=Field<UINT>(proxy,16); ps.height=Field<UINT>(proxy,20);
            memcpy(ps.boundsMin,proxy.data()+24,12); memcpy(ps.boundsMax,proxy.data()+36,12); ps.radius=Field<float>(proxy,48);
            const UINT64 viewCount = UINT64(ps.viewsX) * ps.viewsY;
            if (!viewCount || viewCount > D3D12_REQ_TEXTURE2D_ARRAY_AXIS_DIMENSION || !ps.width || !ps.height ||
                ps.width > D3D12_REQ_TEXTURE2D_U_OR_V_DIMENSION || ps.height > D3D12_REQ_TEXTURE2D_U_OR_V_DIMENSION)
                throw std::runtime_error("Planetary foliage impostor dimensions exceed texture limits.");
            const size_t pixels = size_t(viewCount) * ps.width * ps.height;
            if (pixels>(proxy.size()-52)/20) throw std::runtime_error("Truncated planetary foliage impostor.");
            const UINT views = UINT(viewCount);
            const auto pyramid=ImpostorPyramid(proxy.data()+52,views,ps.width,ps.height);
            const UINT mipCount = UINT(pyramid.size());
            // Each view's coverage at the alpha test kept at every mip, as the meshes' (MeshPyramid).
            std::vector<float> coverageScales(size_t(views)*mipCount,1.0f);
            {
                const size_t baseCount=size_t(ps.width)*ps.height;
                for (UINT view=0;view<views;++view) {
                    const float* base=pyramid[0].pixels.data()+size_t(view)*baseCount*8;
                    size_t hits=0; for (size_t i=0;i<baseCount;++i) if (base[i*8+3]>=0.5f) ++hits;
                    const double target=double(hits)/double(baseCount);
                    for (UINT mip=1;mip<mipCount;++mip) {
                        const ImpostorLevel& level=pyramid[mip]; const size_t count=size_t(level.width)*level.height;
                        coverageScales[size_t(view)*mipCount+mip]=CoverageScale(level.pixels.data()+size_t(view)*count*8,count,8,target);
                    }
                }
            }
            const auto desc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R16G16B16A16_FLOAT,
                ps.width, ps.height, UINT16(views), UINT16(mipCount));
            const auto hp = CD3DX12_HEAP_PROPERTIES(D3D12_HEAP_TYPE_DEFAULT);
            const UINT subresources = views * mipCount;
            std::vector<D3D12_PLACED_SUBRESOURCE_FOOTPRINT> footprints(subresources);
            UINT64 uploadBytes = 0;
            device->GetCopyableFootprints(&desc, 0, subresources, 0, footprints.data(), nullptr, nullptr, &uploadBytes);
            double depthMin=std::numeric_limits<double>::infinity(), depthMax=-std::numeric_limits<double>::infinity(), zeroMoment=0, alphaMax=0, momentMax=0;
            bool finiteDepth=true;
            for (UINT channel = 0; channel < 2; ++channel) {
                Resource& texture = model.impostor[channel];
                Check(device->CreateCommittedResource(&hp, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_COPY_DEST,
                    nullptr, IID_PPV_ARGS(&texture)), "Planetary foliage impostor texture allocation failed.");
                Resource staging = CreateBuffer(device, uploadBytes, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
                unsigned char* mapped = nullptr; CD3DX12_RANGE none(0,0);
                Check(staging->Map(0, &none, reinterpret_cast<void**>(&mapped)), "Planetary foliage texture staging map failed.");
                for (UINT view = 0; view < views; ++view) for (UINT mip = 0; mip < mipCount; ++mip) {
                    const UINT subresource = mip + view * mipCount;
                    const ImpostorLevel& level = pyramid[mip];
                    for (UINT y = 0; y < level.height; ++y) {
                        auto* dst = reinterpret_cast<DirectX::PackedVector::HALF*>(mapped + footprints[subresource].Offset + size_t(y) * footprints[subresource].Footprint.RowPitch);
                        const float* src = level.pixels.data() + ((size_t(view) * level.height + y) * level.width) * 8 + channel * 4;
                        const float coverageScale=coverageScales[size_t(view)*mipCount+mip];
                        for (UINT x = 0; x < level.width; ++x) {
                            const float* sample=src+size_t(x)*8;
                            const float alpha=sample[channel ? -1 : 3];
                            const float adjusted=std::min(alpha*coverageScale,1.0f);
                            const float ratio=alpha > 1e-12f ? adjusted/alpha : 0.0f;
                            for (UINT k = 0; k < 4; ++k) {
                                const float value=channel==0 && k==3 ? adjusted : sample[k]*ratio;
                                dst[x*4+k]=DirectX::PackedVector::XMConvertFloatToHalf(value);
                            }
                            if (channel==1) {
                                // Reconstituer exactement les deux valeurs HALF téléchargées.
                                const float a=DirectX::PackedVector::XMConvertHalfToFloat(DirectX::PackedVector::XMConvertFloatToHalf(adjusted));
                                const float moment=DirectX::PackedVector::XMConvertHalfToFloat(dst[x*4+3]);
                                if (!std::isfinite(a) || a<0 || !std::isfinite(moment)) finiteDepth=false;
                                else { alphaMax=std::max(alphaMax,double(a)); momentMax=std::max(momentMax,std::abs(double(moment))); }
                                if (std::isfinite(a) && a>0 && std::isfinite(moment)) { const double d=double(moment)/double(a); depthMin=std::min(depthMin,d); depthMax=std::max(depthMax,d); }
                                else if (a==0 && std::isfinite(moment)) zeroMoment=std::max(zeroMoment,std::abs(double(moment)));
                            }
                        }
                    }
                    CD3DX12_TEXTURE_COPY_LOCATION dst(texture.Get(), subresource), source(staging.Get(), footprints[subresource]);
                    list->CopyTextureRegion(&dst, 0, 0, 0, &source, nullptr);
                }
                staging->Unmap(0, nullptr);
                auto barrier = CD3DX12_RESOURCE_BARRIER::Transition(texture.Get(), D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
                list->ResourceBarrier(1, &barrier); mUploads.push_back(staging);
                D3D12_SHADER_RESOURCE_VIEW_DESC srv = nullSrv;
                srv.Texture2DArray.MipLevels = mipCount; srv.Texture2DArray.ArraySize = views;
                device->CreateShaderResourceView(texture.Get(), &srv, CD3DX12_CPU_DESCRIPTOR_HANDLE(impostorCpu, modelId * FOLIAGE_MESH_LODS * 7 + channel, descriptorSize));
            }
            if (finiteDepth && std::isfinite(depthMin) && std::isfinite(depthMax)) {
                // L'erreur du filtrage est appliquee apres le melange des vues,
                // avec le minimum d'alpha partage par l'imposteur et sa borne.
                // Hypothese prudente : au plus 64 arrondis float par filtre.
                constexpr double u=1.0/16777216.0, gamma=(64*u)/(1-64*u);
                const double magnitude=std::max(std::abs(depthMin),std::abs(depthMax));
                const double error=gamma*momentMax+magnitude*gamma*alphaMax+zeroMoment;
                const double margin=1e-5*std::max(1.0,magnitude);
                model.depthMin=float(depthMin-margin); model.depthMax=float(depthMax+margin);
                model.depthError=float(error*(1.0+1e-5)+1e-12);
                model.depthValid=std::isfinite(model.depthMin) && std::isfinite(model.depthMax) && std::isfinite(model.depthError);
                if (model.depthValid) { ps.depthBounds[0]=model.depthMin; ps.depthBounds[1]=model.depthMax; ps.depthBounds[2]=1.0f; ps.depthBounds[3]=model.depthError; }
            }
            const std::wstring lightPath=folder+L"impostor_light.bin";
            const DWORD lightAttr=GetFileAttributesW(lightPath.c_str());
            if (lightAttr!=INVALID_FILE_ATTRIBUTES) {
                if (lightAttr&FILE_ATTRIBUTE_DIRECTORY) throw std::runtime_error("Invalid foliage impostor lighting file.");
                const auto light=Read(lightPath);
                if (light.size()!=24+pixels*8 || memcmp(light.data(),"FOLIL001",8) ||
                    Field<UINT>(light,8)!=ps.viewsX || Field<UINT>(light,12)!=ps.viewsY ||
                    Field<UINT>(light,16)!=ps.width || Field<UINT>(light,20)!=ps.height)
                    throw std::runtime_error("Invalid foliage impostor lighting data.");
                const auto lightLevels=ImpostorLightPyramid(light.data()+24,proxy.data()+52,views,ps.width,ps.height);
                const auto lightDesc=CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R8G8B8A8_UNORM,
                    ps.width,ps.height,UINT16(views),UINT16(mipCount));
                std::vector<D3D12_PLACED_SUBRESOURCE_FOOTPRINT> lightFootprints(subresources); UINT64 lightBytes=0;
                device->GetCopyableFootprints(&lightDesc,0,subresources,0,lightFootprints.data(),nullptr,nullptr,&lightBytes);
                for (UINT channel=0;channel<2;++channel) {
                    Resource& texture=model.impostorLighting[channel];
                    Check(device->CreateCommittedResource(&hp,D3D12_HEAP_FLAG_NONE,&lightDesc,D3D12_RESOURCE_STATE_COPY_DEST,
                        nullptr,IID_PPV_ARGS(&texture)),"Foliage impostor lighting texture allocation failed.");
                    Resource staging=CreateBuffer(device,lightBytes,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
                    unsigned char* mapped=nullptr; CD3DX12_RANGE none(0,0);
                    Check(staging->Map(0,&none,reinterpret_cast<void**>(&mapped)),"Foliage impostor lighting staging map failed.");
                    for (UINT view=0;view<views;++view) for (UINT mip=0;mip<mipCount;++mip) {
                        const UINT subresource=mip+view*mipCount;
                        const ImpostorLevel& level=lightLevels[mip]; const ImpostorLevel& alphaLevel=pyramid[mip];
                        const float coverageScale=coverageScales[size_t(view)*mipCount+mip];
                        for (UINT y=0;y<level.height;++y) {
                            unsigned char* dst=mapped+lightFootprints[subresource].Offset+size_t(y)*lightFootprints[subresource].Footprint.RowPitch;
                            for (UINT x=0;x<level.width;++x) {
                                const size_t index=((size_t(view)*level.height+y)*level.width+x)*8;
                                const float alpha=alphaLevel.pixels[index+3];
                                const float ratio=alpha>1e-12f ? std::min(alpha*coverageScale,1.0f)/alpha : 0.0f;
                                for (UINT k=0;k<4;++k) dst[x*4+k]=ByteF(level.pixels[index+channel*4+k]*ratio);
                            }
                        }
                        CD3DX12_TEXTURE_COPY_LOCATION dst(texture.Get(),subresource),src(staging.Get(),lightFootprints[subresource]);
                        list->CopyTextureRegion(&dst,0,0,0,&src,nullptr);
                    }
                    staging->Unmap(0,nullptr);
                    auto barrier=CD3DX12_RESOURCE_BARRIER::Transition(texture.Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
                    list->ResourceBarrier(1,&barrier); mUploads.push_back(staging);
                    D3D12_SHADER_RESOURCE_VIEW_DESC srv=nullSrv; srv.Format=DXGI_FORMAT_R8G8B8A8_UNORM;
                    srv.Texture2DArray.MipLevels=mipCount; srv.Texture2DArray.ArraySize=views;
                    device->CreateShaderResourceView(texture.Get(),&srv,CD3DX12_CPU_DESCRIPTOR_HANDLE(impostorCpu,modelId*FOLIAGE_MESH_LODS*7+5+channel,descriptorSize));
                }
                for (const auto& level:lightLevels) model.proxyBytes+=UINT64(views)*level.width*level.height*8;
                ps.flags|=8u;
            } else if (GetLastError()!=ERROR_FILE_NOT_FOUND && GetLastError()!=ERROR_PATH_NOT_FOUND)
                throw std::runtime_error("Cannot inspect foliage impostor lighting file.");
            for (const auto& level : pyramid) model.proxyBytes += UINT64(views) * level.width * level.height * 16;
        }
        for (UINT level=1;level<FOLIAGE_MESH_LODS;++level) {
            mImpostorTables[modelId][level]=CD3DX12_GPU_DESCRIPTOR_HANDLE(impostorGpu,(modelId*FOLIAGE_MESH_LODS+level)*7,descriptorSize);
            for (UINT channel=0;channel<7;++channel) {
                const bool ownMaps=level<model.levelCount && model.details[level-1].textureSize>0;
                if (ownMaps && channel>=2 && channel<=4) continue;
                device->CopyDescriptorsSimple(1,CD3DX12_CPU_DESCRIPTOR_HANDLE(impostorCpu,(modelId*FOLIAGE_MESH_LODS+level)*7+channel,descriptorSize),CD3DX12_CPU_DESCRIPTOR_HANDLE(impostorCpu,modelId*FOLIAGE_MESH_LODS*7+channel,descriptorSize),D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
            }
        }
    }
    const UINT quadIndices[6]={0,1,2,2,1,3};
    upload(mQuadIndices,quadIndices,sizeof(quadIndices));
    mQuadView={mQuadIndices->GetGPUVirtualAddress(),sizeof(quadIndices),DXGI_FORMAT_R32_UINT};
    mQueues=CreateBuffer(device,UINT64(Queues)*QueueCapacity*64,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mMeshOrder=CreateBuffer(device,UINT64(3)*2*QueueCapacity*4,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    UINT levelCounts[MaxModels];for (UINT m=0;m<MaxModels;++m) levelCounts[m]=std::max(1u,UINT(mModel[m].meshSettings.lodForm[1]));
    upload(mLevelCounts,levelCounts,sizeof(levelCounts));
    mArguments=CreateBuffer(device,CounterBytes,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT | D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mReset=CreateBuffer(device,CounterBytes,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
    mReadback=CreateBuffer(device,CounterBytes,D3D12_HEAP_TYPE_READBACK,D3D12_RESOURCE_STATE_COPY_DEST);
    UINT* reset=nullptr; CD3DX12_RANGE none(0,0); Check(mReset->Map(0,&none,reinterpret_cast<void**>(&reset)),"Planetary foliage reset map failed.");
    std::fill(reset,reset+CounterBytes/sizeof(UINT),0u);
    for (UINT m=0;m<MaxModels;++m) {
        for (UINT level=0;level<FOLIAGE_MESH_LODS;++level)
            reset[(m*FOLIAGE_REPRESENTATIONS+level)*7+2]=level==0?mModel[m].meshIndexCount:level<mModel[m].levelCount?mModel[m].details[level-1].indexCount:0;
        reset[(m*FOLIAGE_REPRESENTATIONS+FOLIAGE_MESH_LODS)*7+2]=6;
    }
    mReset->Unmap(0,nullptr);

    CD3DX12_ROOT_PARAMETER cp[9]; cp[0].InitAsConstantBufferView(0); cp[1].InitAsShaderResourceView(0);
    cp[2].InitAsShaderResourceView(1); cp[3].InitAsShaderResourceView(2); cp[4].InitAsUnorderedAccessView(0);
    cp[5].InitAsUnorderedAccessView(1); cp[6].InitAsConstants(4,1);cp[7].InitAsShaderResourceView(3);cp[8].InitAsUnorderedAccessView(2);
    mClassifyRoot=CreateRootSignature(device,CD3DX12_ROOT_SIGNATURE_DESC(9,cp));
    auto classify=LoadShader(L"PlanetFoliageClassify.cso"), finalize=LoadShader(L"PlanetFoliageFinalize.cso"), scatter=LoadShader(L"PlanetFoliageScatter.cso");
    D3D12_COMPUTE_PIPELINE_STATE_DESC c={}; c.pRootSignature=mClassifyRoot.Get(); c.CS=CD3DX12_SHADER_BYTECODE(classify.Get());
    Check(device->CreateComputePipelineState(&c,IID_PPV_ARGS(&mClassifyPso)),"Planetary foliage classifier failed.");
    c.CS=CD3DX12_SHADER_BYTECODE(finalize.Get());
    Check(device->CreateComputePipelineState(&c,IID_PPV_ARGS(&mFinalizePso)),"Planetary foliage finalizer failed.");
    c.CS=CD3DX12_SHADER_BYTECODE(scatter.Get());
    Check(device->CreateComputePipelineState(&c,IID_PPV_ARGS(&mScatterPso)),"Planetary foliage scatter failed.");
    // La SRV du vertex reste valide aussi sans le HiZ (vues de diagnostic).
    constexpr UINT visibilityBytes=(1u<<20)/8;
    mVisibility=CreateBuffer(device,visibilityBytes,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    Resource visibilityUpload=CreateBuffer(device,visibilityBytes,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
    void* visibilityData=nullptr; CD3DX12_RANGE noRead(0,0);
    Check(visibilityUpload->Map(0,&noRead,&visibilityData),"Foliage visibility initialization failed.");
    memset(visibilityData,0,visibilityBytes); visibilityUpload->Unmap(0,nullptr);
    list->CopyResource(mVisibility.Get(),visibilityUpload.Get());
    auto visibilityReady=CD3DX12_RESOURCE_BARRIER::Transition(mVisibility.Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
    list->ResourceBarrier(1,&visibilityReady); mUploads.push_back(visibilityUpload);
    {
        Settings models[MaxModels]={};
        for (UINT id=0;id<MaxModels;++id) models[id]=mModel[id].proxySettings; // la borne de profondeur comprise
        upload(mCullModels,models,sizeof(models));
        mCullStats=CreateBuffer(device,12,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
        mCullReadback=CreateBuffer(device,12,D3D12_HEAP_TYPE_READBACK,D3D12_RESOURCE_STATE_COPY_DEST);
        CD3DX12_DESCRIPTOR_RANGE hizRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,2);
        CD3DX12_ROOT_PARAMETER hp[7]; hp[0].InitAsConstantBufferView(0); hp[1].InitAsShaderResourceView(0);
        hp[2].InitAsShaderResourceView(1); hp[3].InitAsShaderResourceView(3);
        hp[4].InitAsUnorderedAccessView(0); hp[5].InitAsUnorderedAccessView(1);
        hp[6].InitAsDescriptorTable(1,&hizRange);
        CD3DX12_ROOT_PARAMETER params[8]; for (UINT i=0;i<7;++i) params[i]=hp[i]; params[7].InitAsConstants(5,1);
        mCullRoot=CreateRootSignature(device,CD3DX12_ROOT_SIGNATURE_DESC(8,params));
        auto clear=LoadShader(L"PlanetFoliageHiZClear.cso"), cull=LoadShader(L"PlanetFoliageHiZCull.cso"), count=LoadShader(L"PlanetFoliageHiZCount.cso");
        D3D12_COMPUTE_PIPELINE_STATE_DESC h={}; h.pRootSignature=mCullRoot.Get(); h.CS=CD3DX12_SHADER_BYTECODE(clear.Get());
        Check(device->CreateComputePipelineState(&h,IID_PPV_ARGS(&mCullClearPso)),"Foliage HiZ clear failed.");
        h.CS=CD3DX12_SHADER_BYTECODE(cull.Get());
        Check(device->CreateComputePipelineState(&h,IID_PPV_ARGS(&mCullPso)),"Foliage HiZ culling pipeline failed.");
        h.CS=CD3DX12_SHADER_BYTECODE(count.Get());
        Check(device->CreateComputePipelineState(&h,IID_PPV_ARGS(&mCullCountPso)),"Foliage HiZ count pipeline failed.");
    }
    // The draws: the frame, the plants, the mesh's vertices, the model's settings, the atmosphere's tables, the planet map,
    // the model's textures, its vertices' precomputed light, the impostors left visible by the HiZ.
    CD3DX12_DESCRIPTOR_RANGE lutRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,3,1), mapRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,29), impostorRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,7,32);
    CD3DX12_ROOT_PARAMETER gp[11]; gp[0].InitAsConstantBufferView(0); gp[1].InitAsShaderResourceView(0);
    gp[2].InitAsShaderResourceView(30); gp[3].InitAsConstants(sizeof(Settings)/4,1);
    gp[4].InitAsDescriptorTable(1,&lutRange,D3D12_SHADER_VISIBILITY_PIXEL); gp[5].InitAsDescriptorTable(1,&mapRange,D3D12_SHADER_VISIBILITY_PIXEL);
    gp[6].InitAsDescriptorTable(1,&impostorRange,D3D12_SHADER_VISIBILITY_PIXEL);
    gp[7].InitAsShaderResourceView(39,0,D3D12_SHADER_VISIBILITY_VERTEX);
    gp[8].InitAsShaderResourceView(41,0,D3D12_SHADER_VISIBILITY_VERTEX);
    gp[9].InitAsShaderResourceView(42,0,D3D12_SHADER_VISIBILITY_VERTEX);gp[10].InitAsShaderResourceView(43,0,D3D12_SHADER_VISIBILITY_VERTEX);
    const CD3DX12_STATIC_SAMPLER_DESC samplers[2] = {
        CD3DX12_STATIC_SAMPLER_DESC(0,D3D12_FILTER_MIN_MAG_MIP_LINEAR,D3D12_TEXTURE_ADDRESS_MODE_CLAMP,D3D12_TEXTURE_ADDRESS_MODE_CLAMP,D3D12_TEXTURE_ADDRESS_MODE_CLAMP),
        CD3DX12_STATIC_SAMPLER_DESC(1,D3D12_FILTER_ANISOTROPIC,D3D12_TEXTURE_ADDRESS_MODE_WRAP,D3D12_TEXTURE_ADDRESS_MODE_WRAP,D3D12_TEXTURE_ADDRESS_MODE_WRAP,0,8)
    };
    mDrawRoot=CreateRootSignature(device,CD3DX12_ROOT_SIGNATURE_DESC(11,gp,2,samplers));
    auto proxyVs=LoadShader(L"PlanetFoliageProxyVertex.cso"), proxyPs=LoadShader(L"PlanetFoliageImpostorPixel.cso");
    D3D12_GRAPHICS_PIPELINE_STATE_DESC p={}; p.pRootSignature=mDrawRoot.Get();
    p.VS=CD3DX12_SHADER_BYTECODE(proxyVs.Get()); p.PS=CD3DX12_SHADER_BYTECODE(proxyPs.Get());
    p.RasterizerState=CD3DX12_RASTERIZER_DESC(D3D12_DEFAULT); p.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;
    p.BlendState=CD3DX12_BLEND_DESC(D3D12_DEFAULT); p.DepthStencilState=CD3DX12_DEPTH_STENCIL_DESC(D3D12_DEFAULT);
    p.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_GREATER; p.SampleMask=UINT_MAX; p.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
    p.NumRenderTargets=2; p.RTVFormats[0]=hdr; p.RTVFormats[1]=sun; p.DSVFormat=depth; p.SampleDesc.Count=1;
    Check(device->CreateGraphicsPipelineState(&p,IID_PPV_ARGS(&mProxyPso)),"Planetary foliage proxy pipeline failed.");
    {
        // La profondeur seule, mêmes sommets et mêmes rejets alpha ; puis la couleur où elle est restée égale.
        auto vs=LoadShader(L"PlanetFoliageMeshVertex.cso"), depthOnly=LoadShader(L"PlanetFoliageMeshDepthPixel.cso"),
             shade=LoadShader(L"PlanetFoliageMeshHardwarePixel.cso");
        p.VS=CD3DX12_SHADER_BYTECODE(vs.Get()); p.PS=CD3DX12_SHADER_BYTECODE(shade.Get());
        D3D12_GRAPHICS_PIPELINE_STATE_DESC d=p; d.PS=CD3DX12_SHADER_BYTECODE(depthOnly.Get());
        for (UINT t=0;t<2;++t) d.BlendState.RenderTarget[t].RenderTargetWriteMask=0;
        Check(device->CreateGraphicsPipelineState(&d,IID_PPV_ARGS(&mMeshDepthPso)),"Planetary foliage mesh depth pipeline failed.");
        D3D12_GRAPHICS_PIPELINE_STATE_DESC e=p;
        e.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_EQUAL; e.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ZERO;
        Check(device->CreateGraphicsPipelineState(&e,IID_PPV_ARGS(&mMeshShadePso)),"Planetary foliage mesh shading pipeline failed.");
    }
    D3D12_INDIRECT_ARGUMENT_DESC arg[2]={}; arg[0].Type=D3D12_INDIRECT_ARGUMENT_TYPE_SHADER_RESOURCE_VIEW;
    arg[0].ShaderResourceView.RootParameterIndex=1; arg[1].Type=D3D12_INDIRECT_ARGUMENT_TYPE_DRAW_INDEXED;
    D3D12_COMMAND_SIGNATURE_DESC sig={}; sig.ByteStride=ArgStride; sig.NumArgumentDescs=2; sig.pArgumentDescs=arg;
    Check(device->CreateCommandSignature(&sig,mDrawRoot.Get(),IID_PPV_ARGS(&mIndirect)),"Planetary foliage indirect signature failed.");
    arg[0].ShaderResourceView.RootParameterIndex=9;
    Check(device->CreateCommandSignature(&sig,mDrawRoot.Get(),IID_PPV_ARGS(&mMeshIndirect)),"Foliage mesh LOD signature failed.");
    mReady=true;
}

void PlanetFoliage::Classify(ID3D12GraphicsCommandList* list, D3D12_GPU_VIRTUAL_ADDRESS frame,
                              ID3D12Resource* instances, ID3D12Resource* sourceCounters) {
    if (!Enabled()) return;
    mHiZFrame=false;
    constexpr D3D12_RESOURCE_STATES inputCount = D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT | D3D12_RESOURCE_STATE_COPY_SOURCE;
    const D3D12_RESOURCE_BARRIER before[2]={
        CD3DX12_RESOURCE_BARRIER::Transition(sourceCounters,inputCount,inputCount | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mArguments.Get(),inputCount,D3D12_RESOURCE_STATE_COPY_DEST) };
    list->ResourceBarrier(2,before); list->CopyResource(mArguments.Get(),mReset.Get());
    auto writable=CD3DX12_RESOURCE_BARRIER::Transition(mArguments.Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    list->ResourceBarrier(1,&writable);
    list->SetComputeRootSignature(mClassifyRoot.Get()); list->SetPipelineState(mClassifyPso.Get());
    list->SetComputeRootConstantBufferView(0,frame);
    list->SetComputeRootShaderResourceView(1,instances->GetGPUVirtualAddress()+UINT64(2)*SourceCapacity*64);
    list->SetComputeRootShaderResourceView(2,instances->GetGPUVirtualAddress()+UINT64(3)*SourceCapacity*64);
    list->SetComputeRootShaderResourceView(3,sourceCounters->GetGPUVirtualAddress());
    list->SetComputeRootUnorderedAccessView(4,mQueues->GetGPUVirtualAddress()); list->SetComputeRootUnorderedAccessView(5,mArguments->GetGPUVirtualAddress());
    const UINT64 address=mQueues->GetGPUVirtualAddress();
    const UINT64 order=mMeshOrder->GetGPUVirtualAddress();
    const UINT classifyConstants[4]={UINT(address),UINT(address>>32),UINT(order),UINT(order>>32)};
    list->SetComputeRootShaderResourceView(7,mLevelCounts->GetGPUVirtualAddress());
    list->SetComputeRootUnorderedAccessView(8,mMeshOrder->GetGPUVirtualAddress());
    list->SetComputeRoot32BitConstants(6,4,classifyConstants,0); list->Dispatch((2*SourceCapacity+63)/64,1,1);
    auto barrier=CD3DX12_RESOURCE_BARRIER::UAV(mArguments.Get()); list->ResourceBarrier(1,&barrier);
    list->SetPipelineState(mFinalizePso.Get()); list->Dispatch(1,1,1);
    list->ResourceBarrier(1,&barrier);
    list->SetPipelineState(mScatterPso.Get()); list->Dispatch((2*SourceCapacity+63)/64,1,1);
    const D3D12_RESOURCE_BARRIER after[4]={
        CD3DX12_RESOURCE_BARRIER::Transition(mMeshOrder.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mArguments.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,inputCount),
        CD3DX12_RESOURCE_BARRIER::Transition(mQueues.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(sourceCounters,inputCount | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,inputCount) };
    list->ResourceBarrier(4,after); list->CopyResource(mReadback.Get(),mArguments.Get());
}

void PlanetFoliage::DrawRepresentation(ID3D12GraphicsCommandList* list, D3D12_GPU_VIRTUAL_ADDRESS frame,
    D3D12_GPU_DESCRIPTOR_HANDLE atmosphere, D3D12_GPU_DESCRIPTOR_HANDLE planetMap, UINT rep, bool masked) {
    list->SetGraphicsRootSignature(mDrawRoot.Get()); list->SetGraphicsRootConstantBufferView(0,frame);
    list->SetGraphicsRootDescriptorTable(4,atmosphere); list->SetGraphicsRootDescriptorTable(5,planetMap);
    list->SetGraphicsRootShaderResourceView(8,mVisibility->GetGPUVirtualAddress());
    list->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    // Les maillages en profondeur matérielle : leur profondeur d'abord, leur couleur ensuite, une fois par pixel montré
    // (optimisation.md, round 3).
    for (UINT pass=0;pass<(rep ? 1u : 2u);++pass) {
    list->SetPipelineState(rep ? mProxyPso.Get() : pass ? mMeshShadePso.Get() : mMeshDepthPso.Get());
    for (UINT modelId=0;modelId<mModelCount;++modelId) {
        const Model& model=mModel[modelId];
        for (UINT level=0;level<(rep?1u:model.levelCount);++level) {
            const Detail* detail=(!rep && level)?&model.details[level-1]:nullptr;
            list->SetGraphicsRootShaderResourceView(1,mQueues->GetGPUVirtualAddress()+UINT64(model.meshSettings.species*2)*QueueCapacity*64);
            list->SetGraphicsRootShaderResourceView(2,detail?detail->vertices->GetGPUVirtualAddress():model.meshVertices->GetGPUVirtualAddress());
            list->SetGraphicsRootDescriptorTable(6,mImpostorTables[modelId][rep?0:level]);
            list->SetGraphicsRootShaderResourceView(7,detail?detail->lighting->GetGPUVirtualAddress():model.meshLighting->GetGPUVirtualAddress());
            list->SetGraphicsRootShaderResourceView(9,mMeshOrder->GetGPUVirtualAddress());
            list->SetGraphicsRootShaderResourceView(10,detail?detail->extra->GetGPUVirtualAddress():model.extra->GetGPUVirtualAddress());
            Settings settings=rep?model.proxySettings:model.meshSettings;settings.lodForm[0]=float(level);
            if (masked && rep) settings.flags|=16u;
            list->SetGraphicsRoot32BitConstants(3,sizeof(Settings)/4,&settings,0);
            const auto& view=rep?mQuadView:detail?(pass?detail->reverseView:detail->view):(pass?model.meshReversedView:model.meshView);
            list->IASetIndexBuffer(&view);
            const UINT64 offset=UINT64(modelId*FOLIAGE_REPRESENTATIONS+(rep?FOLIAGE_MESH_LODS:level))*ArgStride;
            list->ExecuteIndirect(rep?mIndirect.Get():mMeshIndirect.Get(),1,mArguments.Get(),offset,mArguments.Get(),offset+12);
        }
    }
    }
}
void PlanetFoliage::Draw(ID3D12GraphicsCommandList* list,D3D12_GPU_VIRTUAL_ADDRESS frame,
    D3D12_GPU_DESCRIPTOR_HANDLE atmosphere,D3D12_GPU_DESCRIPTOR_HANDLE planetMap) {
    if (!Enabled()) return;
    DrawRepresentation(list,frame,atmosphere,planetMap,0,false);
    DrawRepresentation(list,frame,atmosphere,planetMap,1,false);
    auto writable=CD3DX12_RESOURCE_BARRIER::Transition(mQueues.Get(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    list->ResourceBarrier(1,&writable);
    auto orderWritable=CD3DX12_RESOURCE_BARRIER::Transition(mMeshOrder.Get(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    list->ResourceBarrier(1,&orderWritable);
}
void PlanetFoliage::DrawOccluders(ID3D12GraphicsCommandList* list,D3D12_GPU_VIRTUAL_ADDRESS frame,
    D3D12_GPU_DESCRIPTOR_HANDLE atmosphere,D3D12_GPU_DESCRIPTOR_HANDLE planetMap) {
    if (Enabled()) DrawRepresentation(list,frame,atmosphere,planetMap,0,false);
}
void PlanetFoliage::CullOccluded(ID3D12GraphicsCommandList* list,D3D12_GPU_VIRTUAL_ADDRESS frame,
    D3D12_GPU_DESCRIPTOR_HANDLE hiz,UINT width,UINT height,UINT mips,UINT viewportWidth,UINT viewportHeight) {
    if (!Enabled()) return;
    mHiZFrame=true;
    constexpr D3D12_RESOURCE_STATES indirectRead=D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT | D3D12_RESOURCE_STATE_COPY_SOURCE;
    const D3D12_RESOURCE_BARRIER before[2]={
        CD3DX12_RESOURCE_BARRIER::Transition(mVisibility.Get(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
        CD3DX12_RESOURCE_BARRIER::Transition(mArguments.Get(),indirectRead,indirectRead | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE)};
    list->ResourceBarrier(2,before);
    list->SetComputeRootSignature(mCullRoot.Get()); list->SetComputeRootConstantBufferView(0,frame);
    list->SetComputeRootShaderResourceView(1,mQueues->GetGPUVirtualAddress());
    list->SetComputeRootShaderResourceView(2,mArguments->GetGPUVirtualAddress());
    list->SetComputeRootShaderResourceView(3,mCullModels->GetGPUVirtualAddress());
    list->SetComputeRootUnorderedAccessView(4,mVisibility->GetGPUVirtualAddress());
    list->SetComputeRootUnorderedAccessView(5,mCullStats->GetGPUVirtualAddress());
    list->SetComputeRootDescriptorTable(6,hiz);
    const UINT constants[5]={width,height,mips,viewportWidth,viewportHeight};
    list->SetComputeRoot32BitConstants(7,5,constants,0);
    list->SetPipelineState(mCullClearPso.Get()); list->Dispatch(512,1,1);
    const D3D12_RESOURCE_BARRIER cleared[2]={CD3DX12_RESOURCE_BARRIER::UAV(mVisibility.Get()),CD3DX12_RESOURCE_BARRIER::UAV(mCullStats.Get())};
    list->ResourceBarrier(2,cleared);
    list->SetPipelineState(mCullPso.Get()); list->Dispatch(QueueCapacity/64,3,1);
    const D3D12_RESOURCE_BARRIER masked[2]={CD3DX12_RESOURCE_BARRIER::UAV(mVisibility.Get()),CD3DX12_RESOURCE_BARRIER::UAV(mCullStats.Get())};
    list->ResourceBarrier(2,masked);
    list->SetPipelineState(mCullCountPso.Get()); list->Dispatch(QueueCapacity/64,3,1);
    const D3D12_RESOURCE_BARRIER after[3]={
        CD3DX12_RESOURCE_BARRIER::Transition(mVisibility.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mArguments.Get(),indirectRead | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,indirectRead),
        CD3DX12_RESOURCE_BARRIER::Transition(mCullStats.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_COPY_SOURCE)};
    list->ResourceBarrier(3,after); list->CopyResource(mCullReadback.Get(),mCullStats.Get());
    auto statsWrite=CD3DX12_RESOURCE_BARRIER::Transition(mCullStats.Get(),D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    list->ResourceBarrier(1,&statsWrite);
}
void PlanetFoliage::DrawRemaining(ID3D12GraphicsCommandList* list,D3D12_GPU_VIRTUAL_ADDRESS frame,
    D3D12_GPU_DESCRIPTOR_HANDLE atmosphere,D3D12_GPU_DESCRIPTOR_HANDLE planetMap) {
    if (!Enabled()) return;
    DrawRepresentation(list,frame,atmosphere,planetMap,1,true);
    auto writable=CD3DX12_RESOURCE_BARRIER::Transition(mQueues.Get(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    list->ResourceBarrier(1,&writable);
    auto orderWritable=CD3DX12_RESOURCE_BARRIER::Transition(mMeshOrder.Get(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    list->ResourceBarrier(1,&orderWritable);
}

void PlanetFoliage::ReadStats() {
    if (!Enabled()) return;
    UINT* values=nullptr; CD3DX12_RANGE range(0,CounterBytes);
    if (SUCCEEDED(mReadback->Map(0,&range,reinterpret_cast<void**>(&values)))) {
        for (UINT q=0;q<Queues;++q) { mStats[q*5+1]=values[FOLIAGE_AGGREGATE_COUNTS/4+q]; mStats[30+q]=values[FOLIAGE_OVERFLOW/4+q]; }
        for (UINT model=0;model<MaxModels;++model) {
            mModelStats[model*2]=values[FOLIAGE_UNIQUE_COUNTS/4+model];
            mModelStats[model*2+1]=values[(model*FOLIAGE_REPRESENTATIONS+FOLIAGE_MESH_LODS)*7+3];
            for (UINT level=0;level<FOLIAGE_MESH_LODS;++level) mLevelStats[model*FOLIAGE_MESH_LODS+level]=values[(model*FOLIAGE_REPRESENTATIONS+level)*7+3];
        }
        const CD3DX12_RANGE none(0,0); mReadback->Unmap(0,&none);
    }
    mTested=mRejectedCandidates=mRejected=0;
    if (mHiZFrame) {
        UINT* h=nullptr; CD3DX12_RANGE cullRange(0,12);
        if (SUCCEEDED(mCullReadback->Map(0,&cullRange,reinterpret_cast<void**>(&h)))) {
            mTested=h[0]; mRejectedCandidates=h[1]; mRejected=h[2];
            const CD3DX12_RANGE none(0,0); mCullReadback->Unmap(0,&none);
        }
    }
}
std::wstring PlanetFoliage::StatsText() const {
    if (!Enabled()) return L"";
    wchar_t text[256];
    swprintf_s(text,L" | feuillage : sapin %u/%u, feuillu %u/%u, arbuste %u/%u (mesh/proxy), depassement %u",
        mStats[1],mStats[6],mStats[11],mStats[16],mStats[21],mStats[26],mStats[30]+mStats[31]+mStats[32]+mStats[33]+mStats[34]+mStats[35]);
    return text;
}
// Beside a capture, for the benches (tools/banc_arbustes_climat.py, which checks the representation's names).
void PlanetFoliage::SaveStats(const std::wstring& capture,double placement,double draw,double total,const std::vector<Sample>& samples) const {
    if (!Enabled()) return; FILE* f=nullptr;
    if (_wfopen_s(&f,(capture+L".planet-foliage.json").c_str(),L"wb") || !f) return;
    UINT activeCommands=0;
    for (UINT model=0;model<MaxModels;++model) {
        if (mModelStats[model*2+1]) ++activeCommands;
        for (UINT level=0;level<FOLIAGE_MESH_LODS;++level) if (mLevelStats[model*FOLIAGE_MESH_LODS+level]) ++activeCommands;
    }
    fprintf(f,"{\"mode\":\"hybrid-impostor\",\"models\":\"game\",\"volume_strength\":%.6f,\"climate_shrubs\":true,\"queue_bytes\":%llu,\"capacity_per_queue\":%u,\"active_commands\":%u,\"counts\":[",
        VolumeStrength,(unsigned long long)(UINT64(Queues)*QueueCapacity*64),QueueCapacity,activeCommands);
    for (UINT q=0;q<Queues;++q) fprintf(f,"%s%u",q ? "," : "",mStats[q*5+1]);
    fprintf(f,"],\"overflow\":[");
    for (UINT q=0;q<Queues;++q) fprintf(f,"%s%u",q ? "," : "",mStats[Queues*5+q]);
    const UINT proxyCount=mStats[6]+mStats[16]+mStats[26];
    const UINT meshCount=mStats[1]+mStats[11]+mStats[21];
    fprintf(f,"],\"hiz_enabled\":%s,\"hiz_active\":%s,\"hiz_tested\":%u,\"hiz_rejected_candidates\":%u,\"hiz_rejected\":%u,\"hiz_drawn\":%u,\"hiz_occluders\":%u",
        mHiZFrame ? "true" : "false",mHiZFrame ? "true" : "false",mTested,mRejectedCandidates,mRejected,proxyCount-std::min(proxyCount,mRejected),mHiZFrame ? meshCount : 0);
    fprintf(f,",\"representation_bytes\":[");
    for (UINT model=0;model<mModelCount;++model) fprintf(f,"%s%llu,%llu",model ? "," : "",
        (unsigned long long)mModel[model].meshBytes,(unsigned long long)mModel[model].proxyBytes);
    fprintf(f,"],\"model_counts\":[");
    for (UINT model=0;model<mModelCount;++model) fprintf(f,"%s[%u,%u]",model ? "," : "",mModelStats[2*model],mModelStats[2*model+1]);
    fprintf(f,"],\"diverse_biomes\":%s,\"model_names\":[",mDiverse?"true":"false");
    for (size_t i=0;i<mModelNames.size();++i) fprintf(f,"%s\"%s\"",i?",":"",mModelNames[i].c_str());
    fprintf(f,"],\"family_counts\":[");
    for (UINT family=0;family<6;++family) {
        const UINT first=2+2*family;
        fprintf(f,"%s[%u,%u]",family ? "," : "",mModelStats[2*first]+mModelStats[2*(first+1)],
            mModelStats[2*first+1]+mModelStats[2*(first+1)+1]);
    }
    fprintf(f,"],\"volume_sidecars\":[");
    for (UINT model=0;model<mModelCount;++model) fprintf(f,"%s%u,%u",model ? "," : "",
        (mModel[model].meshSettings.flags&8u) ? 1u : 0u,(mModel[model].proxySettings.flags&8u) ? 1u : 0u);
    fprintf(f,"],\"mesh_order_bytes\":%u,\"mesh_lod_counts\":[",3u*2u*QueueCapacity*4u);
    for (UINT model=0;model<mModelCount;++model) {
        fprintf(f,"%s[",model?",":"");
        for (UINT level=0;level<FOLIAGE_MESH_LODS;++level) fprintf(f,"%s%u",level?",":"",mLevelStats[model*FOLIAGE_MESH_LODS+level]);
        fprintf(f,"]");
    }
    fprintf(f,"],\"mesh_lod_triangles\":[");
    for (UINT model=0;model<mModelCount;++model) {
        fprintf(f,"%s[",model?",":"");
        for (UINT level=0;level<FOLIAGE_MESH_LODS;++level) fprintf(f,"%s%u",level?",":"",level==0?mModel[model].meshIndexCount/3:level<mModel[model].levelCount?mModel[model].details[level-1].indexCount/3:0);
        fprintf(f,"]");
    }
    fprintf(f,"],\"art_directed\":%s,\"gpu_ms\":{\"placement\":%.9f,\"draw\":%.9f,\"total_frame\":%.9f},\"gpu_samples_ms\":[",mArtDirected?"true":"false",placement,draw,total);
    for(size_t i=0;i<samples.size();++i) fprintf(f,"%s[%.9f,%.9f,%.9f]",i?",":"",samples[i].placement,samples[i].draw,samples[i].total);
    fprintf(f,"],\"source_placement_samples_ms\":[");
    for(size_t i=0;i<samples.size();++i) fprintf(f,"%s%.9f",i?",":"",samples[i].sourcePlacement);
    fprintf(f,"],\"hiz_gpu_samples_ms\":[");
    for(size_t i=0;i<samples.size();++i) fprintf(f,"%s[%.9f,%.9f]",i?",":"",samples[i].hizBuild,samples[i].hizCull);
    fprintf(f,"],\"hiz_active_samples\":[");
    for(size_t i=0;i<samples.size();++i) fprintf(f,"%s%s",i?",":"",samples[i].hizActive ? "true" : "false");
    fprintf(f,"]}\n"); fclose(f);
}
