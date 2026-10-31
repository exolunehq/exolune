RWByteAddressBuffer arguments : register(u1);
cbuffer ClassifySettings : register(b1) { uint queueBaseLow, queueBaseHigh; };
static const uint STRIDE=28, QUEUE_CAPACITY=524288, MODEL_COUNTS=784, AGGREGATE_COUNTS=1008, OVERFLOW=1032;
[numthreads(1,1,1)]
void CSMain(uint id : SV_DispatchThreadID) {
    // SV_InstanceID démarre à zéro : l'adresse SRV racine porte aussi le préfixe.
    [unroll] for (uint queue=0;queue<6;++queue) {
        uint rep=queue&1, firstModel=queue<4 ? queue/2 : 2, endModel=queue<4 ? firstModel+1 : 14;
        uint total=0;
        [loop] for (uint model=firstModel;model<endModel;++model) {
            uint command=model*2+rep, n=arguments.Load(MODEL_COUNTS+4*command);
            uint start=min(total,QUEUE_CAPACITY), accepted=min(n,QUEUE_CAPACITY-start);
            uint offset=(queue*QUEUE_CAPACITY+min(start,QUEUE_CAPACITY-1))*64;
            uint addressLow=queueBaseLow+offset;
            arguments.Store(command*STRIDE,addressLow);
            arguments.Store(command*STRIDE+4,queueBaseHigh+(addressLow<queueBaseLow ? 1u : 0u));
            arguments.Store(command*STRIDE+12,accepted);
            arguments.Store(command*STRIDE+24,start);
            total+=n;
        }
        arguments.Store(AGGREGATE_COUNTS+queue*4,min(total,QUEUE_CAPACITY));
        arguments.Store(OVERFLOW+queue*4,total>QUEUE_CAPACITY ? total-QUEUE_CAPACITY : 0);
    }
}
