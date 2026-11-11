#ifndef CITY_LAND_HLSLI
#define CITY_LAND_HLSLI
// The guideway's corridor: segments in groups of 8, each group behind its box; a tree within the half width of a
// segment gives way, so no crown crosses the line far from the city. Ground flora and stones stay.
bool CityCorridor(float3 facePoint){
    if(cityLandGrid.w<.5||cityCorridorInfo.x<.5)return false;
    const float2 xy=mul(float4(facePoint,1),cityFromFace).xy;
    const uint boxes=(uint)cityCorridorInfo.z,count=(uint)cityCorridorInfo.x;
    for(uint b=0;b<boxes;++b){
        const float4 box=cityCorridorBoxes[b];
        if(any(xy<box.xy)||any(xy>box.zw))continue;
        for(uint k=b*8;k<min(b*8+8,count);++k){
            const float4 s=cityCorridor[k];const float2 d=s.zw-s.xy;
            const float t=saturate(dot(xy-s.xy,d)/max(dot(d,d),1e-6));
            if(length(xy-s.xy-d*t)<cityCorridorInfo.y)return true;
        }
    }
    return false;
}
bool CityOccupied(float3 facePoint){
    if(cityLandGrid.w<.5)return false;
    float2 xy=mul(float4(facePoint,1),cityFromFace).xy;
    int2 cell=(int2)floor((xy-cityLandGrid.xy)/cityLandGrid.z);
    if(any(cell<0)||any(cell>=256))return false;
    uint bit=(uint)(cell.y*256+cell.x),word=bit/32;
    return (cityLandBits[word/4][word%4]&(1u<<(bit%32)))!=0;
}
#endif
