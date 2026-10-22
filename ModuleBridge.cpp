
#include "2_vehicletrafficControl.cpp"
#include "3_emergencyVehicle.cpp"

#include <algorithm>
#include <array>
#include <functional>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace std;
using namespace SmartCity;

namespace {
constexpr int kApproachCount = 4;
constexpr int kMaxVehiclesPerTypePerApproach = 100;

int clampCount(int value) {
    return max(0, min(value, kMaxVehiclesPerTypePerApproach));
}

void refillLane(Lane& lane, int cars, int buses, const string& prefix) {
    // setVehicleCount(0, ...) clears/deletes the old queue in the existing Module 2 API.
    lane.setVehicleCount(0, prefix);
    cars = clampCount(cars);
    buses = clampCount(buses);

    for (int i = 1; i <= cars; ++i) {
        lane.addVehicle(new Car(prefix + "-CAR-" + to_string(i)));
    }
    for (int i = 1; i <= buses; ++i) {
        lane.addVehicle(new Bus(prefix + "-BUS-" + to_string(i)));
    }
}

void callQuietly(const function<void()>& call) {
    // Module 3 prints messages. Capture them so they cannot corrupt the CSV protocol
    // read by Python; send captured diagnostics to stderr instead.
    ostringstream captured;
    streambuf* original = cout.rdbuf(captured.rdbuf());
    try {
        call();
    } catch (...) {
        cout.rdbuf(original);
        throw;
    }
    cout.rdbuf(original);
    if (!captured.str().empty()) {
        cerr << captured.str();
    }
}

void clearLane(Lane& lane) {
    Vehicle* vehicle = nullptr;
    while ((vehicle = lane.removeFrontVehicle()) != nullptr) {
        delete vehicle;
    }
}

} // namespace

int main() {
    // Index order used throughout this bridge: N=0, S=1, E=2, W=3.
    Lane laneN("North"), laneS("South"), laneE("East"), laneW("West");
    array<Lane*, kApproachCount> lanes = {&laneN, &laneS, &laneE, &laneW};

    TrafficSignal signalN, signalS, signalE, signalW;
    array<TrafficSignal*, kApproachCount> signals = {
        &signalN, &signalS, &signalE, &signalW
    };
    const array<string, kApproachCount> prefixes = {"N", "S", "E", "W"};

    EmergencyPriorityController emergencyController;
    array<bool, kApproachCount> servedThisRound = {false, false, false, false};
    int lastServedIndex = -1;
    int activeEmergencyApproach = 0; 
    string line;

    while (getline(cin, line)) {
        if (line.empty())
        continue;

        vector<int> fields;
        string token;
        stringstream input(line);
        while (getline(input, token, ',')) {
            try {
                size_t used = 0;
                int value = stoi(token, &used);
                if (used != token.size()) throw invalid_argument("extra characters");
                fields.push_back(value);
            } catch (...) {
                fields.clear();
                break;
            }
        }

        if (fields.size() != 9) {
            cerr << "Invalid bridge input: expected 9 comma-separated integers; got: " << line << endl;
            cout << "0,3,0,0,0,0,0" << endl;
            cout.flush();
            continue;
        }

        const int nCars = clampCount(fields[0]);
        const int nBuses = clampCount(fields[1]);
        const int sCars = clampCount(fields[2]);
        const int sBuses = clampCount(fields[3]);
        const int eCars = clampCount(fields[4]);
        const int eBuses = clampCount(fields[5]);
        const int wCars = clampCount(fields[6]);
        const int wBuses = clampCount(fields[7]);
        int emergencyApproach = fields[8];
        if (emergencyApproach < 0 || emergencyApproach > kApproachCount) {
            emergencyApproach = 0;
        }

        refillLane(laneN, nCars, nBuses, prefixes[0]);
        refillLane(laneS, sCars, sBuses, prefixes[1]);
        refillLane(laneE, eCars, eBuses, prefixes[2]);
        refillLane(laneW, wCars, wBuses, prefixes[3]);

        array<int, kApproachCount> crossing = {
            laneN.TotalCrossingTime(), laneS.TotalCrossingTime(),
            laneE.TotalCrossingTime(), laneW.TotalCrossingTime()
        };
        array<int, kApproachCount> counts = {
            laneN.getQueueLength(), laneS.getQueueLength(),
            laneE.getQueueLength(), laneW.getQueueLength()
        };

        // If a previously detected emergency is no longer present (Python applies a
        // short visual hold), remove its override before recalculating normal timings.
        if (activeEmergencyApproach != 0 && emergencyApproach != activeEmergencyApproach) {
            const int oldIndex = activeEmergencyApproach - 1;
            callQuietly([&]() { emergencyController.removePriority(*signals[oldIndex]); });
            activeEmergencyApproach = 0;
        }

        // Calculate normal green-time requirements using Module 2
        for (int i = 0; i < kApproachCount; ++i) {
            if (activeEmergencyApproach != i + 1) {
                signals[i]->setGreenTime(crossing[i]);
            }
        }

        int chosenApproach = 0; // zero means all red/no approach selected
        bool isEmergency = emergencyApproach != 0;

        if (isEmergency) {
            chosenApproach = emergencyApproach;
            const int chosenIndex = chosenApproach - 1;
            if (activeEmergencyApproach != emergencyApproach) {
                EmergencyVehicle ambulance("ML-DETECTED-AMBULANCE", "Ambulance");
                callQuietly([&]() {
                    emergencyController.givePriority(*signals[chosenIndex], ambulance);
                });
            }
            activeEmergencyApproach = emergencyApproach;
        } else {
            array<bool, kApproachCount> active = {false, false, false, false};
            bool anyActive = false;
            bool anyUnservedActive = false;
            for (int i = 0; i < kApproachCount; ++i) {
                active[i] = counts[i] > 0;
                anyActive = anyActive || active[i];
                anyUnservedActive = anyUnservedActive || (active[i] && !servedThisRound[i]);
            }

            if (anyActive && !anyUnservedActive) {
                servedThisRound.fill(false);
            }

            int chosenIndex = -1;
            int largestCrossing = -1;
            // A rotating tie-breaker keeps equal-demand approaches fair.
            for (int step = 1; step <= kApproachCount; ++step) {
                const int base = (lastServedIndex < 0) ? (kApproachCount - 1) : lastServedIndex;
                const int i = (base + step) % kApproachCount;
                if (!active[i] || servedThisRound[i]) continue;
                if (crossing[i] > largestCrossing) {
                    largestCrossing = crossing[i];
                    chosenIndex = i;
                }
            }

            if (chosenIndex >= 0) {
                chosenApproach = chosenIndex + 1;
                servedThisRound[chosenIndex] = true;
                lastServedIndex = chosenIndex;
            } else {
                // If no vehicles are detected, continue rotating phases instead of
                // leaving the intersection stuck on all-red indefinitely.
                chosenIndex = (lastServedIndex + 1 + kApproachCount) % kApproachCount;
                chosenApproach = chosenIndex + 1;
                lastServedIndex = chosenIndex;
            }
        }

        // Enforce one green approach at a time in the software state. Python applies
        // the same choice to SUMO after a yellow + all-red clearance interval.
        for (int i = 0; i < kApproachCount; ++i) {
            if (i + 1 != chosenApproach) signals[i]->setRed();
        }
        if (chosenApproach >= 1 && chosenApproach <= kApproachCount) {
            signals[chosenApproach - 1]->setGreen();
        }

        int greenSeconds = 3;
        if (chosenApproach >= 1 && chosenApproach <= kApproachCount) {
            greenSeconds = max(3, signals[chosenApproach - 1]->getGreenTime());
        }

        cout << chosenApproach << ',' << greenSeconds << ',' << (isEmergency ? 1 : 0)
             << ',' << crossing[0] << ',' << crossing[1] << ','
             << crossing[2] << ',' << crossing[3] << endl;
        cout.flush();
    }

    for (Lane* lane : lanes) clearLane(*lane);
    return 0;
}
