// Settings.cpp - see Settings.h.
#include "Settings.h"
#include "FoliageCatalog.hlsli"
#include <algorithm>
#include <cmath>
#include <cwchar>
#include <stdexcept>

void ApplyProfile(double& altitude,double& latitude,double& longitude,double& pitch,double& heading) {
    wchar_t module[MAX_PATH]={};
    GetModuleFileNameW(nullptr,module,MAX_PATH);
    std::wstring directory=module;
    directory.resize(directory.find_last_of(L"\\/"));
    const std::wstring profile=directory+L"\\MyPlanetEngine.ini";
    if (GetFileAttributesW(profile.c_str())==INVALID_FILE_ATTRIBUTES) return;
    auto read=[&](const wchar_t* section,const wchar_t* key,const wchar_t* fallback) {
        wchar_t value[MAX_PATH]={};
        GetPrivateProfileStringW(section,key,fallback,value,MAX_PATH,profile.c_str());
        return std::wstring(value);
    };
    auto put=[](const wchar_t* name,const std::wstring& value) {
        if (!value.empty() && !GetEnvironmentVariableW(name,nullptr,0)) SetEnvironmentVariableW(name,value.c_str());
    };
    put(L"MYPLANETENGINE_FULLSCREEN",read(L"Affichage",L"PleinEcran",L"1"));
    put(L"MYPLANETENGINE_VSYNC",read(L"Affichage",L"VSync",L"0"));
    put(L"MYPLANETENGINE_RESOLUTION",read(L"Affichage",L"Resolution",L"auto"));
    wchar_t absolute[MAX_PATH]={};
    const std::wstring relative=directory+L"\\"+read(L"Rendu",L"Racine",L"..\\..");
    if (!GetFullPathNameW(relative.c_str(),MAX_PATH,absolute,nullptr)) throw std::runtime_error("Invalid runtime root in MyPlanetEngine.ini.");
    const std::wstring root=absolute;
    put(L"MYPLANETENGINE_SCANS",read(L"Rendu",L"Scans",L""));
    put(L"MYPLANETENGINE_AUDIO",read(L"Audio",L"Volumes",L"1 1 1 1"));
    put(L"MYPLANETENGINE_TESTS",root+L"\\tools\\tests\\vues.txt");
    put(L"MYPLANETENGINE_SUN",read(L"Camera",L"Soleil",L"20 120"));
    const std::wstring position=read(L"Camera",L"Position",L"");
    if (!position.empty() && swscanf_s(position.c_str(),L"%lf %lf %lf %lf %lf",&altitude,&latitude,&longitude,&pitch,&heading)!=5)
        throw std::runtime_error("Invalid camera position in MyPlanetEngine.ini.");
}

float DiagnosticView(const wchar_t* name) {
    const wchar_t* views[] = { L"snow", L"rock", L"elevation", L"spread", L"scree", L"grass", L"sand", L"beach",
                               L"wet", L"sea", L"rockall", L"sun", L"objects", L"ground", L"haze", L"lakes", L"rivers",
                               L"forest", L"biome", L"trees", L"temperature", L"humidity", L"season", L"altitude",
                               L"height", L"distance", L"foam", L"glint", L"foamfresh", L"foamold", L"crest", L"clouds",
                               L"weather", L"cloudshadow", L"plates", L"boundaries", L"boundarydist", L"crustage",
                               L"rocktype", L"uplift", L"relief", // the tectonic map's and the relief's (Tectonics.hlsli)
                               L"precipitation", L"wind", L"plantalbedo", L"plantlod", L"forestlight", L"groundalbedo" }; // asset and light validation
    for (int i = 0; i < _countof(views); ++i)
        if (wcscmp(name, views[i]) == 0) return float(i + 1);
    return 0.0f;
}

Settings ReadSettings() {
    Settings s;
    wchar_t erosionMode[32] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_EROSION_MODE", erosionMode, _countof(erosionMode))) {
        int mode; wchar_t extra;
        if (swscanf_s(erosionMode, L"%d %lc", &mode, &extra, 1u) != 1 || mode < 0 || mode > 2)
            throw std::runtime_error("MYPLANETENGINE_EROSION_MODE expects 0, 1 or 2.");
        s.erosionMode = UINT(mode);
    }
    wchar_t cine[32768] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_CINE", cine, _countof(cine))) s.cinePath = cine;
    if (!s.cinePath.empty()) {
        if (!GetEnvironmentVariableW(L"MYPLANETENGINE_CINE_OUT", cine, _countof(cine)))
            throw std::runtime_error("MYPLANETENGINE_CINE_OUT is required.");
        s.cineOut = cine;
        if (GetEnvironmentVariableW(L"MYPLANETENGINE_CINE_VIDEO", cine, _countof(cine))) s.cineVideo = cine;
        if (GetEnvironmentVariableW(L"MYPLANETENGINE_CINE_RANGE", cine, _countof(cine))) {
            int first, count, warm; wchar_t extra;
            if (swscanf_s(cine, L"%d %d %d %lc", &first, &count, &warm, &extra, 1u) != 3 || first < 0 || count <= 0 || warm < 0)
                throw std::runtime_error("MYPLANETENGINE_CINE_RANGE expects first count warmup (non-negative, count > 0).");
            s.cineFirst = first; s.cineCount = count; s.cineWarm = warm;
        }
        if (GetEnvironmentVariableW(L"MYPLANETENGINE_BATCH", nullptr, 0) ||
            GetEnvironmentVariableW(L"MYPLANETENGINE_CAPTURE", nullptr, 0) ||
            GetEnvironmentVariableW(L"MYPLANETENGINE_TREMBLE", nullptr, 0))
            throw std::runtime_error("CINE cannot be combined with another automated mode.");
    }
    wchar_t capturePath[MAX_PATH] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_CAPTURE", capturePath, MAX_PATH) > 0) s.capturePath = capturePath;
    if(GetEnvironmentVariableW(L"MYPLANETENGINE_CAPTURE_FRAME",capturePath,MAX_PATH)>0)
        s.captureFrame=std::max(1,_wtoi(capturePath));
    wchar_t display[64] = {};
    s.fullscreen = GetEnvironmentVariableW(L"MYPLANETENGINE_FULLSCREEN", display, _countof(display)) > 0 && wcscmp(display,L"1")==0;
    s.vsync = !(GetEnvironmentVariableW(L"MYPLANETENGINE_VSYNC", display, _countof(display)) > 0 && wcscmp(display,L"0")==0);
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_RESOLUTION", display, _countof(display)) > 0 && wcscmp(display,L"auto")!=0) {
        unsigned width=0, height=0;
        if (swscanf_s(display,L"%u %u",&width,&height)!=2 || width<320 || height<180 || width>8192 || height>8192)
            throw std::runtime_error("MYPLANETENGINE_RESOLUTION expects width height, from 320x180 to 8192x8192.");
        s.width=width; s.height=height; s.explicitResolution=true;
    }
    s.wireframe = GetEnvironmentVariableW(L"MYPLANETENGINE_WIREFRAME", nullptr, 0) > 0;
    s.taa = !(GetEnvironmentVariableW(L"MYPLANETENGINE_TAA", display, _countof(display)) > 0 && wcscmp(display,L"0")==0);
    s.foliageWhiteNoise = GetEnvironmentVariableW(L"MYPLANETENGINE_FOLIAGE_WHITE_NOISE",display,_countof(display))>0 && wcscmp(display,L"1")==0;
    s.clouds = GetEnvironmentVariableW(L"MYPLANETENGINE_NO_CLOUDS", nullptr, 0) == 0;
    wchar_t full[16] = {};
    s.cloudTemporal = !(GetEnvironmentVariableW(L"MYPLANETENGINE_CLOUD_FULL", full, _countof(full)) > 0 && wcscmp(full, L"1") == 0);
    wchar_t weather[64] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_WEATHER_TIME", weather, _countof(weather)) > 0) {
        const double time = _wtof(weather);
        if (std::isfinite(time) && time >= 0.0) s.weatherTime = time;
    }
    wchar_t view[16] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_VIEW", view, 16) > 0) s.view = DiagnosticView(view);
    wchar_t tests[MAX_PATH] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_TESTS", tests, MAX_PATH) > 0) s.tests = tests;
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_FIRST_TEST", tests, MAX_PATH) > 0) s.firstTest=unsigned(std::max(0,_wtoi(tests)));
    wchar_t batch[MAX_PATH] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_BATCH", batch, MAX_PATH) > 0) {
        s.batch = true;
        s.batchPath = batch;
        wchar_t motion[128] = {};
        if (GetEnvironmentVariableW(L"MYPLANETENGINE_BATCH_MOTION", motion, _countof(motion)) > 0)
            swscanf_s(motion, L"%lf %lf %lf %lf %lf %lf", &s.batchMotion[0], &s.batchMotion[1], &s.batchMotion[2],
                &s.batchMotion[3], &s.batchMotion[4], &s.batchMotion[5]);
    }
    s.faceted = GetEnvironmentVariableW(L"MYPLANETENGINE_FACETED", nullptr, 0) > 0;
    s.objectPop = GetEnvironmentVariableW(L"MYPLANETENGINE_OBJECT_POP", nullptr, 0) > 0;
    s.objectCensus = GetEnvironmentVariableW(L"MYPLANETENGINE_OBJECT_CENSUS", nullptr, 0) > 0;
    s.objectList = GetEnvironmentVariableW(L"MYPLANETENGINE_OBJECT_LIST", nullptr, 0) > 0;
    s.noPlants = GetEnvironmentVariableW(L"MYPLANETENGINE_NO_PLANTS", nullptr, 0) > 0;
    wchar_t tremble[MAX_PATH] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_TREMBLE", tremble, MAX_PATH) > 0) s.tremblePath = tremble;
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_TREMBLE_SPEED", tremble, MAX_PATH) > 0) s.trembleSpeed = _wtof(tremble);
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_TREMBLE_FRAMES", tremble, MAX_PATH) > 0) s.trembleFrames = _wtoi(tremble);
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_FACE_FACTOR", tremble, MAX_PATH) > 0) s.faceFactor = _wtof(tremble);
    wchar_t label[64] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_LABEL", label, 64) > 0) s.label = label;

    wchar_t sun[64] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_SUN", sun, 64) > 0) swscanf_s(sun, L"%lf %lf", &s.sunLatitude, &s.sunLongitude);
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_TIME", sun, 64) > 0) swscanf_s(sun, L"%lf %lf", &s.seaTime, &s.seaTimeRate);
    wchar_t oceanWindEnv[128]={};
    if(GetEnvironmentVariableW(L"MYPLANETENGINE_OCEAN_WIND",oceanWindEnv,128)>0)
        swscanf_s(oceanWindEnv,L"%f %f %f",&s.oceanSpeed,&s.oceanDirection,&s.oceanSwell);

    wchar_t choice[32] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_VAISSEAU", choice, 32) > 0) {
        s.ship = choice;
        s.shipSet = true;
    }
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_VERRIERE", choice, 32) > 0)
        s.glassTest = !wcscmp(choice, L"pluie") ? 1.0f : !wcscmp(choice, L"nuage") ? 2.0f : !wcscmp(choice, L"givre") ? 3.0f : 0.0f;
    wchar_t audio[128] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_AUDIO", audio, _countof(audio))) {
        wchar_t extra;
        if (swscanf_s(audio,L"%f %f %f %f %lc",&s.audioMaster,&s.audioFootsteps,&s.audioAmbience,&s.audioShip,&extra,1u)!=4)
            throw std::runtime_error("MYPLANETENGINE_AUDIO expects master footsteps ambience ship, each from 0 to 1.");
        for (float gain : {s.audioMaster,s.audioFootsteps,s.audioAmbience,s.audioShip})
            if (!std::isfinite(gain) || gain<0 || gain>1) throw std::runtime_error("Audio gains must be finite and between 0 and 1.");
    }

    wchar_t foliageAssets[MAX_PATH] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_FOLIAGE_ASSETS", foliageAssets, MAX_PATH) > 0) s.foliageAssets = foliageAssets;
    wchar_t warm[32] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_FOLIAGE_WARMUP", warm, _countof(warm)) > 0)
        s.foliageWarm = static_cast<UINT>(std::max(1, std::min(_wtoi(warm), 10000)));
    wchar_t samples[32] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_FOLIAGE_SAMPLES", samples, _countof(samples)) > 0)
        s.foliageSamples = static_cast<UINT>(std::max(1, std::min(_wtoi(samples), 10000)));
    wchar_t scans[MAX_PATH] = {};
    wchar_t testLod[32]={};
    if (s.batch && GetEnvironmentVariableW(L"MYPLANETENGINE_FOLIAGE_TEST_LOD",testLod,_countof(testLod))>0) {
        s.foliageTestLod=_wtoi(testLod);
        if (s.foliageTestLod<0 || s.foliageTestLod>=FOLIAGE_MESH_LODS) throw std::runtime_error("Invalid foliage validation LOD.");
    }
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_SCANS", scans, MAX_PATH) > 0) s.scans = scans;
    wchar_t map[MAX_PATH] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_MAP", map, MAX_PATH) > 0) s.map = map;
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_SEED", map, MAX_PATH) > 0) s.seed = uint32_t(_wtoi(map));
    wchar_t glare[8] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_GLARE", glare, _countof(glare)))
        s.glare = wcscmp(glare, L"0") != 0;
    if (!s.cinePath.empty()) s.vsync = false;
    s.coordinates = !s.Automated();
    wchar_t coordinates[8] = {};
    if (GetEnvironmentVariableW(L"MYPLANETENGINE_COORDINATES", coordinates, _countof(coordinates)))
        s.coordinates = wcscmp(coordinates, L"0") != 0;
    return s;
}
