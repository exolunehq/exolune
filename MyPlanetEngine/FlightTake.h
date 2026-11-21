// Optional controller for a live gameplay take. The wire only accepts ordinary player input.
// Each little-endian double packet is one Windows pipe message. The pilot owns the named pipe.
#pragma once
#include <windows.h>
#include <array>
#include <cmath>
#include <stdexcept>
#include <string>

class FlightTake {
public:
    enum Input { MouseX, MouseY, Wheel, Look, CentreHead, Brake, Burn, Boost, Roll, Finish, InputCount };
    // time, elapsed wall seconds, position/forward/up/velocity (world XYZ), ground, heat, bank,
    // airspeed, throttle, head yaw/pitch, seat load, main jet, brake panels, last GPU milliseconds.
    using Instruments = std::array<double, 25>;
    std::array<double, InputCount> input{};
    float radioLevel = -1.0f; // open carrier 0..1, idle -1

    void Connect(const std::wstring& name) {
        const std::wstring path = L"\\\\.\\pipe\\" + name;
        pipe = CreateFileW(path.c_str(), GENERIC_READ | GENERIC_WRITE, 0, nullptr, OPEN_EXISTING, 0, nullptr);
        if (pipe == INVALID_HANDLE_VALUE) throw std::runtime_error("Cannot connect to the gameplay controller.");
        DWORD mode = PIPE_READMODE_MESSAGE;
        if (!SetNamedPipeHandleState(pipe, &mode, nullptr, nullptr))
            throw std::runtime_error("The gameplay controller requires a message pipe.");
    }
    ~FlightTake() { if (pipe != INVALID_HANDLE_VALUE) CloseHandle(pipe); }
    bool Connected() const { return pipe != INVALID_HANDLE_VALUE; }

    bool ReadControls(const Instruments& instruments) {
        DWORD count = 0;
        std::array<double, InputCount + 1> packet{};
        if (!WriteFile(pipe, instruments.data(), sizeof(instruments), &count, nullptr) || count != sizeof(instruments)
            || !ReadFile(pipe, packet.data(), sizeof(packet), &count, nullptr)
            || (count != sizeof(input) && count != sizeof(packet)))
            throw std::runtime_error("Gameplay controller disconnected during the take.");
        for (size_t i = 0; i < input.size(); ++i) input[i] = packet[i];
        const double carrier = count == sizeof(packet) ? packet[InputCount] : -1.0;
        if (!std::isfinite(carrier) || (carrier != -1.0 && (carrier < 0 || carrier > 1)))
            throw std::runtime_error("Invalid radio meter.");
        radioLevel = static_cast<float>(carrier);
        for (double value : input) if (!std::isfinite(value))
            throw std::runtime_error("Invalid gameplay control.");
        return input[Finish] == 0.0;
    }

private:
    HANDLE pipe = INVALID_HANDLE_VALUE;
};
