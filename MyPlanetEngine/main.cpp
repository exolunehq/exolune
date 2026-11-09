#include "D3DApp.h"
#include <cstdio>
#include <stdexcept>

// Usage: MyPlanetEngine.exe [altitude in metres] [latitude] [longitude] [pitch below the horizon] [heading east
// of north], in degrees. The title shows the camera's own, to come back to a view.
// The default start is 300 km above a continent of the tectonic relief, seed 0, a collision chain on the horizon to the
// north (docs/spec-relief-tectonique.md).
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE, LPSTR cmdLine, int)
{
    try
    {
        SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
        double altitude = 300000.0, latitude = -12.0, longitude = 116.875, pitchDown = 50.0, heading = 0.0;
        ApplyProfile(altitude,latitude,longitude,pitchDown,heading);
        if (cmdLine) sscanf_s(cmdLine, "%lf %lf %lf %lf %lf", &altitude, &latitude, &longitude, &pitchDown, &heading);
        D3DApp app(hInstance, altitude > 0.0 ? altitude : 300000.0, latitude, longitude, pitchDown, heading);
        if (!app.Initialize())
            return 0;

        return app.Run();
    }
    catch (const std::exception& e)
    {
        // A hidden batch must fail visibly to its caller instead of waiting on an invisible message box.
        wchar_t batch[MAX_PATH] = {};
        if (GetEnvironmentVariableW(L"MYPLANETENGINE_CINE", batch, MAX_PATH) > 0) {
            FILE* log = nullptr;
            const std::wstring path = std::wstring(batch) + L".error.txt";
            if (_wfopen_s(&log, path.c_str(), L"w") == 0 && log) {
                fprintf(log, "%s\n", e.what()); fclose(log);
            }
            return 1;
        }
        if (GetEnvironmentVariableW(L"MYPLANETENGINE_BATCH", batch, MAX_PATH) > 0) {
            FILE* log = nullptr;
            const std::wstring path = std::wstring(batch) + L".error.txt";
            if (_wfopen_s(&log, path.c_str(), L"w") == 0) {
                fprintf(log, "%s\n", e.what());
                fclose(log);
            }
            return 1;
        }
        if (GetEnvironmentVariableW(L"MYPLANETENGINE_CAPTURE", batch, MAX_PATH)>0) {
            FILE* log=nullptr;
            if(_wfopen_s(&log,(std::wstring(batch)+L".error.txt").c_str(),L"w")==0 && log) {
                fprintf(log,"%s\n",e.what());fclose(log);
            }
        }
        if (GetEnvironmentVariableW(L"MYPLANETENGINE_CITY_PROBE", nullptr, 0) ||
            GetEnvironmentVariableW(L"MYPLANETENGINE_CAPTURE", nullptr, 0) ||
            GetEnvironmentVariableW(L"MYPLANETENGINE_TREMBLE", nullptr, 0))
            fprintf(stderr, "MyPlanetEngine: %s\n", e.what());
        else
            MessageBoxA(nullptr, e.what(), "MyPlanetEngine", MB_OK | MB_ICONERROR);
        return 1;
    }
}
