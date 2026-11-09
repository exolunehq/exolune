// Continuous sphere contact with a triangle. Positions are relative to the starting sphere centre.
// Shared with the CPU regression fixtures; no terrain model, mesh setting or geographic special case.
#ifndef FLIGHT_SWEEP_HLSLI
#define FLIGHT_SWEEP_HLSLI
#ifdef __cplusplus
#define FLIGHT_REF(Type) Type&
#else
#define FLIGHT_REF(Type) inout Type
#endif

struct FlightHit { float fraction; float3 normal; };

FlightHit FlightNoHit() {
    FlightHit h; h.fraction=2.0f; h.normal=float3(0,0,0); return h;
}

void FlightConsider(FLIGHT_REF(FlightHit) hit,float fraction,float3 normal,float3 movement) {
    const float n2=dot(normal,normal);
    if (fraction<0.0f || fraction>1.0f || fraction>=hit.fraction || n2<1e-20f) return;
    normal*=1.0f/sqrt(n2);
    // Touching while moving tangentially or away is not an obstacle.
    if (dot(movement,normal)>=-1e-7f) return;
    hit.fraction=fraction; hit.normal=normal;
}

// Earliest entry into the quadratic distance interval, with a stable root near a surface.
float FlightEntry(float a,float b,float c) {
    if (c<=0.0f) return 0.0f;
    if (a<=1e-20f || b>=0.0f) return 2.0f;
    const float discriminant=b*b-a*c;
    if (discriminant<0.0f) return 2.0f;
    return c/(-b+sqrt(max(discriminant,0.0f)));
}

void FlightVertex(FLIGHT_REF(FlightHit) hit,float3 vertex,float3 movement,float radius) {
    const float t=FlightEntry(dot(movement,movement),-dot(vertex,movement),dot(vertex,vertex)-radius*radius);
    FlightConsider(hit,t,movement*t-vertex,movement);
}

void FlightEdge(FLIGHT_REF(FlightHit) hit,float3 a,float3 b,float3 movement,float radius) {
    const float3 edge=b-a;
    const float e2=dot(edge,edge);
    if (e2<=1e-20f) return;
    const float u0=-dot(a,edge)/e2, du=dot(movement,edge)/e2;
    const float3 radial=-a-edge*u0, travel=movement-edge*du;
    const float t=FlightEntry(dot(travel,travel),dot(radial,travel),dot(radial,radial)-radius*radius);
    const float u=u0+t*du;
    if (u>=0.0f && u<=1.0f) FlightConsider(hit,t,radial+travel*t,movement);
}

bool FlightInside(float3 p,float3 a,float3 b,float3 c,float3 normal) {
    // The area test uses the same oriented normal on all three edges.
    return dot(cross(b-a,p-a),normal)>=-1e-6f
        && dot(cross(c-b,p-b),normal)>=-1e-6f
        && dot(cross(a-c,p-c),normal)>=-1e-6f;
}

FlightHit FlightTriangle(float3 a,float3 b,float3 c,float3 movement,float radius) {
    FlightHit hit=FlightNoHit();
    // A conservative box test rejects terrain wholly outside the swept sphere before the contact algebra.
    const float3 lo=min(min(a,b),c), hi=max(max(a,b),c);
    const float3 pathLo=min(float3(0,0,0),movement)-radius, pathHi=max(float3(0,0,0),movement)+radius;
    if (lo.x>pathHi.x || lo.y>pathHi.y || lo.z>pathHi.z || hi.x<pathLo.x || hi.y<pathLo.y || hi.z<pathLo.z)
        return hit;
    const float3 raw=cross(b-a,c-a);
    const float n2=dot(raw,raw);
    if (n2>1e-20f) {
        const float3 normal=raw/sqrt(n2);
        const float distance=-dot(normal,a), speed=dot(normal,movement);
        if (abs(distance)<=radius && FlightInside(-normal*distance,a,b,c,normal))
            FlightConsider(hit,0.0f,distance>=0.0f?normal:-normal,movement);
        if (abs(speed)>1e-12f) {
            const float t=(radius-distance)/speed;
            if (t>=0.0f && t<=1.0f && FlightInside(movement*t-normal*radius,a,b,c,normal))
                FlightConsider(hit,t,normal,movement);
            const float back=(-radius-distance)/speed;
            if (back>=0.0f && back<=1.0f && FlightInside(movement*back+normal*radius,a,b,c,normal))
                FlightConsider(hit,back,-normal,movement);
        }
    }
    FlightEdge(hit,a,b,movement,radius); FlightEdge(hit,b,c,movement,radius); FlightEdge(hit,c,a,movement,radius);
    FlightVertex(hit,a,movement,radius); FlightVertex(hit,b,movement,radius); FlightVertex(hit,c,movement,radius);
    return hit;
}

#undef FLIGHT_REF
#endif
