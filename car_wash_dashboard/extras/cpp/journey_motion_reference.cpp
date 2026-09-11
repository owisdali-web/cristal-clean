// Crystal Clean V4 - optional reference math for external/native kiosks.
// NOT compiled or loaded by Odoo. The Odoo dashboard uses OWL/JavaScript.
#include <algorithm>
#include <cmath>
#include <iostream>

double smoothstep(double t) {
    t = std::clamp(t, 0.0, 1.0);
    return t * t * (3.0 - 2.0 * t);
}

double interpolateJourney(double fromPct, double toPct, double frame01) {
    return fromPct + (toPct - fromPct) * smoothstep(frame01);
}

int main() {
    for (int i = 0; i <= 10; ++i) {
        double frame = i / 10.0;
        std::cout << interpolateJourney(25.0, 50.0, frame) << "\n";
    }
}
