#ifndef VEHICLE_TRAFFIC_CONTROL_CPP
#define VEHICLE_TRAFFIC_CONTROL_CPP

#include <iostream>
#include <queue>
#include <string>
#include <vector>

namespace SmartCity {

using namespace std;

enum SignalColor { RED, GREEN };

class Vehicle {
protected:
    string id;
    string type;
    bool emergency;

public:
    Vehicle(string vehicleId, string vehicleType, bool isEmergency = false) {
        id = vehicleId;
        type = vehicleType;
        emergency = isEmergency;
    }

    virtual ~Vehicle() {}

    virtual int crossingTime() = 0;

    string getId() const { return id; }
    string getType() const { return type; }
    bool isEmergencyVehicle() const { return emergency; }
};

class Car : public Vehicle {
public:
    Car(string vehicleId) : Vehicle(vehicleId, "Car") {}

    int crossingTime() override {
        return 2;
    }
};

class Bus : public Vehicle {
public:
    Bus(string vehicleId) : Vehicle(vehicleId, "Bus") {}

    int crossingTime() override {
        return 4;
    }
};

class Lane {
private:
    string laneId;
    queue<Vehicle*> vehicles;

public:
    Lane(string id) {
        laneId = id;
    }

    void addVehicle(Vehicle* vehicle) {
        vehicles.push(vehicle);
    }

    void setVehicleCount(int count, string prefix) {
        while (!vehicles.empty()) {
            delete vehicles.front();
            vehicles.pop();
        }

        for (int i = 1; i <= count; i++) {
            addVehicle(new Car(prefix + "-V" + to_string(i)));
        }
    }

    int getQueueLength() const {
        return (int)vehicles.size();
    }
    int TotalCrossingTime(){
        int total=0;
        queue<Vehicle*> temp=vehicles;
        while(!temp.empty()){
            Vehicle* vehicle=temp.front();
            if(vehicle !=nullptr)
            {
                total=total+vehicle->crossingTime();
            }
            temp.pop();
        }
        return total;
    }

    Vehicle* removeFrontVehicle() {
        if (vehicles.empty()) {
            return nullptr;
        }

        Vehicle* vehicle = vehicles.front();
        vehicles.pop();
        return vehicle;
    }

    string getLaneId() {
        return laneId;
    }
};

class TrafficSignal {
private:
    SignalColor color;
    int greenTime;
    bool emergencyOverride;

public:
    TrafficSignal() {
        color = RED;
        greenTime = 30;
        emergencyOverride = false;
    }

    void setGreen() {
        color = GREEN;
    }

    void setRed() {
        color = RED;
    }

    void setGreenTime(int total) {
         if (total < 0) {
            total = 0;
        }

        greenTime = 10 + total;

        if (greenTime > 60) {
            greenTime = 60;
        }
    }

    void enableEmergency(int time) {
        emergencyOverride = true;
        color = GREEN;
         if (time < 0) {
            time = 0;
        }

        greenTime = 10 + time;

        if (greenTime > 60) {
            greenTime = 60;
        }
    }

    void disableEmergency() {
        emergencyOverride = false;
    }

    bool isGreen() {
        return color == GREEN;
    }

    bool isEmergencyActive(){
        return emergencyOverride;
    }

    int getGreenTime(){
        return greenTime;
    }

    void display(){
        cout << "Signal: " << (color == GREEN ? "GREEN" : "RED");
        cout << " | Green Time: " << greenTime << " sec";

        if (emergencyOverride) {
            cout << " | EMERGENCY OVERRIDE";
        }

        cout << endl;
    }
};

    void VehicleTrafficControl() {
    cout << "\n=============VEHICLE & TRAFFIC CONTROL =========="<< endl;
    cout<<"Enter lane id";
    string lid;
    getline(cin,lid);
    Lane lane(lid);
    cout << "\n1. Adding vehicles to the lane queue:" << endl;

    lane.addVehicle(new Car("CAR-101"));
    lane.addVehicle(new Bus("BUS-201"));
    lane.addVehicle(new Car("CAR-102"));

    cout << "Lane: " << lane.getLaneId() << endl;
    cout << "Vehicles waiting: "
         << lane.getQueueLength() << endl;

    cout << "\n2. Calculating individual crossing times:"
         << endl;

    int totalCrossingTime = lane.TotalCrossingTime();

    cout << "Total vehicle crossing time: "
         << totalCrossingTime << " seconds" << endl;

    cout << "\n3. Dynamic traffic signal control:" << endl;

    const int baseClearanceTime = 10;

    TrafficSignal signal;

    signal.setGreenTime(totalCrossingTime);

    signal.setGreen();

    cout << "Base/clearance allowance: "
         << baseClearanceTime << " seconds" << endl;

    cout << "Total vehicle crossing time: "
         << totalCrossingTime << " seconds" << endl;

    cout << "Green-time calculation: "
         << baseClearanceTime << " + "
         << totalCrossingTime << " = "
         << signal.getGreenTime() << " seconds"
         << endl;

    cout << "Updated signal: ";
    signal.display();

    cout << "\n4. Removing vehicles in FIFO order:" << endl;

    Vehicle* vehicle = nullptr;

    while ((vehicle = lane.removeFrontVehicle()) != nullptr) {
        cout << "Vehicle ID: " << vehicle->getId()
             << " | Type: " << vehicle->getType()
             << " | Crossing time: "
             << vehicle->crossingTime()
             << " seconds" << endl;

        delete vehicle;
    }

    cout << "\nVehicles remaining: "
         << lane.getQueueLength() << endl;

    cout << "\nModule 2 test completed successfully."
         << endl;
}
};

#endif
