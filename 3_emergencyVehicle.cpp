#ifndef EMERGENCY_VEHICLE_PRIORITY_CPP
#define EMERGENCY_VEHICLE_PRIORITY_CPP

// MODULE 3: Emergency Vehicle Priority

#include <iostream>
#include <string>
#include "2_vehicletrafficControl.cpp"

namespace SmartCity {

using namespace std;

class EmergencyVehicle : public Vehicle {
private:
    string service;

public:
    EmergencyVehicle(string vehicleId, string serviceType)
        : Vehicle(vehicleId, "Emergency Vehicle", true) {
        service = serviceType;
    }

    int crossingTime() override {
        return 1;
    }

    string getService() const {
        return service;
    }

    string getDescription() const {
        return service + " " + id;
    }
};

class EmergencyPriorityController {
public:
    void givePriority(TrafficSignal& signal, EmergencyVehicle& vehicle) {
        cout << "\nEmergency vehicle detected: " << vehicle.getDescription() << endl;
        cout << "Giving priority to emergency vehicle..." << endl;
        cout<<"Estimated crossing time: "<<vehicle.crossingTime()<<"sec";

        signal.enableEmergency(vehicle.crossingTime());
        signal.display();
    }

    void removePriority(TrafficSignal& signal) {
        signal.disableEmergency();
        signal.setRed();

        cout << "Emergency vehicle passed." << endl;
        cout << "Normal signal control resumed." << endl;
        signal.display();
    }
};
void runEmergencyVehiclePriority() {
    cout << "\n========== EMERGENCY VEHICLE PRIORITY ==========" << endl;

    TrafficSignal signal;
    cout<<"Enter the emergency vehicle details: ";
    string name,id;
    cout<<"\n1. Vehicle name \n 2.Vehicle ID";
    cin>>name;
    cin>>id;
    EmergencyVehicle ambulance(id, name);
    EmergencyPriorityController c;

    cout << "\n1. Signal state before emergency arrival:" << endl;
    signal.display();

    cout << "\n2. Emergency vehicle approaches:" << endl;
    cout << "Emergency vehicle: " << ambulance.getDescription() << endl;
    cout << "Crossing time assigned to emergency vehicle: "
         << ambulance.crossingTime() << " sec" << endl;

    c.givePriority(signal, ambulance);

    cout << "\n3. the emergency vehicle passing:" << endl;
    c.removePriority(signal);

}

}
#endif
