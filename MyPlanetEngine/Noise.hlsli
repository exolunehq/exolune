// Noise.hlsli - the relief's noise bricks (Relief.hlsli; docs/geometrie.md): a gradient noise on the integer lattice, with
// its derivatives too, and its fractal sums, fBm, billow, ridged multifractal, a Voronoi distance, a vector turbulence.
// Exolune's own code.
//
// Precision: the point and the frequencies are doubles; only the lattice split runs in double, the noise itself in float.
// Each octave's split gives an integer cell and a float remainder, three ways: exact, in doubles (gExactLattice); float,
// for cells of 4 m and more; in pairs of floats, about 48 bits, under LATTICE_PAIRS only (TerrainComputePairs.hlsl).
// Filtering: an octave the vertex cannot carry fades out and is replaced by its mean (gMaxFrequency); the creases of the
// billow and the ridged are rounded over about a cell, their mean kept (gCreaseMaxFrequency).
// The CPU port, the same hash and gradients: tools/hydro/cp.py. A change here goes there too.
#ifndef RELIEF_NOISE_HLSLI
#define RELIEF_NOISE_HLSLI

#include "PlanetSettings.hlsli"

// The thread's state, written by the callers before ReliefElevation.
static float gMaxFrequency = NO_LIMIT;       // the highest frequency the vertex can show, cycles per unit sphere radius
static float gCreaseMaxFrequency = NO_LIMIT; // the same, for the creases' rounding
static bool gExactLattice = true;            // the lattice split in doubles
#ifdef LATTICE_PAIRS
static bool gLatticePairs = false;           // the lattice split in pairs of floats
#endif

// The noise's deviation, per quality its scale to it, and the means of the filtered signals at that deviation, measured
// on the noise itself (tools/hydro/cp.py): the billow's 2 E|n| - 1, the ridged's E[(1 - |n|)^2], the Voronoi's.
static const float RL_SIGMA = 0.4;
static const float RL_SCALE_STANDARD = 2.1935;
static const float RL_SCALE_BEST = 2.0961;
static const float RL_MEAN_BILLOW_STANDARD = -0.3503;
static const float RL_MEAN_BILLOW_BEST = -0.3448;
static const float RL_MEAN_RIDGED_STANDARD = 0.5103;
static const float RL_MEAN_RIDGED_BEST = 0.5048;
static const float RL_MEAN_VORONOI = -0.0550;

// The gradients: 256 unit vectors on a Fibonacci spiral, z = 1 - (2i + 1) / 256 at the angle i pi (3 - sqrt 5), in float.
static const float3 RL_GRADIENTS[256] = {
    float3(0.0883019865, 0, 0.99609375), float3(-0.112554885, 0.103109494, 0.98828125), float3(0.017194448, -0.195921868, 0.98046875), float3(0.141309604, 0.184313357, 0.97265625),
    float3(-0.258806497, -0.0457792245, 0.96484375), float3(0.244676217, -0.155642986, 0.95703125), float3(-0.0816758871, 0.303830236, 0.94921875), float3(-0.155452311, -0.299313962, 0.94140625),
    float3(0.336590052, 0.122922145, 0.93359375), float3(-0.349457741, 0.144251078, 0.92578125), float3(0.168119669, -0.35926196, 0.91796875), float3(0.123982869, 0.395276934, 0.91015625),
    float3(-0.372920841, -0.216115251, 0.90234375), float3(0.436579347, -0.0959807485, 0.89453125), float3(-0.265887678, 0.378197849, 0.88671875), float3(-0.0612988994, -0.473039359, 0.87890625),
    float3(0.375531942, 0.316498727, 0.87109375), float3(-0.50429219, 0.0208540652, 0.86328125), float3(0.367070466, -0.365284145, 0.85546875), float3(-0.0245066788, 0.529979527, 0.84765625),
    float3(-0.34779501, -0.41677466, 0.83984375), float3(0.549774706, 0.0739714131, 0.83203125), float3(-0.4648287, 0.323415697, 0.82421875), float3(0.126745656, -0.563397169, 0.81640625),
    float3(0.292524993, 0.510495126, 0.80859375), float3(-0.570621908, -0.182043955, 0.80078125), float3(0.553082943, -0.255538344, 0.79296875), float3(-0.239086747, 0.571285546, 0.78515625),
    float3(-0.212912232, -0.591950238, 0.77734375), float3(0.565290093, 0.297100633, 0.76953125), float3(-0.626507401, 0.165145352, 0.76171875), float3(0.355320662, -0.552605271, 0.75390625),
    float3(0.112777583, 0.656220496, 0.74609375), float3(-0.533269763, -0.412994087, 0.73828125), float3(0.680614293, -0.0563875064, 0.73046875), float3(-0.469384789, 0.507391214, 0.72265625),
    float3(0.00341130211, -0.699275911, 0.71484375), float3(0.47514531, 0.523778319, 0.70703125), float3(-0.71185708, -0.0659747496, 0.69921875), float3(0.575487256, -0.436774313, 0.69140625),
    float3(-0.130633444, 0.718076944, 0.68359375), float3(-0.392584771, -0.623856485, 0.67578125), float3(0.717723846, 0.196698353, 0.66796875), float3(-0.668268561, 0.342944384, 0.66015625),
    float3(0.263466865, -0.710656643, 0.65234375), float3(0.28827852, 0.708148956, 0.64453125), float3(-0.696805537, -0.330229133, 0.63671875), float3(0.742970884, -0.229065865, 0.62890625),
    float3(-0.396274596, 0.676172316, 0.62109375), float3(-0.16583395, -0.772259831, 0.61328125), float3(0.648829937, 0.460898399, 0.60546875), float3(-0.795597613, 0.0991537943, 0.59765625),
    float3(0.523408115, -0.614921331, 0.58984375), float3(0.0296344049, 0.812626243, 0.58203125), float3(-0.574658096, -0.5831303, 0.57421875), float3(0.823051035, 0.0420831516, 0.56640625),
    float3(-0.639416456, 0.52831775, 0.55859375), float3(0.115331978, -0.826642931, 0.55078125), float3(0.476241231, 0.691649616, 0.54296875), float3(-0.823240936, -0.189425811, 0.53515625),
    float3(0.739249945, -0.418829471, 0.52734375), float3(-0.263665646, 0.812753141, 0.51953125), float3(-0.35653913, -0.781680107, 0.51171875), float3(0.795157731, 0.337346494, 0.50390625),
    float3(-0.818450689, 0.289878428, 0.49609375), float3(0.409764111, -0.770502925, 0.48828125), float3(0.21940206, 0.849124551, 0.48046875), float3(-0.738906622, -0.480221868, 0.47265625),
    float3(0.873321295, -0.145705864, 0.46484375), float3(-0.54803735, 0.700555146, 0.45703125), float3(-0.0694210902, -0.890720606, 0.44921875), float3(0.655701458, 0.612548888, 0.44140625),
    float3(-0.901065588, -0.00879160874, 0.43359375), float3(0.673122048, -0.604662776, 0.42578125), float3(-0.0882485285, 0.90416497, 0.41796875), float3(-0.547817647, -0.729155481, 0.41015625),
    float3(0.89989537, 0.168249384, 0.40234375), float3(-0.780086875, 0.48560226, 0.39453125), float3(0.248083994, -0.888202071, 0.38671875), float3(0.418506503, 0.825398326, 0.37890625),
    float3(-0.869100094, -0.327038974, 0.37109375), float3(0.864621162, -0.347069174, 0.36328125), float3(-0.404404581, 0.842673659, 0.35546875), float3(-0.271873236, -0.897340536, 0.34765625),
    float3(0.809075952, 0.47948128, 0.33984375), float3(-0.923199594, 0.193540126, 0.33203125), float3(0.551586509, -0.768527508, 0.32421875), float3(0.112724051, 0.941902518, 0.31640625),
    float3(-0.721314251, -0.62006104, 0.30859375), float3(0.953217864, -0.0301059503, 0.30078125), float3(-0.68427521, 0.667784989, 0.29296875), float3(0.053612899, -0.956980467, 0.28515625),
    float3(0.60834831, 0.74363482, 0.27734375), float3(-0.95309329, -0.137717381, 0.26953125), float3(0.797586918, -0.543468833, 0.26171875), float3(-0.221485212, 0.941528499, 0.25390625),
    float3(-0.473662853, -0.845624864, 0.24609375), float3(0.922327638, 0.304193616, 0.23828125), float3(-0.887293041, 0.399493754, 0.23046875), float3(0.385125995, -0.895601571, 0.22265625),
    float3(0.32156688, 0.922191381, 0.21484375), float3(-0.86152935, -0.463578761, 0.20703125), float3(0.949979007, -0.240523964, 0.19921875), float3(-0.538867533, 0.820356905, 0.19140625),
    float3(-0.157037199, -0.970377564, 0.18359375), float3(0.772394657, 0.61033386, 0.17578125), float3(-0.983173847, 0.0718031675, 0.16796875), float3(0.677351058, -0.718014956, 0.16015625),
    float3(-0.0144635485, 0.988221705, 0.15234375), float3(-0.657648623, -0.739330113, 0.14453125), float3(0.98544383, 0.101036958, 0.13671875), float3(-0.795725107, 0.591780961, 0.12890625),
    float3(0.187186256, -0.974832118, 0.12109375), float3(0.520947635, 0.846038342, 0.11328125), float3(-0.956448138, -0.272182554, 0.10546875), float3(0.889824867, -0.445729703, 0.09765625),
    float3(-0.355305523, 0.930422544, 0.08984375), float3(-0.366748124, -0.926696658, 0.08203125), float3(0.896953881, 0.435850054, 0.07421875), float3(-0.956326187, 0.284658492, 0.06640625),
    float3(0.513132572, -0.85630703, 0.05859375), float3(0.200144842, 0.978449464, 0.05078125), float3(-0.808810472, -0.586497486, 0.04296875), float3(0.992868423, -0.113913447, 0.03515625),
    float3(-0.655323029, 0.754853666, 0.02734375), float3(-0.0266864393, -0.999453008, 0.01953125), float3(0.694883406, 0.719026923, 0.01171875), float3(-0.998142064, -0.0608047806, 0.00390625),
    float3(0.777071893, -0.629399717, -0.00390625), float3(-0.147826225, 0.988943934, -0.01171875), float3(-0.558951318, -0.828970432, -0.01953125), float3(0.971936703, 0.233648002, -0.02734375),
    float3(-0.874289155, 0.48413071, -0.03515625), float3(0.317550927, -0.947267175, -0.04296875), float3(0.405568719, 0.91265285, -0.05078125), float3(-0.915149629, -0.398833156, -0.05859375),
    float3(0.943748057, -0.323928744, -0.06640625), float3(-0.476816416, 0.875863969, -0.07421875), float3(-0.239900649, -0.967325449, -0.08203125), float3(0.829752803, 0.550852418, -0.08984375),
    float3(-0.983202577, 0.154194549, -0.09765625), float3(0.620328486, -0.777218699, -0.10546875), float3(0.0675343052, 0.991265118, -0.11328125), float3(-0.718720138, -0.684673369, -0.12109375),
    float3(0.991468012, 0.0193491559, -0.12890625), float3(-0.743362248, 0.654767573, -0.13671875), float3(0.105724454, -0.983835876, -0.14453125), float3(0.585918486, 0.795921445, -0.15234375),
    float3(-0.968462706, -0.190866485, -0.16015625), float3(0.841932952, -0.512772262, -0.16796875), float3(-0.274062991, 0.945510685, -0.17578125), float3(-0.435964853, -0.88103801, -0.18359375),
    float3(0.915208995, 0.354621172, -0.19140625), float3(-0.912940323, 0.356162697, -0.19921875), float3(0.431873888, -0.877851367, -0.20703125), float3(0.274056613, 0.937408745, -0.21484375),
    float3(-0.833793402, -0.505185843, -0.22265625), float3(0.954279304, -0.19035551, -0.23046875), float3(-0.57395941, 0.783449173, -0.23828125), float3(-0.1057797, -0.963456571, -0.24609375),
    float3(0.727287412, 0.63763988, -0.25390625), float3(-0.964914501, 0.021054307, -0.26171875), float3(0.695720851, -0.665826857, -0.26953125), float3(-0.0630974397, 0.958696604, -0.27734375),
    float3(-0.599631727, -0.747748435, -0.28515625), float3(0.944915175, 0.145960912, -0.29296875), float3(-0.793325782, 0.529305995, -0.30078125), float3(0.226836696, -0.92375052, -0.30859375),
    float3(0.455488116, 0.832116365, -0.31640625), float3(-0.895448744, -0.305047095, -0.32421875), float3(0.863847136, -0.378844798, -0.33203125), float3(-0.379942298, 0.860319734, -0.33984375),
    float3(-0.300064772, -0.888310909, -0.34765625), float3(0.818733871, 0.450906634, -0.35546875), float3(-0.905368268, 0.219852328, -0.36328125), float3(0.517363966, -0.771118641, -0.37109375),
    float3(0.138920665, 0.914948702, -0.37890625), float3(-0.717954397, -0.578783333, -0.38671875), float3(0.917051136, -0.0579851978, -0.39453125), float3(-0.634683669, 0.659769773, -0.40234375),
    float3(0.022243198, -0.911743999, -0.41015625), float3(0.597136796, 0.684638441, -0.41796875), float3(-0.8991642, -0.101064913, -0.42578125), float3(0.728279412, -0.530665219, -0.43359375),
    float3(-0.177798212, 0.879515946, -0.44140625), float3(-0.460996717, -0.765300274, -0.44921875), float3(0.853068829, 0.251785666, -0.45703125), float3(-0.795459449, 0.388798863, -0.46484375),
    float3(0.322400421, -0.820154905, -0.47265625), float3(0.314758658, 0.818582177, -0.48046875), float3(-0.781165659, -0.389052242, -0.48828125), float3(0.834562361, -0.239575952, -0.49609375),
    float3(-0.451192915, 0.736548305, -0.50390625), float3(-0.163956776, -0.843363583, -0.51171875), float3(0.686801434, 0.508321822, -0.51953125), float3(-0.845019221, 0.0886064991, -0.52734375),
    float3(0.559990525, -0.632470071, -0.53515625), float3(0.0142231463, 0.839632452, -0.54296875), float3(-0.574140847, -0.605807185, -0.55078125), float3(0.827375174, 0.0585094057, -0.55859375),
    float3(-0.645440459, 0.512435913, -0.56640625), float3(0.128928021, -0.808486462, -0.57421875), float3(0.448007524, 0.678622782, -0.58203125), float3(-0.783270538, -0.196396679, -0.58984375),
    float3(0.705152988, -0.381531447, -0.59765625), float3(-0.260312736, 0.752093673, -0.60546875), float3(-0.313700736, -0.724898577, -0.61328125), float3(0.715381265, 0.320112765, -0.62109375),
    float3(-0.737797081, 0.245219022, -0.62890625), float3(0.375278085, -0.673613846, -0.63671875), float3(0.176794037, 0.743857086, -0.64453125), float3(-0.627322614, -0.425339818, -0.65234375),
    float3(0.743158281, -0.109130763, -0.66015625), float3(-0.46988371, 0.577084959, -0.66796875), float3(-0.0429249518, -0.735851288, -0.67578125), float3(0.523519158, 0.508554101, -0.68359375),
    float3(-0.722156763, -0.0211434066, -0.69140625), float3(0.541057706, -0.467279047, -0.69921875), float3(-0.0824163109, 0.702363431, -0.70703125), float3(-0.409048438, -0.567166448, -0.71484375),
    float3(0.676826417, 0.140263692, -0.72265625), float3(-0.586720049, 0.349535346, -0.73046875), float3(0.194088966, -0.645964622, -0.73828125), float3(0.289466262, 0.599627733, -0.74609375),
    float3(-0.610257268, -0.24333398, -0.75390625), float3(0.605869055, -0.229580596, -0.76171875), float3(-0.287483513, 0.570241094, -0.76953125), float3(-0.17062524, -0.605494618, -0.77734375),
    float3(0.526506245, 0.326068759, -0.78515625), float3(-0.598625422, 0.113349877, -0.79296875), float3(0.358669877, -0.479692936, -0.80078125), float3(0.058502961, 0.585451603, -0.80859375),
    float3(-0.430487514, -0.384917289, -0.81640625), float3(0.566230357, -0.00682896283, -0.82421875), float3(-0.404491097, 0.379619479, -0.83203125), float3(0.0409325175, -0.541282713, -0.83984375),
    float3(0.327858776, 0.417118073, -0.84765625), float3(-0.510988951, -0.0840447247, -0.85546875), float3(0.422564983, -0.276015103, -0.86328125), float3(-0.121767178, 0.475781918, -0.87109375),
    float3(-0.224939048, -0.420625985, -0.87890625), float3(0.436137885, 0.153341472, -0.88671875), float3(-0.411100566, 0.175528228, -0.89453125), float3(0.177963719, -0.392561674, -0.90234375),
    float3(0.128740698, 0.393753022, -0.91015625), float3(-0.345561862, -0.194731534, -0.91796875), float3(0.368235856, -0.0856237188, -0.92578125), float3(-0.202537894, 0.295602977, -0.93359375),
    float3(-0.0473739058, -0.333931118, -0.94140625), float3(0.242999077, 0.199837968, -0.94921875), float3(-0.289571613, 0.0154747618, -0.95703125), float3(0.184048221, -0.187624067, -0.96484375),
    float3(-0.00792933162, 0.232114077, -0.97265625), float3(-0.127823293, -0.14947319, -0.98046875), float3(0.151515201, 0.0185287558, -0.98828125), float3(-0.0718699694, 0.0513025261, -0.99609375)
};

// Read at scattered indices: cheaper in group memory than in a constant. Loaded by every thread group that evaluates the
// relief, before any return.
groupshared float3 rlGradients[256];

void LoadGradients(uint threadInGroup, uint groupSize)
{
    for (uint i = threadInGroup; i < 256; i += groupSize)
        rlGradients[i] = RL_GRADIENTS[i];
    GroupMemoryBarrierWithGroupSync();
}

// ---------------------------------------------------------------------------------------------
// The lattice
// ---------------------------------------------------------------------------------------------

struct RlPoint
{
    double3 p;
#ifdef LATTICE_PAIRS
    float3 hi, lo; // the point in a pair of floats: its float, and the rest
#endif
};

RlPoint RlMakePoint(double3 p)
{
    RlPoint r;
    r.p = p;
#ifdef LATTICE_PAIRS
    r.hi = (float3)p;
    r.lo = (float3)(p - (double3)r.hi);
#endif
    return r;
}

// An octave's lattice point: its integer cell and the remainder, in [0, 1) but for rounding.
struct RlCell
{
    int3 cell;
    float3 q;
};

#ifdef LATTICE_PAIRS
// p f in a pair of floats: the high parts' exact product by Dekker's method, Veltkamp's split by 2^12 + 1; the cross terms
// added to its error, then a fast two-sum. The cell is the high part's floor.
RlCell RlSplitPairs(RlPoint pt, double f)
{
    precise float fh = (float)f;
    precise float fl = (float)(f - (double)fh);
    precise float cf = 4097.0 * fh;
    precise float fhh = cf - (cf - fh);
    precise float fhl = fh - fhh;
    precise float3 cp = 4097.0 * pt.hi;
    precise float3 phh = cp - (cp - pt.hi);
    precise float3 phl = pt.hi - phh;
    precise float3 prod = pt.hi * fh;
    precise float3 err = (((phh * fhh - prod) + phh * fhl + phl * fhh) + phl * fhl) + (pt.hi * fl + pt.lo * fh);
    precise float3 s = prod + err;
    precise float3 e = err - (s - prod);
    precise float3 c = floor(s);
    RlCell l;
    l.cell = (int3)c;
    l.q = (s - c) + e;
    return l;
}
#endif

RlCell RlSplit(RlPoint pt, double f)
{
#ifdef LATTICE_PAIRS
    [branch] if (gLatticePairs && gExactLattice)
        return RlSplitPairs(pt, f);
#endif
    RlCell l;
    [branch] if (gExactLattice)
    {
        const double3 x = pt.p * f;
        const float3 c = floor((float3)x);
        l.cell = (int3)c;
        l.q = (float3)(x - (double3)c);
    }
    else
    {
        const float3 x = (float3)pt.p * (float)f;
        const float3 c = floor(x);
        l.cell = (int3)c;
        l.q = x - c;
    }
    return l;
}

// Each octave's lattice shifted by a fraction of a cell: no two octaves share their nodes (docs/principes.md).
float3 RlShift(int octave)
{
    return frac((float)octave * float3(0.7548776662, 0.5698402910, 0.4142135624));
}

// ---------------------------------------------------------------------------------------------
// The hash: xxHash32's rounds nested axis by axis, the cell's corners sharing them, then the seed and the avalanche.
// ---------------------------------------------------------------------------------------------

uint RlRound1(uint h, uint v)
{
    h += v * 0x85EBCA77u;
    h = (h << 13) | (h >> 19);
    return h * 0x9E3779B1u;
}

uint4 RlRound4(uint4 h, uint4 v)
{
    h += v * 0x85EBCA77u;
    h = (h << 13) | (h >> 19);
    return h * 0x9E3779B1u;
}

uint4 RlMix4(uint4 h)
{
    h ^= h >> 15;
    h *= 0x85EBCA77u;
    h ^= h >> 13;
    h *= 0xC2B2AE3Du;
    return h ^ (h >> 16);
}

uint RlMix1(uint h)
{
    h ^= h >> 15;
    h *= 0x85EBCA77u;
    h ^= h >> 13;
    h *= 0xC2B2AE3Du;
    return h ^ (h >> 16);
}

// The cell's eight corners, before the seed: h0 at z, h1 at z + 1; in each, x, x + 1, then y + 1.
void RlCornerHashes(int3 c, out uint4 h0, out uint4 h1)
{
    const uint x = asuint(c.x), y = asuint(c.y), z = asuint(c.z);
    const uint4 a = RlRound4(0x165667B1u.xxxx, uint4(x, x + 1u, x, x + 1u));
    const uint4 b = RlRound4(a, uint4(y, y, y + 1u, y + 1u));
    h0 = RlRound4(b, z.xxxx);
    h1 = RlRound4(b, (z + 1u).xxxx);
}

// A value in [-1, 1) per cell hash and seed.
float RlValue(uint h, uint seed)
{
    return (float)(RlMix1(h + seed * 0x27D4EB2Fu) >> 8) * (2.0 / 16777216.0) - 1.0;
}

// ---------------------------------------------------------------------------------------------
// The gradient noise
// ---------------------------------------------------------------------------------------------

// The blend weights: standard, 3t^2 - 2t^3, C1; best, 6t^5 - 15t^4 + 10t^3, C2.
float3 RlFade(float3 t, bool best)
{
    return best ? t * t * t * (t * (t * 6.0 - 15.0) + 10.0) : t * t * (3.0 - 2.0 * t);
}

// The eight corners' gradients against the point, blended; unscaled.
float RlCorners(uint4 h0, uint4 h1, uint seed, float3 q, float3 s)
{
    const uint k = seed * 0x27D4EB2Fu;
    const uint4 g0 = RlMix4(h0 + k) >> 24, g1 = RlMix4(h1 + k) >> 24;
    const float3 r = q - 1.0;
    const float4 n0 = float4(dot(rlGradients[g0.x], q), dot(rlGradients[g0.z], float3(q.x, r.y, q.z)),
                             dot(rlGradients[g1.x], float3(q.x, q.y, r.z)), dot(rlGradients[g1.z], float3(q.x, r.y, r.z)));
    const float4 n1 = float4(dot(rlGradients[g0.y], float3(r.x, q.y, q.z)), dot(rlGradients[g0.w], float3(r.x, r.y, q.z)),
                             dot(rlGradients[g1.y], float3(r.x, q.y, r.z)), dot(rlGradients[g1.w], r));
    const float4 x = n0 + s.x * (n1 - n0);
    const float2 y = x.xz + s.y * (x.yw - x.xz);
    return y.x + s.z * (y.y - y.x);
}

// One octave at the cell and its remainder, deviation RL_SIGMA. The remainder may leave [0, 1): its floor moves the cell.
float RlGradientNoise(int3 cell, float3 q, uint seed, bool best)
{
    const float3 fl = floor(q);
    cell += (int3)fl;
    q -= fl;
    uint4 h0, h1;
    RlCornerHashes(cell, h0, h1);
    return RlCorners(h0, h1, seed, q, RlFade(q, best)) * (best ? RL_SCALE_BEST : RL_SCALE_STANDARD);
}

// One octave and its gradient against the lattice coordinates, best quality: x the value, deviation RL_SIGMA; yzw its
// derivatives, exact, continuous from cell to cell with the quintic blend. The relief's slopes and erosion (Relief.hlsli).
float4 RlGradientNoiseD(int3 cell, float3 q, uint seed)
{
    const float3 fl = floor(q);
    cell += (int3)fl;
    q -= fl;
    uint4 h0, h1;
    RlCornerHashes(cell, h0, h1);
    const uint k = seed * 0x27D4EB2Fu;
    const uint4 i0 = RlMix4(h0 + k) >> 24, i1 = RlMix4(h1 + k) >> 24;
    const float3 g000 = rlGradients[i0.x], g100 = rlGradients[i0.y], g010 = rlGradients[i0.z], g110 = rlGradients[i0.w];
    const float3 g001 = rlGradients[i1.x], g101 = rlGradients[i1.y], g011 = rlGradients[i1.z], g111 = rlGradients[i1.w];
    const float3 r = q - 1.0;
    const float n000 = dot(g000, q), n100 = dot(g100, float3(r.x, q.y, q.z)), n010 = dot(g010, float3(q.x, r.y, q.z));
    const float n110 = dot(g110, float3(r.x, r.y, q.z)), n001 = dot(g001, float3(q.x, q.y, r.z));
    const float n101 = dot(g101, float3(r.x, q.y, r.z)), n011 = dot(g011, float3(q.x, r.y, r.z)), n111 = dot(g111, r);
    const float3 s = RlFade(q, true), ds = 30.0 * q * q * r * r;
    // The trilinear blend as a polynomial in the weights, for the values and for the corners' gradients.
    const float k1 = n100 - n000, k2 = n010 - n000, k3 = n001 - n000, k4 = n000 - n100 - n010 + n110;
    const float k5 = n000 - n010 - n001 + n011, k6 = n000 - n100 - n001 + n101;
    const float k7 = n100 + n010 + n001 + n111 - n000 - n110 - n101 - n011;
    const float3 a1 = g100 - g000, a2 = g010 - g000, a3 = g001 - g000, a4 = g000 - g100 - g010 + g110;
    const float3 a5 = g000 - g010 - g001 + g011, a6 = g000 - g100 - g001 + g101;
    const float3 a7 = g100 + g010 + g001 + g111 - g000 - g110 - g101 - g011;
    const float value = n000 + k1 * s.x + k2 * s.y + k3 * s.z + k4 * s.x * s.y + k5 * s.y * s.z + k6 * s.z * s.x
                      + k7 * s.x * s.y * s.z;
    const float3 gradient = g000 + a1 * s.x + a2 * s.y + a3 * s.z + a4 * s.x * s.y + a5 * s.y * s.z + a6 * s.z * s.x
                          + a7 * s.x * s.y * s.z
                          + ds * float3(k1 + k4 * s.y + k6 * s.z + k7 * s.y * s.z, k2 + k5 * s.z + k4 * s.x + k7 * s.z * s.x,
                                        k3 + k6 * s.x + k5 * s.y + k7 * s.x * s.y);
    return float4(value, gradient) * RL_SCALE_BEST;
}

// ---------------------------------------------------------------------------------------------
// Filtering
// ---------------------------------------------------------------------------------------------

// An octave's weight: whole while its wavelength exceeds 2 MESH_BAND_LIMIT cells, gone at MESH_BAND_LIMIT.
float RlWeight(float f)
{
    return saturate(2.0 - 2.0 * f / gMaxFrequency);
}

// erf for x >= 0, Abramowitz and Stegun 7.1.26: error under 1.5e-7.
float RlErf(float x)
{
    const float t = 1.0 / (1.0 + 0.3275911 * x);
    return 1.0 - t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429)))) * exp(-x * x);
}

// The rounded |x|'s mean excess over |x| for a normal noise of deviation RL_SIGMA. Under e = sigma, its series to e^8,
// within 1e-6: the closed form subtracts nearly equal terms there and divides by e.
float RlCreaseExcess(float e)
{
    const float s = RL_SIGMA, s2 = RL_SIGMA * RL_SIGMA, phi0 = 0.39894228;
    [branch] if (e < s)
    {
        const float e2 = e * e, r = e2 / s2;
        return phi0 / s * e2 * (1.0 / 3.0 + r * (-1.0 / 60.0 + r * (1.0 / 840.0 - r / 12096.0)));
    }
    const float u = e / s, er = RlErf(u * 0.70710678), ph = phi0 * exp(-0.5 * u * u);
    return s2 / (2.0 * e) * (er - 2.0 * u * ph) + 0.5 * e * er - 2.0 * s * (phi0 - ph);
}

// |x| rounded by a parabola over |x| < e, e = CREASE_ROUNDING f / gCreaseMaxFrequency, less its mean excess.
float RlCrease(float x, float f)
{
    const float e = CREASE_ROUNDING * f / gCreaseMaxFrequency, a = abs(x);
    [branch] if (e <= 0.0)
        return a;
    return (a >= e ? a : 0.5 * (x * x / e + e)) - RlCreaseExcess(e);
}

// ---------------------------------------------------------------------------------------------
// The fractal sums. Persistence 0.5; octave o has frequency f L^o and seed seed + o.
// ---------------------------------------------------------------------------------------------

float RlFbm(RlPoint pt, double f, double lacunarity, int octaves, uint seed, bool best)
{
    float sum = 0.0, amplitude = 1.0;
    [loop] for (int o = 0; o < octaves; ++o)
    {
        const float w = RlWeight((float)f);
        [branch] if (w <= 0.0)
            break; // the finer octaves are filtered out too, and their mean is 0
        const RlCell l = RlSplit(pt, f);
        sum += amplitude * w * RlGradientNoise(l.cell, l.q + RlShift(o), seed + (uint)o, best);
        f *= lacunarity;
        amplitude *= 0.5;
    }
    return sum;
}

float RlBillow(RlPoint pt, double f, double lacunarity, int octaves, uint seed, bool best)
{
    const float mean = best ? RL_MEAN_BILLOW_BEST : RL_MEAN_BILLOW_STANDARD;
    float sum = 0.5, amplitude = 1.0;
    [loop] for (int o = 0; o < octaves; ++o)
    {
        const float fo = (float)f, w = RlWeight(fo);
        float b = mean;
        [branch] if (w > 0.0)
        {
            const RlCell l = RlSplit(pt, f);
            b = mean + w * (2.0 * RlCrease(RlGradientNoise(l.cell, l.q + RlShift(o), seed + (uint)o, best), fo) - 1.0 - mean);
        }
        sum += amplitude * b;
        f *= lacunarity;
        amplitude *= 0.5;
    }
    return sum;
}

// Offset 1, gain 2, spectral exponent 1: each octave's signal weighted by the previous one's.
float RlRidged(RlPoint pt, double f, double lacunarity, int octaves, uint seed, bool best)
{
    const float mean = best ? RL_MEAN_RIDGED_BEST : RL_MEAN_RIDGED_STANDARD, spectralStep = 1.0 / (float)lacunarity;
    float sum = 0.0, chain = 1.0, spectral = 1.0;
    [loop] for (int o = 0; o < octaves; ++o)
    {
        const float fo = (float)f, w = RlWeight(fo);
        float r = mean;
        [branch] if (w > 0.0)
        {
            const RlCell l = RlSplit(pt, f);
            const float a = 1.0 - RlCrease(RlGradientNoise(l.cell, l.q + RlShift(o), seed + (uint)o, best), fo);
            r = mean + w * (a * a - mean);
        }
        r *= chain;
        chain = saturate(2.0 * r);
        sum += r * spectral;
        f *= lacunarity;
        spectral *= spectralStep;
    }
    return 1.25 * sum - 1.0;
}

// The distance to the nearest seed point, sqrt(3) d - 1, in lattice units: one seed per cell, its corner moved by three
// values in [-1, 1], seeds seed to seed + 2; the cells at +-2 around the point's.
float RlVoronoi(RlPoint pt, double f, uint seed)
{
    const float w = RlWeight((float)f);
    [branch] if (w <= 0.0)
        return RL_MEAN_VORONOI;
    const RlCell l = RlSplit(pt, f);
    const float3 fl = floor(l.q), q = l.q - fl;
    const int3 c = l.cell + (int3)fl;
    float nearest = 1e30;
    [loop] for (int dz = -2; dz <= 2; ++dz)
    {
        [loop] for (int dy = -2; dy <= 2; ++dy)
        {
            [loop] for (int dx = -2; dx <= 2; ++dx)
            {
                const int3 k = c + int3(dx, dy, dz);
                const uint h = RlRound1(RlRound1(RlRound1(0x165667B1u, asuint(k.x)), asuint(k.y)), asuint(k.z));
                const float3 v = float3(dx, dy, dz) + float3(RlValue(h, seed), RlValue(h, seed + 1u), RlValue(h, seed + 2u)) - q;
                nearest = min(nearest, dot(v, v));
            }
        }
    }
    return RL_MEAN_VORONOI + w * (1.7320508 * sqrt(nearest) - 1.0 - RL_MEAN_VORONOI);
}

// The point displaced by power times three fBm of lacunarity 2, standard quality, one per axis, seeds seed, seed + 16,
// seed + 32: the three share the lattice split, the corners' hashes and the blend weights. No displacement at all when
// the first octave is filtered out.
RlPoint RlTurbulence(RlPoint pt, double f, float power, int octaves, uint seed)
{
    [branch] if (RlWeight((float)f) <= 0.0)
        return pt;
    float3 d = 0.0;
    float amplitude = RL_SCALE_STANDARD;
    [loop] for (int o = 0; o < octaves; ++o)
    {
        const float w = RlWeight((float)f);
        [branch] if (w <= 0.0)
            break;
        const RlCell l = RlSplit(pt, f);
        float3 q = l.q + RlShift(o);
        const float3 fl = floor(q);
        q -= fl;
        uint4 h0, h1;
        RlCornerHashes(l.cell + (int3)fl, h0, h1);
        const float3 s = RlFade(q, false);
        const uint so = seed + (uint)o;
        d += amplitude * w * float3(RlCorners(h0, h1, so, q, s), RlCorners(h0, h1, so + 16u, q, s),
                                    RlCorners(h0, h1, so + 32u, q, s));
        f *= 2.0;
        amplitude *= 0.5;
    }
    return RlMakePoint(pt.p + (double3)(power * d));
}

#endif
