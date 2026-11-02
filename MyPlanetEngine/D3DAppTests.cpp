// D3DAppTests.cpp - D3DApp's test views, to judge a change in flight (D3DApp.h): a "Tests" palette beside the render
// window, a button for each, and F1 to F12.
#include "D3DApp.h"
#include "Ocean.h"
#include <fstream>
#include <sstream>

// The test views' file, MYPLANETENGINE_TESTS: one per line, UTF-8, "label | altitude latitude longitude pitchDown heading
// [view] [| sunLatitude sunLongitude [| windSpeed windDirection swellHeight]]"; # starts a comment.
void D3DApp::ReadTests() {
    if (mSettings.tests.empty()) return;
    std::ifstream file(mSettings.tests.c_str(), std::ios::binary);
    for (std::string bytes; std::getline(file, bytes);) {
        if (bytes.size() >= 3 && bytes.compare(0, 3, "\xEF\xBB\xBF") == 0) bytes.erase(0, 3); // a BOM
        wchar_t wide[1024] = {};
        MultiByteToWideChar(CP_UTF8, 0, bytes.c_str(), -1, wide, 1024);
        std::wstring line(wide);
        const size_t bar = line.find(L'|');
        if (line.empty() || line[0] == L'#' || bar == std::wstring::npos) continue;
        TestView t = {};
        t.label = line.substr(0, bar);
        t.label.erase(t.label.find_last_not_of(L" \t") + 1);
        t.label.erase(0, t.label.find_first_not_of(L" \t"));
        const size_t sunBar = line.find(L'|', bar + 1);
        std::wistringstream place(line.substr(bar + 1, sunBar == std::wstring::npos ? std::wstring::npos : sunBar - bar - 1));
        if (!(place >> t.altitude >> t.latitude >> t.longitude >> t.pitchDown >> t.heading)) continue;
        std::wstring view;
        if (place >> view) { t.walk = view==L"marche"; t.view = DiagnosticView(view.c_str()); }
        if (sunBar != std::wstring::npos) {
            std::wistringstream sun(line.substr(sunBar + 1));
            t.sun = static_cast<bool>(sun >> t.sunLatitude >> t.sunLongitude);
        }
        const size_t windBar=sunBar==std::wstring::npos?std::wstring::npos:line.find(L'|',sunBar+1);
        if(windBar!=std::wstring::npos) {
            std::wistringstream wind(line.substr(windBar+1));
            t.wind=static_cast<bool>(wind>>t.windSpeed>>t.windDirection>>t.swellHeight);
        }
        mTests.push_back(t);
    }
}

// The "Tests" palette: a small tool window owned by the render window, on its right, one button per test view.
void D3DApp::CreateTestsWindow() {
    if (mTests.empty() || mFullscreen) return;
    WNDCLASS wc = {};
    wc.lpfnWndProc = TestsProc;
    wc.hInstance = mhAppInst;
    wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wc.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_BTNFACE + 1);
    wc.lpszClassName = L"MyPlanetEngineTests";
    RegisterClass(&wc);
    const int width = 380, button = 30, gap = 6;
    const DWORD style = WS_CAPTION | WS_SYSMENU;
    RECT r = { 0, 0, width, gap + int(mTests.size()) * (button + gap) };
    AdjustWindowRectEx(&r, style, FALSE, WS_EX_TOOLWINDOW);
    RECT main = {};
    GetWindowRect(mhMainWnd, &main);
    mTestsWnd = CreateWindowEx(WS_EX_TOOLWINDOW, wc.lpszClassName, L"Tests", style, main.right + 4, main.top,
        r.right - r.left, r.bottom - r.top, mhMainWnd, nullptr, mhAppInst, this);
    if (!mTestsWnd) return;
    const HFONT font = static_cast<HFONT>(GetStockObject(DEFAULT_GUI_FONT));
    for (size_t i = 0; i < mTests.size(); ++i) {
        const std::wstring text = (i < 12 ? L"F" + std::to_wstring(i + 1) + L"   " : L"") + mTests[i].label;
        HWND b = CreateWindow(L"BUTTON", text.c_str(), WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON | BS_LEFT, gap, gap + int(i) * (button + gap),
            width - 2 * gap, button, mTestsWnd, reinterpret_cast<HMENU>(static_cast<INT_PTR>(100 + i)), mhAppInst, nullptr);
        SendMessage(b, WM_SETFONT, reinterpret_cast<WPARAM>(font), TRUE);
    }
    ShowWindow(mTestsWnd, SW_SHOWNOACTIVATE);
}

// The camera at test `index`: its place, its sun or the startup one (the previous test's could leave it in the
// night); the smoothing starts afresh; the focus back to fly.
void D3DApp::GoToTest(size_t index) {
    const TestView& t = mTests[index];
    const bool walking = mView==View::Walk;
    if (walking) SetView(mWalkReturnView);
    mGroundHeight = 0.0; // the previous place's ground is not a valid collision sample at this one
    mOceanElevation = -1000.0f;
    if (t.wind) {
        mOceanSpeed = t.windSpeed; mOceanDirection = t.windDirection; mOceanSwell = t.swellHeight;
        mOcean->SetWind(mOceanSpeed, mOceanDirection, mOceanSwell);
    }
    // The test palette follows the shared cloud wind, without resetting the weather clock.
    const double windLongitude = mWeatherTime * kWeatherWindSpeed / PlanetRadius * 180.0 / XM_PI;
    PlaceCamera(t.latitude, t.longitude + windLongitude, t.pitchDown, t.heading, t.altitude);
    if (mView != View::Free) PlaceShipAtCamera();
    mStartWalking = t.walk || walking;
    mSunDir = t.sun ? LatLonToDir(t.sunLatitude, t.sunLongitude) : mStartSunDir;
    mDiagnosticView = t.view;
    mHistoryValid = false;
    mPlanetPlantPlacement.Reset();
    mTestLabel = t.label;
    SetForegroundWindow(mhMainWnd);
}

LRESULT CALLBACK D3DApp::TestsProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    if (msg == WM_NCCREATE)
        SetWindowLongPtr(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(reinterpret_cast<CREATESTRUCT*>(lParam)->lpCreateParams));
    D3DApp* app = reinterpret_cast<D3DApp*>(GetWindowLongPtr(hwnd, GWLP_USERDATA));
    if (app && msg == WM_COMMAND && LOWORD(wParam) >= 100 && size_t(LOWORD(wParam) - 100) < app->mTests.size()) {
        app->GoToTest(LOWORD(wParam) - 100);
        return 0;
    }
    if (msg == WM_CLOSE) { ShowWindow(hwnd, SW_HIDE); return 0; } // the palette hides; the app goes on
    return DefWindowProc(hwnd, msg, wParam, lParam);
}
