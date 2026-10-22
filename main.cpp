#include <iostream>
#include <limits>
#include "2_vehicletrafficControl.cpp"
#include "3_emergencyVehicle.cpp"
using namespace std;
using namespace SmartCity;

void showMenu() {
    cout << "\n==================================================" << endl;
    cout << " SMART CITY TRAFFIC MANAGEMENT SYSTEM" << endl;
    cout << "==================================================" << endl;
    cout << "1. Vehicle & Traffic Control module" << endl;
    cout << "2. Emergency Vehicle Priority module" << endl;
    cout << "0. Exit" << endl;
    cout << "Enter choice: ";
}

int main() {
    int choice;

    do {
        showMenu();

        if (!(cin >> choice)) {
            cout << "Invalid input. Please enter 0, 1, or 2." << endl;
            cin.clear();
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            continue;
        }

        cin.ignore(numeric_limits<streamsize>::max(), '\n');

        switch (choice) {
            case 1:
                VehicleTrafficControl();
                break;
            case 2:
                runEmergencyVehiclePriority();
                break;
            case 0:
                cout << "Module 2 and Module 3 demonstration ended." << endl;
                break;
            default:
                cout << "Invalid choice. Select 0, 1, or 2." << endl;
        }
    } while (choice != 0);

    return 0;
}
