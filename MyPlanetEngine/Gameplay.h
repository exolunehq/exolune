// Gameplay.h - Pure C++ state for player-triggered and mission-scripted gameplay phases.
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <string>

struct Gameplay {
    enum class SequenceId : uint32_t { ShuttleBoarding = 0, Count };
    enum class SequencePhase : uint8_t { Dormant = 0, Armed, Running, Completed };

    struct SequenceState {
        SequencePhase phase = SequencePhase::Dormant;
        double clock = 0.0;
        uint32_t done = 0, total = 0;
        bool completionNotified = false;
    };

    std::array<SequenceState, size_t(SequenceId::Count)> sequences{};

    static bool ParseSequence(const std::wstring& token, SequenceId& out) {
        if (token == L"shuttle_boarding" || token == L"embarquement") {
            out = SequenceId::ShuttleBoarding;
            return true;
        }
        return false;
    }

    static const wchar_t* SequenceTitle(SequenceId id) {
        switch (id) {
        case SequenceId::ShuttleBoarding: return L"Embarquement navette";
        default: return L"";
        }
    }

    const SequenceState& State(SequenceId id) const {
        return sequences[size_t(id)];
    }

    bool Active(SequenceId id) const {
        return State(id).phase != SequencePhase::Dormant;
    }

    void Trigger(SequenceId id, bool restart = true) {
        SequenceState& s = sequences[size_t(id)];
        s.phase = SequencePhase::Armed;
        if (restart) {
            s.clock = 0.0;
            s.done = 0;
            s.completionNotified = false;
        }
    }

    void Stop(SequenceId id) {
        sequences[size_t(id)] = {};
    }

    void Advance(SequenceId id, double dt, bool preconditionsMet) {
        SequenceState& s = sequences[size_t(id)];
        if (s.phase == SequencePhase::Armed && preconditionsMet)
            s.phase = SequencePhase::Running;
        if (s.phase == SequencePhase::Running && preconditionsMet)
            s.clock += std::max(0.0, dt);
    }

    bool SyncProgress(SequenceId id, uint32_t done, uint32_t total) {
        SequenceState& s = sequences[size_t(id)];
        s.done = done;
        s.total = total;
        if (s.phase == SequencePhase::Running && total > 0 && done >= total) {
            s.phase = SequencePhase::Completed;
            if (!s.completionNotified) {
                s.completionNotified = true;
                return true;
            }
        }
        return false;
    }
};
