// The transport handbook and its flight strip share the same phase, controls and measurements as the ship.
#include "D3DApp.h"
#include "GpuHelpers.h"
#include <algorithm>
#include <cstring>
#include <cwchar>

namespace {
    using Rig=TransportEquipment;
    using Phase=Rig::Phase;
    constexpr int MenuW=810, MenuH=608, StripW=450, StripH=82;
    constexpr COLORREF Back=RGB(21,31,39), Band=RGB(29,43,52), Rule=RGB(60,78,86);
    constexpr COLORREF Ink=RGB(237,242,242), Muted=RGB(187,202,206), Accent=RGB(128,223,211), Warm=RGB(245,198,134);

    // GDI rasterizes the small UTF-16 panel on changes. Only the final display pass samples it.
    struct Canvas {
        HDC dc=CreateCompatibleDC(nullptr);
        HBITMAP bitmap=nullptr;
        HGDIOBJ oldBitmap=nullptr, oldFont=nullptr;
        HFONT fonts[4]={};
        void* pixels=nullptr;
        Canvas(int w,int h) {
            BITMAPINFO info={};
            info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);
            info.bmiHeader.biWidth=w; info.bmiHeader.biHeight=-h;
            info.bmiHeader.biPlanes=1; info.bmiHeader.biBitCount=32; info.bmiHeader.biCompression=BI_RGB;
            bitmap=CreateDIBSection(dc,&info,DIB_RGB_COLORS,&pixels,nullptr,0);
            if (!pixels) return;
            oldBitmap=SelectObject(dc,bitmap);
            const int sizes[]={15,17,20,30}, weights[]={FW_SEMIBOLD,FW_NORMAL,FW_SEMIBOLD,FW_SEMIBOLD};
            for (int i=0;i<4;++i)
                fonts[i]=CreateFontW(-sizes[i],0,0,0,weights[i],FALSE,FALSE,FALSE,DEFAULT_CHARSET,
                    OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,ANTIALIASED_QUALITY,DEFAULT_PITCH,L"Segoe UI");
            oldFont=SelectObject(dc,fonts[1]);
            SetBkMode(dc,TRANSPARENT);
            fill(0,0,w,h,Back);
        }
        ~Canvas() {
            if (oldFont) SelectObject(dc,oldFont);
            if (oldBitmap) SelectObject(dc,oldBitmap);
            for (HFONT font:fonts) if (font) DeleteObject(font);
            if (bitmap) DeleteObject(bitmap);
            DeleteDC(dc);
        }
        void fill(int x,int y,int w,int h,COLORREF color) {
            const RECT r={x,y,x+w,y+h};
            SetDCBrushColor(dc,color);
            FillRect(dc,&r,(HBRUSH)GetStockObject(DC_BRUSH));
        }
        void line(int x,int y,int w,const std::wstring& value,int font=1,COLORREF color=Ink) {
            RECT r={x,y,x+w,y+42};
            SelectObject(dc,fonts[font]);
            SetTextColor(dc,color);
            DrawTextW(dc,value.c_str(),int(value.size()),&r,DT_SINGLELINE|DT_END_ELLIPSIS|DT_NOPREFIX);
        }
        void row(int x,int y,const std::wstring& key,const std::wstring& action) {
            fill(x,y,104,23,Band);
            line(x+7,y+1,95,key,0,Accent);
            line(x+114,y-1,263,action);
        }
    };

    std::wstring KeyPair(UINT a,UINT b) {
        return std::wstring(1,wchar_t(a))+L" / "+wchar_t(b);
    }
}

void D3DApp::SetTransportMenu(bool open) {
    mTransportMenu=open; mTransportPanelRefresh=-1;
    mRawDx=mRawDy=0; mLooking=false;
    HoldMouse(!open && mView!=View::Free && GetForegroundWindow()==mhMainWnd);
}

bool D3DApp::TransportPanelClick(int x,int y) {
    if (!mTransportPanelVisible || !TransportInView() || !PtInRect(&mTransportPanelRect,POINT{x,y})) return false;
    if (!mTransportMenu) { SetTransportMenu(true); return true; }
    const RECT& r=mTransportPanelRect;
    if ((x-r.left)*MenuW >= (MenuW-166)*(r.right-r.left) && (y-r.top)*MenuH < 62*(r.bottom-r.top))
        SetTransportMenu(false);
    return true;
}

void D3DApp::DrawTransportPanel() {
    const bool visible=TransportInView() && mCine.empty() && !mSettings.Automated() &&
        (!mFlightTake.Connected() || mTransportMenu);
    if (!mTransportPanelBuffer) {
        mTransportPanelBuffer=CreateBuffer(md3dDevice.Get(),32+4*MenuW*MenuH,D3D12_HEAP_TYPE_UPLOAD,D3D12_RESOURCE_STATE_GENERIC_READ);
        mTransportPanelRefresh=-1;
    }
    mCommandList->SetGraphicsRootShaderResourceView(10,mTransportPanelBuffer->GetGPUVirtualAddress());
    const int w=mTransportMenu ? MenuW : StripW, h=mTransportMenu ? MenuH : StripH;
    const double scale=std::min({std::max(1.0,mClientWidth/1440.0),(mClientWidth-12.0)/w,(mClientHeight-12.0)/h,1.55});
    const int dw=std::max(1,int(w*scale)), dh=std::max(1,int(h*scale));
    const int x=mTransportMenu ? (int(mClientWidth)-dw)/2 : int(mClientWidth)-dw-8;
    const int y=mTransportMenu ? (int(mClientHeight)-dh)/2 : (mClientWidth<900 ? int(mClientHeight)-dh-8 : 10);
    const RECT rect={x,y,x+dw,y+dh};
    if (visible==mTransportPanelVisible && EqualRect(&rect,&mTransportPanelRect) && mTransportPanelRefresh>=0 &&
        (!visible || mTransportMenu || mClock<mTransportPanelRefresh)) return;
    mTransportPanelVisible=visible; mTransportPanelRect=rect; mTransportPanelRefresh=mClock+.20;
    UINT* out=nullptr; CD3DX12_RANGE noRead(0,0);
    Check(mTransportPanelBuffer->Map(0,&noRead,reinterpret_cast<void**>(&out)),"Transport panel map failed.");
    UINT header[8]={UINT(x),UINT(y),visible ? UINT(dw) : 0,UINT(dh),UINT(w),UINT(h),UINT(mTransportMenu),0};
    size_t bytes=sizeof(header);
    if (visible) {
        Canvas c(w,h);
        if (c.pixels) {
            const auto& rig=mTransport;
            const bool inAir=mFlightCues.density >= Rig::AtmosphericControlDensity;
            const double feet=std::max(0.0,TransportClearance()-Rig::PadDepth);
            const double groundSpeed=Length(mShipVelocity);
            const auto up=SurfaceUp(mShipPos);
            const double verticalSpeed=Dot(mShipVelocity,up);
            const double horizontalSpeed=Length(mShipVelocity-up*verticalSpeed);
            const bool manualApproach=rig.phase==Phase::Flight && rig.gearNearGround && feet<150 && groundSpeed<45;
            const bool wingborne=rig.airAuthority>=.999;
            const wchar_t* phase=wingborne ? L"Vol sur les ailes" : L"Vol manuel";
            const wchar_t* action=L"L  Atterrissage automatique";
            if (feet>Rig::MaxApproachHeight || groundSpeed*3.6>Rig::MaxApproachKmh)
                action=L"Atterrissage auto sous 5 km et 1 200 km/h";
            if (manualApproach) {
                phase=L"Approche manuelle";
                action=L"X  Freiner    •    Ctrl  Descendre    •    L  Automatique";
                if (rig.precisionHover) {
                    phase=groundSpeed<.2 ? L"Stationnaire manuel" : L"Approche manuelle · précision";
                    action=L"Espace  Monter    •    Ctrl  Descendre    •    Relâcher  Stabiliser";
                }
            }
            wchar_t seqPhase[96]={};
            if (rig.phase==Phase::Approach) {
                phase=horizontalSpeed>3 ? L"Approche auto · freinage" : L"Approche auto · descente";
                if (rig.position[Rig::Gear]<1) phase=L"Approche auto · sortie du train";
                if (feet<9 && !Landable(CurrentLandingSite())) phase=L"Recherche d’un sol praticable";
                action=L"L  Reprendre le pilotage";
            } else if (rig.phase==Phase::Parked) {
                phase=L"Posée · moteurs coupés";
                action=rig.CanWalk() ? L"J  Descendre à pied    •    L  Décoller" :
                    rig.target[Rig::Hatch] ? L"Escalier en mouvement    •    L  Décoller" : L"5  Ouvrir l’escalier    •    L  Décoller";
                if (!mTransportMenu && mGameplay.Active(Gameplay::SequenceId::ShuttleBoarding)) {
                    const auto& seq=mGameplay.State(Gameplay::SequenceId::ShuttleBoarding);
                    if (seq.phase==Gameplay::SequencePhase::Armed) phase=L"Embarquement · ouverture de l’escalier";
                    else if (seq.phase==Gameplay::SequencePhase::Running) {
                        swprintf_s(seqPhase,L"Embarquement en cours · %u/%u",seq.done,seq.total);
                        phase=seqPhase;
                    } else if (seq.phase==Gameplay::SequencePhase::Completed && rig.CanWalk()) {
                        action=L"Équipage à bord  ·  J Descendre  •  L Décoller";
                    }
                }
            } else if (rig.phase==Phase::Closing) {
                phase=L"Départ · fermeture de l’escalier"; action=L"L  Annuler le départ";
            } else if (rig.phase==Phase::Takeoff) {
                phase=L"Décollage vertical"; action=L"Montée automatique vers le stationnaire à 8 m";
            } else if (!manualApproach && rig.phase==Phase::Flight && mFlightPilot.holding) phase=L"Vol stationnaire";
            if (rig.brakeToHover) {
                phase=mFlightPilot.holding ? L"Vol stationnaire" : L"Freinage vers le stationnaire";
                action=mFlightPilot.holding ? L"Espace / Ctrl  Hauteur    •    Molette ↑  Repartir" :
                    L"Freinage engagé    •    Molette ↑  Reprendre les gaz";
            }
            const wchar_t* wing=rig.position[Rig::Wings]==0 ? L"rentrées" : rig.position[Rig::Wings]==1 ? L"déployées" :
                rig.target[Rig::Wings] ? L"en sortie" : L"en rentrée";
            const std::wstring wingMode=rig.GroundLocked() ? L"au sol" : rig.wingProtected ? L"protection" : rig.phase!=Phase::Flight ? L"manœuvre" :
                rig.manual[Rig::Wings]>=0 ? L"manuel" : L"auto";
            wchar_t air[128];
            swprintf_s(air,L"Ailes %ls (%ls)    ·    %d km/h indiqués",wing,wingMode.c_str(),int(std::lround(mFlightCues.equivalentAirspeed*3.6)));
            const bool notice=mClock<mTransportNoticeUntil;
            if (!mTransportMenu) {
                c.fill(0,0,3,h,Accent);
                c.line(14,7,w-155,phase,2);
                c.fill(w-131,7,122,25,Band);
                c.line(w-122,9,114,L"P   Commandes",0,Accent);
                c.line(14,35,w-28,notice ? mTransportNotice : action,0,notice ? Warm : Accent);
                c.line(14,56,w-28,air,0,Muted);
            } else {
                c.fill(0,0,w,62,Band);
                c.line(23,10,620,L"Commandes de la navette",3);
                c.fill(w-159,16,140,30,Back);
                c.line(w-150,20,132,L"Échap · Fermer",0,Accent);
                c.line(24,76,360,L"Pilotage",2);
                c.line(415,76,360,L"Atterrissage et équipements",2);
                c.fill(24,105,367,1,Rule); c.fill(415,105,371,1,Rule);
                c.row(24,116,L"Souris",L"Orienter la navette");
                c.row(24,143,L"Molette",inAir ? L"Régler les gaz · 0 = stationnaire" : L"Régler les gaz · 0 = vol inertiel");
                c.row(24,170,L"↑  /  Maj",inAir ? L"Caler plein gaz / surpuissance" : L"Maintenir plein gaz / surpuissance");
                c.row(24,197,L"↓  /  X",inAir ? L"Freiner jusqu’au stationnaire" : L"Maintenir pour freiner et s’arrêter");
                c.row(24,224,L"Espace/Ctrl",wingborne ? L"Cabrer / piquer" : L"Monter / descendre (ou "+KeyPair(mMoveKeys[0],mMoveKeys[1])+L")");
                c.row(24,251,KeyPair(mMoveKeys[2],mMoveKeys[3]),wingborne ? L"Virer à gauche / à droite" : L"Translation gauche / droite");
                c.row(24,278,KeyPair(mMoveKeys[4],mMoveKeys[5]),L"Roulis gauche / droite");
                c.row(24,305,L"Tab",L"Changer de vue");
                c.row(24,332,L"Clic droit",L"Regarder autour (R recentre)");
                c.row(415,116,L"L",L"Atterrir, annuler ou décoller");
                c.row(415,143,L"J",L"Sortir à pied / remonter à bord");
                c.row(415,170,L"2",L"Sortir / rentrer les ailes");
                c.row(415,197,L"3",L"Sortir / rentrer le train");
                c.row(415,224,L"4",L"Ouvrir / fermer l’aérofrein");
                c.row(415,251,L"5",L"Ouvrir / fermer l’escalier au sol");
                c.row(415,278,L"6",L"Rétablir les automatismes");
                c.row(415,305,L"Y / Entrée",L"Activer le son / appeler la radio");
                c.row(415,332,L"M / Alt",L"Libérer le pointeur");
                c.fill(0,368,w,h-368,Band);
                c.line(24,378,w-48,std::wstring(phase)+L"    ·    "+action,1,Accent);
                wchar_t thresholds[140];
                swprintf_s(thresholds,L"%ls. Sortie à %d km/h, rentrée à %d km/h.",air,Rig::WingOpenKmh,Rig::WingCloseKmh);
                c.line(24,406,w-48,thresholds,1);
                swprintf_s(thresholds,L"Protection à %d km/h indiqués ou 48 %% de chauffe. Réarmement sous %d km/h et 22 %%.",
                    Rig::WingProtectKmh,Rig::WingRearmKmh);
                c.line(24,432,w-48,thresholds,1,Muted);
                wchar_t steering[160];
                if (rig.GroundLocked()) wcscpy_s(steering,L"Navette posée · gouvernes au neutre, jets de stabilisation coupés.");
                else if (wingborne) wcscpy_s(steering,L"Gouvernes actives · roulis et tangage aux ailes, lacet à la dérive.");
                else if (rig.airAuthority>0) swprintf_s(steering,L"Transition · gouvernes %.0f %% et jets de stabilisation %.0f %%.",
                    100*rig.airAuthority,100*(1-rig.airAuthority));
                else wcscpy_s(steering,L"Pilotage aux jets de stabilisation · gouvernes au neutre.");
                c.line(24,455,w-48,steering,1,Muted);
                wchar_t power[170];
                wchar_t regime[80]=L"Dans le vide, relâcher ↑ rend la main à la molette.";
                if (inAir) swprintf_s(regime,L"Plein panache dès le cran %.0f en atmosphère.",FlightDynamics::FirstBurnNotch);
                swprintf_s(power,L"Gaz %.0f/%.0f    ·    Réacteurs principaux %.0f %%    ·    %ls",mThrottle,FlightDynamics::ThrottleNotches,
                    100*mTransportExhaust.MainPower(),regime);
                c.line(24,480,w-48,power,1,Accent);
                c.line(24,510,w-48,L"Auto sous 5 km et 1 200 km/h sol. En manuel, gaz à zéro, Ctrl descend et relâcher stabilise.",1);
                c.line(24,537,w-48,L"H  Regard libre     ·     U  Viseur     ·     I  Coordonnées",0,Muted);
                wchar_t readings[180];
                swprintf_s(readings,L"Vol en pause    ·    Hauteur des patins %.0f m    ·    Vitesse sol %.0f km/h    ·    Verticale %+.1f m/s",
                    feet,horizontalSpeed*3.6,verticalSpeed);
                c.line(24,577,w-48,readings,0,Muted);
            }
            GdiFlush();
            std::memcpy(out+8,c.pixels,size_t(w)*h*4); bytes+=size_t(w)*h*4;
        } else header[2]=0;
    }
    std::memcpy(out,header,sizeof(header));
    const CD3DX12_RANGE written(0,bytes);
    mTransportPanelBuffer->Unmap(0,&written);
}
