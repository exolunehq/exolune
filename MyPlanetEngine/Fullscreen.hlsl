// One triangle that covers the screen, without any vertex buffer: for the full-screen passes.
float4 VSMain(uint id : SV_VertexID) : SV_POSITION
{
    const float2 uv = float2((id << 1) & 2, id & 2);
    return float4(uv * float2(2.0, -2.0) + float2(-1.0, 1.0), 0.0, 1.0);
}
