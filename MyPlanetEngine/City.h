// Generated architecture. A bounded, instanced review district uses the same
// planetary frame, atmosphere, depth and solar-share buffers as the landscape.
#pragma once
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <d3d12.h>
#include <DirectXMath.h>
#include <wrl.h>
#include <string>
#include <vector>
#include <array>

class City {
public:
    static constexpr UINT DescriptorCount=7, ShadowSize=4096, MaskSide=256;
    static constexpr float PlanetRadiusM=6378000.0f; // D3DApp::PlanetRadius
    bool Ready() const { return mReady; }
    double Latitude() const { return mLatitude; }
    double Longitude() const { return mLongitude; }
    const DirectX::XMFLOAT4& LandGrid() const { return mLandGrid; }
    const std::array<DirectX::XMUINT4,512>& LandBits() const { return mLandBits; }
    // Earthworks (grading.bin): pads graded into the relief. The shaders apply them in CityGrade.hlsli;
    // Grade applies the same function to a natural height, for walking.
    const std::vector<DirectX::XMFLOAT4>& Pads() const { return mPads; }
    const std::array<UINT,1024>& GradeCells() const { return mGradeCells; }
    const std::vector<UINT16>& GradeIndex() const { return mGradeIndex; }
    const DirectX::XMFLOAT4& GradeGrid() const { return mGradeGrid; }
    // The guideway's tree-free corridor (corridor.bin, CITYCOR1): info (count, half width, boxes), boxes, segments.
    const DirectX::XMFLOAT4& CorridorInfo() const { return mCorridorInfo; }
    const std::vector<DirectX::XMFLOAT4>& CorridorBoxes() const { return mCorridorBoxes; }
    const std::vector<DirectX::XMFLOAT4>& Corridor() const { return mCorridor; }
    float Knee() const { return mKnee; }
    float Round() const { return mRound; }
    double Grade(double x,double y,double height) const;
    DirectX::XMMATRIX Shadow() const;
    void Initialize(ID3D12Device*,ID3D12GraphicsCommandList*,ID3D12DescriptorHeap*,UINT,const std::wstring&,UINT worldSeed,DXGI_FORMAT,DXGI_FORMAT);
    void ReleaseUploads() { mUploads.clear(); }
    void Update(DirectX::FXMMATRIX model,DirectX::FXMMATRIX viewProj,const DirectX::XMFLOAT3& camera,
                const DirectX::XMFLOAT3& sun,UINT screenHeight);
    void DrawShadows(ID3D12GraphicsCommandList*,D3D12_GPU_VIRTUAL_ADDRESS);
    void Draw(ID3D12GraphicsCommandList*,D3D12_GPU_VIRTUAL_ADDRESS,D3D12_GPU_DESCRIPTOR_HANDLE,D3D12_GPU_DESCRIPTOR_HANDLE);
    D3D12_GPU_DESCRIPTOR_HANDLE ShadowSrv() const { return mTable; }
    // The exact cooked street mesh supplies walking contact. Solid buildings
    // remain exterior obstacles until a separately validated interior exists.
    bool Surface(double x,double y,double current,double& height) const;
    bool ResolveMovement(double fromX,double fromY,double& x,double& y,double elevation) const;
    void SaveStats(const std::wstring&) const;
private:
    using Resource=Microsoft::WRL::ComPtr<ID3D12Resource>;
    struct Vertex { float p[3],n[3],uv[2],material,ambient; };
    struct Instance { DirectX::XMFLOAT4 originYaw,detail; };
    struct Level { UINT first,count; };
    struct Model { std::string name; DirectX::XMFLOAT3 lo,hi;std::vector<Level> levels; };
    struct Placement { UINT model;Instance instance; };
    struct Batch { UINT model,level,first,count; };
    struct Frame { DirectX::XMFLOAT4X4 model,shadow;DirectX::XMFLOAT4 sun,camera; };
    std::vector<Model> mModels;
    std::vector<Placement> mPlacements;
    std::vector<Batch> mBatches;
    std::vector<Batch> mShadowBatches;
    std::vector<Vertex> mRoadVertices;
    std::vector<UINT> mRoadIndices;
    UINT mWalkIndices=0; // the walkable prefix of mRoadIndices
    std::vector<DirectX::XMFLOAT4> mPads; // two per pad: centre xy, yaw, bank slope; half extents, radius, height
    std::array<UINT,1024> mGradeCells={};
    std::vector<UINT16> mGradeIndex;
    DirectX::XMFLOAT4 mGradeGrid={};
    DirectX::XMFLOAT4 mCorridorInfo={};
    std::vector<DirectX::XMFLOAT4> mCorridorBoxes,mCorridor;
    std::vector<std::vector<UINT>> mByModel; // placement indices per model
    float mKnee=0,mRound=0;
    std::vector<std::vector<UINT>> mRoadCells;
    std::array<DirectX::XMUINT4,512> mLandBits={};
    DirectX::XMFLOAT4 mLandGrid={};
    DirectX::XMFLOAT3 mBoundsLo={},mBoundsHi={};
    double mLatitude=0,mLongitude=0;
    bool mReady=false,mVisible=false,mShadowReadable=false;
    UINT mCapacity=0,mVisibleCount=0;UINT64 mTriangles=0,mShadowTriangles=0,mBytes=0;
    Resource mVertices,mIndices,mMaterials,mInstances,mShadow,mConstants,mTextures[3],mAtlases[3];
    std::vector<Resource> mUploads;
    Instance* mInstanceData=nullptr;Frame* mFrame=nullptr;
    D3D12_INDEX_BUFFER_VIEW mIndexView={};
    D3D12_GPU_DESCRIPTOR_HANDLE mTable={},mImageTable={};
    Microsoft::WRL::ComPtr<ID3D12DescriptorHeap> mDsv;
    Microsoft::WRL::ComPtr<ID3D12RootSignature> mRoot;
    Microsoft::WRL::ComPtr<ID3D12PipelineState> mDrawPso,mShadowPso;
    void Bind(ID3D12GraphicsCommandList*,D3D12_GPU_VIRTUAL_ADDRESS);
};
