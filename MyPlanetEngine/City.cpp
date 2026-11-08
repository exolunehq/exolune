#include "City.h"
#include "GpuHelpers.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <map>

using namespace DirectX;
using Microsoft::WRL::ComPtr;
namespace {
struct Reader {
    std::ifstream file;
    explicit Reader(const std::wstring& path):file(path,std::ios::binary) { if(!file)throw std::runtime_error("City asset missing."); }
    void bytes(void* p,size_t n) { if(!file.read(static_cast<char*>(p),n))throw std::runtime_error("City asset truncated."); }
    template<class T>T read(){T v;bytes(&v,sizeof(v));return v;}
    void magic(const char* expected){char m[8];bytes(m,8);if(memcmp(m,expected,8))throw std::runtime_error("Unsupported city format.");}
    void end(){if(file.peek()!=EOF)throw std::runtime_error("Unexpected city trailing data.");}
};
float Size(const XMFLOAT3& a,const XMFLOAT3& b){return std::max({b.x-a.x,b.y-a.y,b.z-a.z});}
bool Ground(const std::string& name){return name=="streets"||name.rfind("ground_",0)==0;}
}

XMMATRIX City::Shadow() const { return mFrame?XMMatrixTranspose(XMLoadFloat4x4(&mFrame->shadow)):XMMatrixIdentity(); }

void City::Initialize(ID3D12Device* device,ID3D12GraphicsCommandList* cmd,ID3D12DescriptorHeap* heap,UINT base,
                      const std::wstring& folder,UINT worldSeed,DXGI_FORMAT hdr,DXGI_FORMAT sunFormat) {
    if(folder.empty())return;
    Reader lib(folder+L"\\library.bin");lib.magic("CITYLIB1");
    const UINT version=lib.read<UINT>();if(version<1||version>3)throw std::runtime_error("Unsupported city library version.");
    const UINT count=lib.read<UINT>(),materials=lib.read<UINT>(),nv=lib.read<UINT>(),ni=lib.read<UINT>();
    if(!count||count>128||!materials||materials>128||!nv||nv>10000000||!ni||ni>30000000||ni%3)
        throw std::runtime_error("City library budget invalid.");
    for(UINT i=0;i<count;++i){
        char name[64];lib.bytes(name,64);if(!memchr(name,0,64))throw std::runtime_error("Invalid city model name.");
        Model m;m.name=name;m.lo=lib.read<XMFLOAT3>();m.hi=lib.read<XMFLOAT3>();
        const UINT levels=lib.read<UINT>();if(levels<1||levels>7)throw std::runtime_error("Invalid city LOD count.");
        for(UINT k=0;k<levels;++k){auto l=lib.read<Level>();if(l.first>ni||l.count>ni-l.first||l.count%3)throw std::runtime_error("City index range invalid.");m.levels.push_back(l);}
        mModels.push_back(std::move(m));
    }
    std::vector<XMFLOAT4> materialData(materials*3);
    for(UINT i=0;i<materials;++i){lib.bytes(materialData.data()+i*3,(version==1?2:3)*sizeof(XMFLOAT4));if(version==1)materialData[i*3+2]={0,1,0,0};}
    std::vector<Vertex> vertices(nv);std::vector<UINT> indices(ni);
    if(version>=3)lib.bytes(vertices.data(),vertices.size()*sizeof(Vertex));
    else for(auto& v:vertices){lib.bytes(&v,36);v.ambient=1;}
    lib.bytes(indices.data(),indices.size()*4);lib.end();
    for(auto& v:vertices){for(float f:v.p)if(!std::isfinite(f))throw std::runtime_error("Nonfinite city vertex.");if(v.material<0||v.material>=materials)throw std::runtime_error("Invalid city material.");}
    for(UINT i:indices)if(i>=nv)throw std::runtime_error("Invalid city index.");
    Reader scene(folder+L"\\scene.bin");scene.magic("CITYSCN1");
    const UINT sceneVersion=scene.read<UINT>();
    if(sceneVersion<1||sceneVersion>3||scene.read<UINT>()!=worldSeed)throw std::runtime_error("City scene does not match the planet seed.");
    mLatitude=scene.read<double>();mLongitude=scene.read<double>();
    if(!std::isfinite(mLatitude)||!std::isfinite(mLongitude)||std::abs(mLatitude)>89.9||std::abs(mLongitude)>180)throw std::runtime_error("Invalid city anchor.");
    const UINT np=scene.read<UINT>(),rv=scene.read<UINT>(),ri=scene.read<UINT>();
    if(np>4096||rv>2000000||ri>6000000||ri%3)throw std::runtime_error("City scene capacity exceeded.");
    mLandGrid=scene.read<XMFLOAT4>();
    if(sceneVersion>=3)scene.bytes(mLandBits.data(),sizeof(mLandBits));
    else {
        std::array<UINT,512> oldBits;scene.bytes(oldBits.data(),sizeof(oldBits));
        auto words=reinterpret_cast<UINT*>(mLandBits.data());
        for(UINT y=0;y<128;++y)for(UINT x=0;x<128;++x){UINT bit=y*128+x;if(!(oldBits[bit/32]&(1u<<(bit%32))))continue;
            for(UINT dy=0;dy<2;++dy)for(UINT dx=0;dx<2;++dx){UINT target=(y*2+dy)*256+x*2+dx;words[target/32]|=1u<<(target%32);}}
        mLandGrid.z*=.5f;
    }
    for(UINT i=0;i<np;++i){
        Placement p={};p.model=scene.read<UINT>();p.instance.originYaw=scene.read<XMFLOAT4>();
        p.instance.detail={scene.read<float>(),1,0,0};
        if(p.model>=count)throw std::runtime_error("City placement model invalid.");
        const auto& q=p.instance.originYaw;
        if(!std::isfinite(q.x+q.y+q.z+q.w+p.instance.detail.x)||std::abs(q.x)>2000||std::abs(q.y)>2000)
            throw std::runtime_error("City placement invalid.");
        mPlacements.push_back(p);
    }
    mRoadVertices.resize(rv);mRoadIndices.resize(ri);
    if(sceneVersion>=2)scene.bytes(mRoadVertices.data(),size_t(rv)*sizeof(Vertex));
    else for(auto& v:mRoadVertices){scene.bytes(&v,36);v.ambient=1;}
    scene.bytes(mRoadIndices.data(),size_t(ri)*4);scene.end();
    for(UINT i:mRoadIndices)if(i>=rv)throw std::runtime_error("City street index invalid.");
    if(rv&&ri){
        // Local ground chunks are culled separately; a street view no longer
        // submits every path and every foundation across the entire city.
        std::map<std::pair<int,int>,std::vector<UINT>> chunks;
        for(UINT t=0;t<ri;t+=3){float x=0,y=0;for(UINT k=0;k<3;++k){x+=mRoadVertices[mRoadIndices[t+k]].p[0]/3;y+=mRoadVertices[mRoadIndices[t+k]].p[1]/3;}
            auto& chunk=chunks[{int(floor(x/64)),int(floor(y/64))}];for(UINT k=0;k<3;++k)chunk.push_back(mRoadIndices[t+k]);}
        for(const auto& entry:chunks){const auto& cell=entry.first;const auto& chunk=entry.second;
            Model road;road.name="ground_"+std::to_string(cell.first)+"_"+std::to_string(cell.second);
            const float cx=(cell.first+.5f)*64,cy=(cell.second+.5f)*64;
            road.lo={1e9f,1e9f,1e9f};road.hi={-1e9f,-1e9f,-1e9f};road.levels.push_back({UINT(indices.size()),UINT(chunk.size())});
            std::map<UINT,UINT> remap;
            for(UINT source:chunk){auto result=remap.emplace(source,UINT(vertices.size()));const auto it=result.first;
                if(result.second){Vertex v=mRoadVertices[source];v.p[0]-=cx;v.p[1]-=cy;vertices.push_back(v);
                    road.lo.x=std::min(road.lo.x,v.p[0]);road.lo.y=std::min(road.lo.y,v.p[1]);road.lo.z=std::min(road.lo.z,v.p[2]);
                    road.hi.x=std::max(road.hi.x,v.p[0]);road.hi.y=std::max(road.hi.y,v.p[1]);road.hi.z=std::max(road.hi.z,v.p[2]);}
                indices.push_back(it->second);}
            mPlacements.push_back({UINT(mModels.size()),{{cx,cy,0,0},{1,1,0,0}}});mModels.push_back(road);
        }
    }
    mBoundsLo={mLandGrid.x,mLandGrid.y,0};mBoundsHi={mLandGrid.x+MaskSide*mLandGrid.z,mLandGrid.y+MaskSide*mLandGrid.z,20};
    for(const auto& p:mPlacements){if(Ground(mModels[p.model].name))continue;const auto& m=mModels[p.model];
        mBoundsLo.z=std::min(mBoundsLo.z,p.instance.originYaw.z+m.lo.z);mBoundsHi.z=std::max(mBoundsHi.z,p.instance.originYaw.z+m.hi.z);}
    mCapacity=UINT(mPlacements.size())*3+1;mBatches.reserve(mModels.size()*7);
    auto upload=[&](const void* data,size_t bytes,D3D12_RESOURCE_STATES state){
        auto buffer=CreateBuffer(device,bytes,D3D12_HEAP_TYPE_DEFAULT,D3D12_RESOURCE_STATE_COPY_DEST);
        auto stage=CreateBuffer(device,bytes,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
        void* ptr=nullptr;CD3DX12_RANGE none(0,0);Check(stage->Map(0,&none,&ptr),"City upload failed.");memcpy(ptr,data,bytes);stage->Unmap(0,nullptr);
        cmd->CopyBufferRegion(buffer.Get(),0,stage.Get(),0,bytes);auto barrier=CD3DX12_RESOURCE_BARRIER::Transition(buffer.Get(),D3D12_RESOURCE_STATE_COPY_DEST,state);
        cmd->ResourceBarrier(1,&barrier);mUploads.push_back(stage);mBytes+=bytes;return buffer;
    };
    mVertices=upload(vertices.data(),vertices.size()*sizeof(Vertex),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
    mIndices=upload(indices.data(),indices.size()*4,D3D12_RESOURCE_STATE_INDEX_BUFFER);
    mMaterials=upload(materialData.data(),materialData.size()*16,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
    mIndexView={mIndices->GetGPUVirtualAddress(),UINT(indices.size()*4),DXGI_FORMAT_R32_UINT};
    mInstances=CreateBuffer(device,size_t(mCapacity)*sizeof(Instance),D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
    mConstants=CreateBuffer(device,256,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
    CD3DX12_RANGE noRead(0,0);Check(mInstances->Map(0,&noRead,reinterpret_cast<void**>(&mInstanceData)),"City instance mapping failed.");
    Check(mConstants->Map(0,&noRead,reinterpret_cast<void**>(&mFrame)),"City constant mapping failed.");*mFrame={};
    const UINT stride=device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
    auto cpu=heap->GetCPUDescriptorHandleForHeapStart();cpu.ptr+=SIZE_T(base)*stride;
    mTable=heap->GetGPUDescriptorHandleForHeapStart();mTable.ptr+=UINT64(base)*stride;
    D3D12_DESCRIPTOR_HEAP_DESC dsv={D3D12_DESCRIPTOR_HEAP_TYPE_DSV,1,D3D12_DESCRIPTOR_HEAP_FLAG_NONE,0};
    Check(device->CreateDescriptorHeap(&dsv,IID_PPV_ARGS(&mDsv)),"City DSV failed.");
    CD3DX12_HEAP_PROPERTIES gpu(D3D12_HEAP_TYPE_DEFAULT);CD3DX12_CLEAR_VALUE clear(DXGI_FORMAT_D32_FLOAT,1,0);
    auto tex=CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R32_TYPELESS,ShadowSize,ShadowSize,1,1,1,0,D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL);
    Check(device->CreateCommittedResource(&gpu,D3D12_HEAP_FLAG_NONE,&tex,D3D12_RESOURCE_STATE_DEPTH_WRITE,&clear,IID_PPV_ARGS(&mShadow)),"City shadow allocation failed.");
    D3D12_DEPTH_STENCIL_VIEW_DESC depth={};depth.Format=DXGI_FORMAT_D32_FLOAT;depth.ViewDimension=D3D12_DSV_DIMENSION_TEXTURE2D;
    device->CreateDepthStencilView(mShadow.Get(),&depth,mDsv->GetCPUDescriptorHandleForHeapStart());
    // A city may load outside the camera's range. Its bound SRV must still
    // contain a cleared, readable map before the first visible shadow pass.
    cmd->ClearDepthStencilView(mDsv->GetCPUDescriptorHandleForHeapStart(),D3D12_CLEAR_FLAG_DEPTH,1,0,0,nullptr);
    auto shadowReady=CD3DX12_RESOURCE_BARRIER::Transition(mShadow.Get(),D3D12_RESOURCE_STATE_DEPTH_WRITE,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
    cmd->ResourceBarrier(1,&shadowReady);mShadowReadable=true;
    D3D12_SHADER_RESOURCE_VIEW_DESC srv={};srv.Format=DXGI_FORMAT_R32_FLOAT;srv.ViewDimension=D3D12_SRV_DIMENSION_TEXTURE2D;
    srv.Shader4ComponentMapping=D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;srv.Texture2D.MipLevels=1;device->CreateShaderResourceView(mShadow.Get(),&srv,cpu);
    for(UINT channel=0;channel<3;++channel){
        UINT size=1,layers=1,mips=1;std::vector<unsigned char> pixels={255,255,255,255};
        if(channel==1)pixels={128,128,255,255};
        if(version>=2){
            Reader texture(folder+L"\\texture"+std::to_wstring(channel)+L".bin");texture.magic("CITYTEX1");
            size=texture.read<UINT>();layers=texture.read<UINT>();mips=texture.read<UINT>();
            if(texture.read<UINT>()!=channel||size<1||size>1024||(size&(size-1))||!layers||layers>32||mips<1||mips>11||mips!=UINT(log2(size))+1)
                throw std::runtime_error("City texture budget or format invalid.");
            size_t bytes=0;for(UINT mip=0;mip<mips;++mip)bytes+=size_t(std::max(size>>mip,1u))*std::max(size>>mip,1u)*4*layers;
            pixels.resize(bytes);texture.bytes(pixels.data(),bytes);texture.end();
            for(UINT i=0;i<materials;++i)if(materialData[i*3+2].x<0||materialData[i*3+2].x>=layers)throw std::runtime_error("City texture layer invalid.");
        }
        auto desc=CD3DX12_RESOURCE_DESC::Tex2D(channel==0?DXGI_FORMAT_R8G8B8A8_UNORM_SRGB:DXGI_FORMAT_R8G8B8A8_UNORM,size,size,UINT16(layers),UINT16(mips));
        Check(device->CreateCommittedResource(&gpu,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&mTextures[channel])),"City material texture failed.");
        auto stage=CreateBuffer(device,GetRequiredIntermediateSize(mTextures[channel].Get(),0,layers*mips),D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
        std::vector<D3D12_SUBRESOURCE_DATA> subs;size_t offset=0;
        for(UINT layer=0;layer<layers;++layer)for(UINT mip=0;mip<mips;++mip){UINT n=std::max(size>>mip,1u);subs.push_back({pixels.data()+offset,LONG_PTR(n)*4,LONG_PTR(n)*n*4});offset+=size_t(n)*n*4;}
        UpdateSubresources(cmd,mTextures[channel].Get(),stage.Get(),0,0,UINT(subs.size()),subs.data());mUploads.push_back(stage);
        auto barrier=CD3DX12_RESOURCE_BARRIER::Transition(mTextures[channel].Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);cmd->ResourceBarrier(1,&barrier);
        auto handle=cpu;handle.ptr+=SIZE_T(1+channel)*stride;
        D3D12_SHADER_RESOURCE_VIEW_DESC image={};image.Format=desc.Format;image.ViewDimension=D3D12_SRV_DIMENSION_TEXTURE2DARRAY;
        image.Shader4ComponentMapping=D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;image.Texture2DArray.MipLevels=mips;image.Texture2DArray.ArraySize=layers;
        device->CreateShaderResourceView(mTextures[channel].Get(),&image,handle);
    }
    CD3DX12_DESCRIPTOR_RANGE luts(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,3,1),planet(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,29),shadow(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,33),images(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,3,34);
    CD3DX12_ROOT_PARAMETER params[9];params[0].InitAsConstantBufferView(0);params[1].InitAsConstantBufferView(2);
    params[2].InitAsShaderResourceView(30);params[3].InitAsShaderResourceView(31);params[4].InitAsShaderResourceView(32);
    params[5].InitAsDescriptorTable(1,&luts);params[6].InitAsDescriptorTable(1,&planet);params[7].InitAsDescriptorTable(1,&shadow);
    params[8].InitAsDescriptorTable(1,&images);
    CD3DX12_STATIC_SAMPLER_DESC samplers[]={CD3DX12_STATIC_SAMPLER_DESC(0,D3D12_FILTER_MIN_MAG_MIP_LINEAR,D3D12_TEXTURE_ADDRESS_MODE_CLAMP,D3D12_TEXTURE_ADDRESS_MODE_CLAMP,D3D12_TEXTURE_ADDRESS_MODE_CLAMP),
        CD3DX12_STATIC_SAMPLER_DESC(4,D3D12_FILTER_COMPARISON_MIN_MAG_LINEAR_MIP_POINT,D3D12_TEXTURE_ADDRESS_MODE_BORDER,D3D12_TEXTURE_ADDRESS_MODE_BORDER,D3D12_TEXTURE_ADDRESS_MODE_BORDER,0,1,D3D12_COMPARISON_FUNC_LESS_EQUAL,D3D12_STATIC_BORDER_COLOR_OPAQUE_WHITE),
        CD3DX12_STATIC_SAMPLER_DESC(5,D3D12_FILTER_ANISOTROPIC)};
    mRoot=CreateRootSignature(device,CD3DX12_ROOT_SIGNATURE_DESC(9,params,3,samplers));
    mImageTable=mTable;mImageTable.ptr+=stride;
    auto vs=LoadShader(L"CityVertex.cso"),ps=LoadShader(L"CityPixel.cso"),sv=LoadShader(L"CityShadow.cso");
    D3D12_GRAPHICS_PIPELINE_STATE_DESC pso={};pso.pRootSignature=mRoot.Get();pso.VS=CD3DX12_SHADER_BYTECODE(vs.Get());pso.PS=CD3DX12_SHADER_BYTECODE(ps.Get());
    pso.RasterizerState=CD3DX12_RASTERIZER_DESC(D3D12_DEFAULT);pso.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;
    pso.BlendState=CD3DX12_BLEND_DESC(D3D12_DEFAULT);pso.DepthStencilState=CD3DX12_DEPTH_STENCIL_DESC(D3D12_DEFAULT);
    pso.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_GREATER;pso.SampleMask=UINT_MAX;pso.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
    pso.NumRenderTargets=2;pso.RTVFormats[0]=hdr;pso.RTVFormats[1]=sunFormat;pso.DSVFormat=DXGI_FORMAT_D32_FLOAT;pso.SampleDesc.Count=1;
    Check(device->CreateGraphicsPipelineState(&pso,IID_PPV_ARGS(&mDrawPso)),"City drawing PSO failed.");
    pso.VS=CD3DX12_SHADER_BYTECODE(sv.Get());pso.PS={};pso.NumRenderTargets=0;pso.RTVFormats[0]=pso.RTVFormats[1]=DXGI_FORMAT_UNKNOWN;
    pso.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_LESS;pso.RasterizerState.DepthBias=100;pso.RasterizerState.SlopeScaledDepthBias=1.5f;
    Check(device->CreateGraphicsPipelineState(&pso,IID_PPV_ARGS(&mShadowPso)),"City shadow PSO failed.");
    // Bounded 4 m bins index the exact cooked street triangles for walking.
    mRoadCells.resize(MaskSide*MaskSide);
    for(UINT t=0;t<mRoadIndices.size();t+=3){
        float lx=1e9f,ly=1e9f,hx=-1e9f,hy=-1e9f;
        for(UINT k=0;k<3;++k){const auto& v=mRoadVertices[mRoadIndices[t+k]];lx=std::min(lx,v.p[0]);ly=std::min(ly,v.p[1]);hx=std::max(hx,v.p[0]);hy=std::max(hy,v.p[1]);}
        for(int y=std::max(0,int(floor((ly-mLandGrid.y)/mLandGrid.z)));y<=std::min(int(MaskSide)-1,int(floor((hy-mLandGrid.y)/mLandGrid.z)));++y)
            for(int x=std::max(0,int(floor((lx-mLandGrid.x)/mLandGrid.z)));x<=std::min(int(MaskSide)-1,int(floor((hx-mLandGrid.x)/mLandGrid.z)));++x)mRoadCells[y*MaskSide+x].push_back(t);
    }
    mReady=true;
}

void City::Update(FXMMATRIX model,FXMMATRIX viewProj,const XMFLOAT3& camera,const XMFLOAT3& sun,UINT screenHeight){
    if(!mReady)return;
    XMStoreFloat4x4(&mFrame->model,XMMatrixTranspose(model));mFrame->sun={sun.x,sun.y,sun.z,0};mFrame->camera={camera.x,camera.y,camera.z,0};
    const float sx=std::min(std::max(camera.x,mBoundsLo.x),mBoundsHi.x),sy=std::min(std::max(camera.y,mBoundsLo.y),mBoundsHi.y);
    XMVECTOR centre=XMVectorSet(sx,sy,(mBoundsLo.z+mBoundsHi.z)*.5f,1),s=XMLoadFloat3(&sun);
    XMVECTOR up=fabs(sun.z)<.95f?XMVectorSet(0,0,1,0):XMVectorSet(0,1,0,0);
    XMMATRIX shadowMatrix=XMMatrixLookToLH(centre+s*900,-s,up)*XMMatrixOrthographicLH(760,760,.1f,1800);
    XMFLOAT4X4 stable;XMStoreFloat4x4(&stable,shadowMatrix);
    stable._41+=(roundf(stable._41*ShadowSize*.5f)-stable._41*ShadowSize*.5f)*2/ShadowSize;
    stable._42+=(roundf(stable._42*ShadowSize*.5f)-stable._42*ShadowSize*.5f)*2/ShadowSize;
    XMStoreFloat4x4(&mFrame->shadow,XMMatrixTranspose(XMLoadFloat4x4(&stable)));
    mVisible=std::hypot(camera.x,camera.y)<18000&&std::abs(camera.z)<18000;
    mBatches.clear();mShadowBatches.clear();mVisibleCount=0;mTriangles=0;mShadowTriangles=0;
    if(!mVisible)return;
    // Offscreen casters inside the local light volume batch by shared mesh.
    UINT at=0;
    for(UINT i=0;i<mModels.size();++i){const auto& m=mModels[i];if(Ground(m.name))continue;
        Batch batch={i,UINT(std::min<size_t>(2,m.levels.size()-1)),at,0};
        for(const auto& p:mPlacements){if(p.model!=i)continue;const auto& q=p.instance.originYaw;
            const float extent=Size(m.lo,m.hi);if(std::hypot(q.x-sx,q.y-sy)>550+extent*.5f)continue;
            if(extent<5&&std::hypot(q.x-camera.x,q.y-camera.y)>230)continue;
            mInstanceData[at++]=p.instance;++batch.count;}
        if(batch.count){mShadowBatches.push_back(batch);mShadowTriangles+=UINT64(batch.count)*m.levels[batch.level].count/3;}
    }
    const UINT shadowCount=at;
    const XMMATRIX cityClip=model*viewProj;
    for(UINT modelIndex=0;modelIndex<mModels.size();++modelIndex){const auto& m=mModels[modelIndex];
        const float extent=Size(m.lo,m.hi),radius=.5f*sqrtf(powf(m.hi.x-m.lo.x,2)+powf(m.hi.y-m.lo.y,2)+powf(m.hi.z-m.lo.z,2));
        for(UINT level=0;level<m.levels.size();++level){Batch batch={modelIndex,level,at,0};
            for(const auto& p:mPlacements){if(p.model!=modelIndex)continue;const auto& q=p.instance.originYaw;
                const float distance=std::max(1.0f,sqrtf(powf(q.x-camera.x,2)+powf(q.y-camera.y,2)+powf(q.z+(m.hi.z+m.lo.z)*.5f-camera.z,2))-radius*.3f);
                XMFLOAT4 clip;XMStoreFloat4(&clip,XMVector4Transform(XMVectorSet(q.x,q.y,q.z+(m.hi.z+m.lo.z)*.5f,1),cityClip));
                if(clip.w+radius<=0||std::abs(clip.x)>clip.w+radius*2||std::abs(clip.y)>clip.w+radius*2)continue;
                const float pixels=extent*screenHeight/distance;
                if(pixels<.7f||(extent<5&&distance>650))continue;
                const float thresholds[4]={520,260,115,42};UINT desired=0;
                while(desired+1<m.levels.size()&&desired<4&&pixels<thresholds[desired])++desired;
                // A complementary screen-space dither relays adjacent levels.
                float fine=1;UINT coarse=desired;
                if(desired+1<m.levels.size()&&desired<4&&pixels<thresholds[desired]*1.2f){coarse=desired+1;fine=std::min(std::max((pixels/thresholds[desired]-1)/.2f,0.0f),1.0f);}
                if(level!=desired&&level!=coarse)continue;
                Instance instance=p.instance;
                instance.detail.y=(level==coarse&&coarse!=desired)?-fine:fine;
                instance.detail.z=(level==coarse&&coarse!=desired)?1.0f:0.0f;
                if(at>=mCapacity)throw std::runtime_error("City visible capacity exceeded.");
                mInstanceData[at++]=instance;++batch.count;mTriangles+=m.levels[level].count/3;
            }
            if(batch.count)mBatches.push_back(batch);
        }
    }
    mVisibleCount=at-shadowCount;
}

void City::Bind(ID3D12GraphicsCommandList* cmd,D3D12_GPU_VIRTUAL_ADDRESS frame){
    cmd->SetGraphicsRootSignature(mRoot.Get());cmd->SetGraphicsRootConstantBufferView(0,frame);
    cmd->SetGraphicsRootConstantBufferView(1,mConstants->GetGPUVirtualAddress());cmd->SetGraphicsRootShaderResourceView(2,mVertices->GetGPUVirtualAddress());
    cmd->SetGraphicsRootShaderResourceView(3,mInstances->GetGPUVirtualAddress());cmd->SetGraphicsRootShaderResourceView(4,mMaterials->GetGPUVirtualAddress());
    cmd->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);cmd->IASetIndexBuffer(&mIndexView);
}

void City::DrawShadows(ID3D12GraphicsCommandList* cmd,D3D12_GPU_VIRTUAL_ADDRESS frame){
    if(!mReady||!mVisible)return;
    if(mShadowReadable){auto b=CD3DX12_RESOURCE_BARRIER::Transition(mShadow.Get(),D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_DEPTH_WRITE);cmd->ResourceBarrier(1,&b);}
    auto depth=mDsv->GetCPUDescriptorHandleForHeapStart();cmd->OMSetRenderTargets(0,nullptr,FALSE,&depth);cmd->ClearDepthStencilView(depth,D3D12_CLEAR_FLAG_DEPTH,1,0,0,nullptr);
    CD3DX12_VIEWPORT viewport(0.0f,0.0f,float(ShadowSize),float(ShadowSize));CD3DX12_RECT rect(0,0,ShadowSize,ShadowSize);
    cmd->RSSetViewports(1,&viewport);cmd->RSSetScissorRects(1,&rect);Bind(cmd,frame);cmd->SetPipelineState(mShadowPso.Get());
    for(const auto& batch:mShadowBatches){const auto& lod=mModels[batch.model].levels[batch.level];
        cmd->SetGraphicsRootShaderResourceView(3,mInstances->GetGPUVirtualAddress()+UINT64(batch.first)*sizeof(Instance));
        cmd->DrawIndexedInstanced(lod.count,batch.count,lod.first,0,0);}
    auto b=CD3DX12_RESOURCE_BARRIER::Transition(mShadow.Get(),D3D12_RESOURCE_STATE_DEPTH_WRITE,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);cmd->ResourceBarrier(1,&b);mShadowReadable=true;
}

void City::Draw(ID3D12GraphicsCommandList* cmd,D3D12_GPU_VIRTUAL_ADDRESS frame,D3D12_GPU_DESCRIPTOR_HANDLE luts,D3D12_GPU_DESCRIPTOR_HANDLE planet){
    if(!mReady||!mVisible)return;Bind(cmd,frame);cmd->SetPipelineState(mDrawPso.Get());
    cmd->SetGraphicsRootDescriptorTable(5,luts);cmd->SetGraphicsRootDescriptorTable(6,planet);cmd->SetGraphicsRootDescriptorTable(7,mTable);
    cmd->SetGraphicsRootDescriptorTable(8,mImageTable);
    // SV_InstanceID starts at zero in Direct3D even with StartInstanceLocation.
    // Vertex pulling therefore offsets the SRV, not the input-assembler stream.
    for(const auto& b:mBatches){const auto& l=mModels[b.model].levels[b.level];
        cmd->SetGraphicsRootShaderResourceView(3,mInstances->GetGPUVirtualAddress()+UINT64(b.first)*sizeof(Instance));
        cmd->DrawIndexedInstanced(l.count,b.count,l.first,0,0);}
}

bool City::Surface(double x,double y,double current,double& height) const {
    if(!mReady||mLandGrid.z<=0)return false;
    const int ix=int(floor((x-mLandGrid.x)/mLandGrid.z)),iy=int(floor((y-mLandGrid.y)/mLandGrid.z));
    if(ix<0||iy<0||ix>=int(MaskSide)||iy>=int(MaskSide))return false;bool found=false;height=current;
    for(UINT t:mRoadCells[iy*MaskSide+ix]){
        const auto& a=mRoadVertices[mRoadIndices[t]];const auto& b=mRoadVertices[mRoadIndices[t+1]];const auto& c=mRoadVertices[mRoadIndices[t+2]];
        const double d=(b.p[1]-c.p[1])*(a.p[0]-c.p[0])+(c.p[0]-b.p[0])*(a.p[1]-c.p[1]);if(fabs(d)<1e-10)continue;
        const double u=((b.p[1]-c.p[1])*(x-c.p[0])+(c.p[0]-b.p[0])*(y-c.p[1]))/d;
        const double v=((c.p[1]-a.p[1])*(x-c.p[0])+(a.p[0]-c.p[0])*(y-c.p[1]))/d;
        if(u>=-1e-5&&v>=-1e-5&&u+v<=1.00001){height=std::max(height,u*a.p[2]+v*b.p[2]+(1-u-v)*c.p[2]);found=true;}
    }
    return found;
}

bool City::ResolveMovement(double fromX,double fromY,double& x,double& y,double elevation) const {
    if(!mReady)return false;
    auto inside=[](double x,double y,const Placement& p,const Model& m){
        const auto& q=p.instance.originYaw;const double c=cos(q.w),s=sin(q.w),dx=x-q.x,dy=y-q.y;
        const double u=c*dx+s*dy,v=-s*dx+c*dy;
        return u>m.lo.x-.30&&u<m.hi.x+.30&&v>m.lo.y-.30&&v<m.hi.y+.30;
    };
    auto blocked=[&](double px,double py){for(const auto& p:mPlacements){const auto& m=mModels[p.model];
        if(Ground(m.name)||m.hi.z-m.lo.z<6||elevation>p.instance.originYaw.z+m.hi.z+.1||elevation+1.8<p.instance.originYaw.z+m.lo.z)continue;
        // Exterior-only conservative hull. A teleport inside a hull can leave it.
        if(!inside(fromX,fromY,p,m)&&inside(px,py,p,m))return true;
    }return false;};
    const double dx=x-fromX,dy=y-fromY;const int steps=std::min(256,std::max(1,int(ceil(std::hypot(dx,dy)/.15))));
    double px=fromX,py=fromY;bool hit=false;
    for(int k=0;k<steps;++k){const double nx=px+dx/steps,ny=py+dy/steps;
        if(!blocked(nx,ny)){px=nx;py=ny;continue;}
        hit=true;if(!blocked(nx,py))px=nx;if(!blocked(px,ny))py=ny;
    }
    x=px;y=py;return hit;
}

void City::SaveStats(const std::wstring& path) const {
    if(!mReady)return;std::ofstream file(path+L".city.json");
    file<<"{\"functional_only\":true,\"placements\":"<<mPlacements.size()<<",\"visible_representations\":"<<mVisibleCount
        <<",\"draw_calls\":"<<mBatches.size()<<",\"triangles_one_pass\":"<<mTriangles<<",\"geometry_bytes\":"<<mBytes
        <<",\"shadow_draw_calls\":"<<mShadowBatches.size()<<",\"shadow_triangles\":"<<mShadowTriangles<<"}\n";
}
