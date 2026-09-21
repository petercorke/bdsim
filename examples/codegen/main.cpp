//============================================================
// Hand-written driver for codegen.cpp.
// Diagram: /Users/pic/Library/CloudStorage/Dropbox/code/bdsim/examples/codegen/motor_control2.py
// Edit freely -- unlike codegen.cpp, this file is never regenerated
// automatically. If motor_control2.py's I/O blocks change (a renamed
// block, a different channel, a new DeviceIn/DeviceOut), the bodies
// below need updating to match -- get a signature wrong and it's a
// linker error, not a compile error.
//
// Desktop stand-in only: this builds and runs locally with clang++, not
// on real hardware -- the three I/O bodies below print what they'd do
// instead of touching real pins. See docs/codegen-transpilation.md for
// an Arduino-flavored version of the same three declarations.
//============================================================
#include "codegen.cpp"
#include <cstdio>

// ---- DEVICEIN (encoder) -- stub: fake a slowly drifting count ----
void encoder_output(double t, const Eigen::VectorXd& x, encoder_self& self,
                     const encoder_inports& inports, encoder_outports& outports) {
    outports._0 = 0.0;  // real hardware: read the actual quadrature count here
}

// ---- ANALOGOUT (pwm_magnitude) -- stub: report what would be written ----
void pwm_magnitude_output(double t, const Eigen::VectorXd& x, pwm_magnitude_self& self,
                           const pwm_magnitude_inports& inports, pwm_magnitude_outports& outports) {
    printf("  [stub] pwm_magnitude: analogWrite(channel=%d, value=%d)\n",
           self.channel, inports._0);
}

// ---- DIGITALOUT (motor_direction) -- stub: report what would be written ----
void motor_direction_output(double t, const Eigen::VectorXd& x, motor_direction_self& self,
                             const motor_direction_inports& inports, motor_direction_outports& outports) {
    printf("  [stub] motor_direction: digitalWrite(channel=%d, value=%s)\n",
           self.channel, inports._0 > 0 ? "HIGH" : "LOW");
}

int main() {
    bdsim_init();
    for (double t = 0.0; t < 5.0; t += 0.01) {
        bdsim_tick(t);
        // print every 25th tick (4 Hz) -- at 100 Hz this would otherwise
        // be 500 lines for a 5 s run
        if (static_cast<int>(t * 100) % 25 == 0) {
            printf("t=%.2f demand=%.1f\n", t, demand_outports_inst._0);
        }
    }
    return 0;
}
