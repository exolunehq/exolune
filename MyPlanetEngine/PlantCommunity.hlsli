#ifndef PLANT_COMMUNITY_HLSLI
#define PLANT_COMMUNITY_HLSLI
// Architectural communities, not a botanical simulation. Climate admits the pool; slow spatial fields give it a
// dominant form and a few companions. Nothing depends on camera distance, weather time or GPU execution order.
float CommunityRandom(uint seed,uint salt) {
    uint h=seed^salt; h^=h>>16; h*=0x7feb352du; h^=h>>15; h*=0x846ca68bu; h^=h>>16;
    return ((h&0xffffffu)+0.5)/16777216.0;
}
uint CommunityChoice(float field,uint seed,uint count) {
    float phase=frac(0.5+field*0.65)*count;
    uint first=min((uint)phase,count-1u), second=(first+1u)%count;
    float choose=CommunityRandom(seed,0x695ec4d1u);
    // 88% follows the two local dominants; 12% supplies compatible minority forms.
    if (choose<0.12) return min((uint)(choose/0.12*count),count-1u);
    return (choose-0.12)/0.88<smoothstep(0.15,0.85,frac(phase)) ? second : first;
}
float HerbCeiling() { return GameVegetation()?0.32:0.18; }
float HerbCover(Vegetation v) {
    if (!DiverseVegetation()) return 0.0;
    return HerbCeiling()*v.herbs*v.able*(1.0-(GameVegetation()?0.55:0.7)*TreesHere(v))*(0.35+0.65*v.shrub);
}
float HerbFootprint(Vegetation v,int octave) {
    return -log(max(1.0-HerbCover(v),1e-4))*OctaveShare(octave,0.65);
}
uint CommunityModel(Vegetation v,uint species,uint family,uint seed,float2 fields,bool herb) {
    if (GeneratedVegetationBank() && !herb) {
        uint bank=family;
        if (species==CONIFER) bank=(family==3u || v.exposure>.35)?3u:0u;
        else if (species==BROADLEAF && (bank==0u || bank==3u)) bank=4u;
        return 31u+bank*10u+(species==SHRUB?5u:0u)+CommunityChoice(species==SHRUB?fields.y:fields.x,seed,5u);
    }
    if (species==CONIFER) {
        const uint models[3]={0,14,15};
        return models[CommunityChoice(fields.x,seed,3)];
    }
    if (species==BROADLEAF) {
        const uint models[5]={1,16,17,18,19};
        return models[CommunityChoice(fields.x,seed,5)];
    }
    if (herb) {
        float sun=1.0-smoothstep(0.15,0.55,TreesHere(v));
        float flowers=sun*smoothstep(0.02,0.22,fields.y)*smoothstep(7.0,12.0,v.season)
            *(1.0-smoothstep(1.5,2.5,v.aridity));
        if (CommunityRandom(seed,0xd49726a1u)<0.12*flowers)
            return 27u+CommunityChoice(fields.x,seed,2);
        if (sun<0.6 && v.season>10.0 && v.aridity>0.7)
            return GameVegetation() && CommunityRandom(seed,0x372ca184u)<0.72
                ? 29u+CommunityChoice(fields.y,seed,2) : 23u+CommunityChoice(fields.y,seed,2);
        return 25u+CommunityChoice(fields.y,seed,2);
    }
    // Upright leafy companions stay on temperate/tropical edges; arid scrub keeps its sparse grey-green forms.
    if (family>=4u && v.season>8.0 && CommunityRandom(seed,0x64dce837u)<0.30)
        return 20u+CommunityChoice(fields.y,seed,2);
    if (family!=3u && v.aridity>0.30 && v.season>14.0 && CommunityRandom(seed,0x1e739c45u)<0.22) return 22;
    return 2u+2u*family+CommunityChoice(fields.y,seed,2);
}
#endif
