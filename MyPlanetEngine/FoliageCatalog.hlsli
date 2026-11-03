// Shared CPU/GPU command layout. Extra models partition the same six bounded queues.
#ifndef FOLIAGE_CATALOG_HLSLI
#define FOLIAGE_CATALOG_HLSLI
#define FOLIAGE_MAX_MODELS 96
#if FOLIAGE_MAX_MODELS > 127
#error Update the exact float32 coverage packing before extending the active catalogue.
#endif
#define FOLIAGE_MESH_LODS 7
#define FOLIAGE_REPRESENTATIONS (FOLIAGE_MESH_LODS + 1)
#define FOLIAGE_COMMANDS (FOLIAGE_MAX_MODELS * FOLIAGE_REPRESENTATIONS)
#define FOLIAGE_MODEL_COUNTS (FOLIAGE_COMMANDS * 28)
#define FOLIAGE_MODEL_CURSORS (FOLIAGE_MODEL_COUNTS + FOLIAGE_COMMANDS * 4)
#define FOLIAGE_UNIQUE_COUNTS (FOLIAGE_MODEL_CURSORS + FOLIAGE_COMMANDS * 4)
#define FOLIAGE_AGGREGATE_COUNTS (FOLIAGE_UNIQUE_COUNTS + FOLIAGE_MAX_MODELS * 4)
#define FOLIAGE_OVERFLOW (FOLIAGE_AGGREGATE_COUNTS + 24)
#define FOLIAGE_COUNTER_BYTES (FOLIAGE_OVERFLOW + 24)
#ifdef __cplusplus
inline unsigned FoliageModelSpecies(unsigned model) {
#else
uint FoliageModelSpecies(uint model) {
#endif
    if (model>=31u) {
#ifdef __cplusplus
        const unsigned family=(model-31u)/10u;
#else
        const uint family=(model-31u)/10u;
#endif
        return ((model-31u)%10u)>=5u?2u:(family==0u || family==3u)?0u:1u;
    }
    return model==0 || model==14 || model==15 ? 0 : model==1 || (model>=16 && model<=19) ? 1 : 2;
}
#endif
