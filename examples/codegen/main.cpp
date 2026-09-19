// Quick standalone driver for codegen.cpp -- not part of the build, just
// for poking at generated output by hand. #include's codegen.cpp directly
// since it isn't split into a .h/.cpp pair yet (single translation unit).
#include "codegen.cpp"
#include <cstdio>

int main() {
    bdsim_init();
    for (double t = 0.0; t < 5.0; t += 0.01) {
        bdsim_tick(t);
        printf("t=%.2f demand=%.1f pwm=%.1f dir=%.1f\n", t,
               demand_outports_inst._0, motor_out_outports_inst._0,
               motor_out_outports_inst._1);
    }
    return 0;
}
