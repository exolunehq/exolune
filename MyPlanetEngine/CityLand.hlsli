#ifndef CITY_LAND_HLSLI
#define CITY_LAND_HLSLI
bool CityOccupied(float3 facePoint){
    if(cityLandGrid.w<.5)return false;
    float2 xy=mul(float4(facePoint,1),cityFromFace).xy;
    int2 cell=(int2)floor((xy-cityLandGrid.xy)/cityLandGrid.z);
    if(any(cell<0)||any(cell>=256))return false;
    uint bit=(uint)(cell.y*256+cell.x),word=bit/32;
    return (cityLandBits[word/4][word%4]&(1u<<(bit%32)))!=0;
}
#endif
