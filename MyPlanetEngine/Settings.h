// Settings.h - the launch settings: the MYPLANETENGINE_* environment variables, read once at startup, and the profile
// beside the executable that fills those left unset.
#pragma once

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <string>

struct Settings
{
    // The display: MYPLANETENGINE_FULLSCREEN=1, MYPLANETENGINE_VSYNC=0, MYPLANETENGINE_RESOLUTION="width height" or auto.
    bool fullscreen = false, vsync = true, explicitResolution = false;
    UINT width = 1280, height = 720;
    bool wireframe = false; // MYPLANETENGINE_WIREFRAME: key F at startup
    bool faceted = false;   // MYPLANETENGINE_FACETED: key R at startup
    bool taa = true;        // MYPLANETENGINE_TAA=0 disables temporal smoothing; diagnostics bypass it; key T
    bool foliageWhiteNoise = false; // functional control for the coverage sequence
    bool glare = true;      // The lens's glare; MYPLANETENGINE_GLARE=0 disables it for inspection.
    float view = 0.0f;      // MYPLANETENGINE_VIEW: a diagnostic view (DiagnosticView), 0 for none
    // MYPLANETENGINE_FACE_FACTOR: the face's half-width over the height above the ground (keys K, L).
    double faceFactor = 2.0;
    std::wstring label;     // MYPLANETENGINE_LABEL, shown in the title: tells side-by-side builds apart
    UINT erosionMode = 2;   // MYPLANETENGINE_EROSION_MODE: key 1's comparison, 0 none, 1 ravines, 2 full (default)

    // The clouds: always, unless MYPLANETENGINE_NO_CLOUDS (key N); in their temporal pass, unless
    // MYPLANETENGINE_CLOUD_FULL=1. Their weather starts at MYPLANETENGINE_WEATHER_TIME (s).
    bool clouds = true, cloudTemporal = true;
    double weatherTime = 0.0;

    // The sun: high in the sky over the default start, or MYPLANETENGINE_SUN="latitude longitude".
    double sunLatitude = -5.0, sunLongitude = 125.0;
    // The sea: its clock, MYPLANETENGINE_TIME="start [rate]"; its wind and swell at startup,
    // MYPLANETENGINE_OCEAN_WIND="speed direction swell".
    double seaTime = 0.0, seaTimeRate = 1.0;
    float oceanSpeed = 12.0f, oceanDirection = 70.0f, oceanSwell = 1.8f;

    // MYPLANETENGINE_VAISSEAU selects the first view (cockpit, poursuite, sans, libre, orbite, altitude-fixe or marche); the glass's
    // weather forced for the captures, MYPLANETENGINE_VERRIERE=pluie, nuage or givre (1, 2, 3).
    std::wstring ship;
    bool shipSet = false;
    float glassTest = 0.0f;
    // MYPLANETENGINE_AUDIO="master footsteps ambience ship", independent gains in [0,1]; Y mutes the master.
    float audioMaster = 1.0f, audioFootsteps = 1.0f, audioAmbience = 1.0f, audioShip = 1.0f;

    // The objects: MYPLANETENGINE_OBJECT_POP, they pop whole instead of growing, the pop measure's reference;
    // MYPLANETENGINE_OBJECT_CENSUS, in batch mode, every cell's candidate recorded, nothing drawn;
    // MYPLANETENGINE_OBJECT_LIST, in batch mode, the objects and plants of each capture.
    bool objectPop = false, objectCensus = false, objectList = false;
    // The plants: MYPLANETENGINE_NO_PLANTS, none drawn, the ground's canopy everywhere (docs/recherche-vegetation.md);
    // their catalogue, MYPLANETENGINE_FOLIAGE_ASSETS, empty for the first above the executable; the frames a batch job
    // gives them before it measures, MYPLANETENGINE_FOLIAGE_WARMUP, then measures, MYPLANETENGINE_FOLIAGE_SAMPLES.
    bool noPlants = false;
    std::wstring foliageAssets;
    // Optional authored city bank and a hidden terrain export for its planner.
    std::wstring cityAssets, cityProbe;
    UINT foliageWarm = 120, foliageSamples = 120;
    int foliageTestLod = -1; // offscreen validation only

    // The photo scans' folder, MYPLANETENGINE_SCANS; empty for the first folder named scans above the executable.
    std::wstring scans;
    // MYPLANETENGINE_MAP: the planet map's arrays and times saved there (D3DApp::CreatePlanetMap).
    std::wstring map;
    // MYPLANETENGINE_SEED: the seed of the tectonic map and the climate, for comparisons between planets; the detail's noise
    // keeps PLANET_SEED (PlanetSettings.hlsli).
    uint32_t seed = 0;
    // MYPLANETENGINE_TESTS: the test views' file (D3DApp::ReadTests).
    std::wstring tests;
    unsigned firstTest=0; // optional one-based starting view from the review route

    // The benches (D3DApp.h): MYPLANETENGINE_CAPTURE, a .bmp path, and MYPLANETENGINE_CAPTURE_FRAME, the frame saved
    // there; MYPLANETENGINE_TREMBLE, a path prefix, its speed, MYPLANETENGINE_TREMBLE_SPEED, and frames,
    // MYPLANETENGINE_TREMBLE_FRAMES; MYPLANETENGINE_BATCH, a list of jobs, and MYPLANETENGINE_BATCH_MOTION: per frame
    // after the settling, degrees of heading and of latitude, seconds of weather, the height's factor (the camera
    // descends to the job's); then frames held still before the capture; then the share of the height flown north per
    // frame, as the app's speed.
    std::wstring capturePath;
    UINT captureFrame = 200; // long enough for the title to show the GPU times
    std::wstring tremblePath;
    double trembleSpeed = 1.0;
    UINT trembleFrames = 24;
    std::wstring batchPath;
    bool batch = false; // MYPLANETENGINE_BATCH set: hidden, and quits even when no job could be read
    bool coordinates = true; // I: screenshot coordinates; off by default in automated captures
    double batchMotion[6] = {};

    std::wstring cinePath, cineOut, cineVideo; // cineVideo: an .mp4 the frames are encoded to, instead of BMP files
    UINT cineFirst = 0, cineCount = 0, cineWarm = 120; // count 0: to the end

    // The benches render without showing the window, in the free camera, the sea on a fixed clock.
    bool Automated() const { return batch || !capturePath.empty() || !tremblePath.empty() || !cinePath.empty() || !cityProbe.empty(); }
};

// The profile MyPlanetEngine.ini beside the executable, if any: it sets the variables still unset, so that hidden
// captures and the launchers keep their own, and gives the start's camera.
void ApplyProfile(double& altitude, double& latitude, double& longitude, double& pitch, double& heading);

// The settings, from the environment.
Settings ReadSettings();

// The diagnostic view named `name`, in the order of PixelShader.hlsl's GroundAt, then the sea's, the clouds' and the
// tectonic map's and the relief's; 0 for none.
float DiagnosticView(const wchar_t* name);
