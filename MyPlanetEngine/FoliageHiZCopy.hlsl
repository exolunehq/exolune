Texture2D<float> sourceDepth : register(t0);
RWTexture2D<float> outputDepth : register(u0);
cbuffer Dimensions : register(b0) { uint sourceWidth, sourceHeight, targetWidth, targetHeight; };
[numthreads(8, 8, 1)]
void main(uint3 id : SV_DispatchThreadID) {
    if (id.x >= targetWidth || id.y >= targetHeight) return;
    // Reversed-Z sky is zero: padded pixels must never hide an object.
    outputDepth[id.xy] = id.x < sourceWidth && id.y < sourceHeight
        ? sourceDepth.Load(int3(id.xy, 0)) : 0.0f;
}
