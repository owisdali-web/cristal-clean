// Optional companion example. NOT executed by Odoo.
#include <algorithm>
#include <iomanip>
#include <iostream>
#include <string>

struct StationSnapshot {
    std::string name;
    int inProgress{0};
    int queued{0};
    double capacity{1.0};
};

static double utilization(const StationSnapshot& s) {
    const double cap = std::max(1.0, s.capacity);
    return (static_cast<double>(s.inProgress) / cap) * 100.0;
}

static int progressFromSteps(int doneSteps, int totalSteps) {
    if (totalSteps <= 0) return 0;
    return std::clamp(static_cast<int>((100.0 * doneSteps) / totalSteps + 0.5), 0, 100);
}

int main() {
    StationSnapshot station{"A0 - Automatic Wash", 1, 3, 1.0};
    std::cout << station.name << " | utilization=" << std::fixed << std::setprecision(1)
              << utilization(station) << "% | queue=" << station.queued
              << " | progress=" << progressFromSteps(3, 5) << "%\n";
    return 0;
}
