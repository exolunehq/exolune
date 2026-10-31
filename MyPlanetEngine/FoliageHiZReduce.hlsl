Texture2D<float> sourceDepth : register(t0);
RWTexture2D<float> outputDepth : register(u0);
cbuffer Dimensions : register(b0) { uint sourceWidth, sourceHeight, targetWidth, targetHeight; };
[numthreads(8, 8, 1)]
void main(uint3 id : SV_DispatchThreadID) {
    if (id.x >= targetWidth || id.y >= targetHeight) return;
    uint2 p = id.xy * 2;
    uint2 q = min(p + 1, uint2(sourceWidth - 1, sourceHeight - 1));
    float a = sourceDepth.Load(int3(p, 0));
    float b = sourceDepth.Load(int3(q.x, p.y, 0));
    float c = sourceDepth.Load(int3(p.x, q.y, 0));
    float d = sourceDepth.Load(int3(q, 0));
    outputDepth[id.xy] = min(min(a, b), min(c, d));
}
