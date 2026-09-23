#!/usr/bin/env python3

"""
Cross-check bdsim.codegen's generated C++ against bdsim's own Python
simulation of the same diagram (motor_control.py), and benchmark the
compiled C++ against Python.

Ground truth comes from motor_control.py's SCOPE block (scope.tdata/
scope.ydata) -- reusing bdsim's real, already-tested simulator rather
than hand-rolling a second simulation loop that could have its own bugs.
scope.tdata has duplicate timestamps from the solver handling WAVEFORM's
own declared discontinuity events (confirmed the values at each duplicate
match exactly -- deduplication is safe, just keep the last occurrence).

The C++ side is driven over that exact deduplicated time sequence (not a
separately-constructed one), compiled with -O2 -g (fast, but still
profilable), and its stdout is parsed back for comparison.

Usage: python verify_codegen.py [path-to-eigen-include-dir]
"""

import os
import runpy
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EIGEN_INC = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "/opt/homebrew/Cellar/eigen/5.0.1/include/eigen3"
)

os.environ.setdefault("MPLBACKEND", "Agg")

print("=== Running motor_control.py (Python ground truth + codegen) ===")
ns = runpy.run_path(os.path.join(HERE, "motor_control.py"))
scope = ns["scope"]

# Deduplicate by timestamp, keeping the last occurrence at each t.
t_raw = np.asarray(scope.tdata)
_, last_idx = np.unique(t_raw[::-1], return_index=True)
keep = len(t_raw) - 1 - last_idx
keep.sort()
t_py = t_raw[keep]
demand_py, pid_py, pwm_py, dir_py = (
    np.asarray(scope.ydata[i])[keep] for i in range(4)
)
print(f"{len(t_raw)} raw samples -> {len(t_py)} after deduplication")

print("\n=== Generating C++ driver over the identical time sequence ===")
t_list = ", ".join(repr(float(v)) for v in t_py)
# Capture values into plain arrays during the timed loop, then print
# afterwards -- keeps I/O (which has no embedded-target equivalent, and
# would otherwise dominate the measurement) out of the timed region, so
# the reported time reflects pure tick-computation cost.
driver_src = f"""#include "codegen.cpp"
#include <cstdio>
#include <chrono>

static const double kTimes[] = {{{t_list}}};
static const int kN = {len(t_py)};
static double demand_log[kN], pid_log[kN], pwm_log[kN], dir_log[kN];

int main() {{
    bdsim_init(0);  // desktop cross-check drives bdsim_tick_clock0() directly
                    // with each simulation timestamp -- never touches
                    // bdsim_clocks[]/millis()-based polling, so the actual
                    // now_ms value here doesn't matter
    auto start = std::chrono::steady_clock::now();
    for (int i = 0; i < kN; i++) {{
        bdsim_tick_clock0(kTimes[i]);
        demand_log[i] = demand_outports_inst._0;
        pid_log[i] = pid_outport_0_outports_inst._0;
        pwm_log[i] = motor_out_outports_inst._0;
        dir_log[i] = motor_out_outports_inst._1;
    }}
    auto end = std::chrono::steady_clock::now();
    double us = std::chrono::duration<double, std::micro>(end - start).count();
    fprintf(stderr, "TICK_LOOP_US=%.3f\\n", us);
    for (int i = 0; i < kN; i++) {{
        printf("%.10g,%.10g,%.10g,%.10g,%.10g\\n", kTimes[i],
               demand_log[i], pid_log[i], pwm_log[i], dir_log[i]);
    }}
    return 0;
}}
"""
driver_path = os.path.join(HERE, "verify_driver.cpp")
with open(driver_path, "w") as f:
    f.write(driver_src)

print("=== Compiling (-O2 -g) ===")
binary_path = os.path.join(HERE, "verify_driver")
subprocess.run(
    [
        "clang++",
        "-O2",
        "-g",
        "-std=c++17",
        f"-I{EIGEN_INC}",
        driver_path,
        "-o",
        binary_path,
    ],
    check=True,
    cwd=HERE,
)

print("=== Running compiled C++ ===")
result = subprocess.run([binary_path], capture_output=True, text=True, check=True)

cpp_us = None
for line in result.stderr.splitlines():
    if line.startswith("TICK_LOOP_US="):
        cpp_us = float(line.split("=", 1)[1])
if cpp_us is None:
    raise RuntimeError(f"didn't find TICK_LOOP_US in stderr:\n{result.stderr}")

rows = [line.split(",") for line in result.stdout.strip().split("\n")]
cpp_data = np.array(rows, dtype=float)
t_cpp, demand_cpp, pid_cpp, pwm_cpp, dir_cpp = cpp_data.T

print(f"{len(t_cpp)} ticks, pure compute time {cpp_us / 1000:.3f} ms "
      f"(excludes process startup and I/O -- see below for those separately)")

print("\n=== Numerical comparison (Python ground truth vs. compiled C++) ===")
print("(port types are float in C++ vs double in Python -- expect ~float32")
print(" precision-level differences, not exact equality)")


def compare(name, py_vals, cpp_vals):
    diff = np.abs(np.asarray(py_vals) - cpp_vals)
    print(f"  {name:10s} max_err={diff.max():.3e}  mean_err={diff.mean():.3e}")
    return diff.max()


max_errs = [
    compare("demand", demand_py, demand_cpp),
    compare("pid", pid_py, pid_cpp),
    compare("pwm", pwm_py, pwm_cpp),
    compare("direction", dir_py, dir_cpp),
]

# float32-appropriate tolerance: float32 epsilon (~1.19e-7) times signal
# magnitude, plus a small absolute floor for near-zero signals.
scale = max(np.abs(demand_py).max(), np.abs(pid_py).max(), np.abs(pwm_py).max())
tol = 1e-3 + 50 * np.finfo(np.float32).eps * scale
ok = all(e < tol for e in max_errs)
print(f"\n{'PASS' if ok else 'FAIL'}: max error {max(max_errs):.3e} (tolerance {tol:.3e})")

print("\n=== Benchmark: Python vs. compiled C++ for the same tick sequence ===")
print("(pure evaluate()+next() stepping, bypassing sim.run()'s graphics/event overhead)")

bd = ns["bd"]
state_map = bd.initial_state_map()
t0 = time.perf_counter()
for t in t_py:
    bd.evaluate(state_map, float(t), sinks=False)
    clock_next = bd.next(float(t), state_map)
    for clock, xnext in clock_next.items():
        offset = 0
        for blk in clock.blocklist:
            n = blk.ndstates
            if blk in state_map:
                state_map[blk] = xnext[offset : offset + n]
            offset += n
py_elapsed = time.perf_counter() - t0
py_us = py_elapsed * 1e6

print(f"Python: {len(t_py)} ticks in {py_us / 1000:.3f} ms  ({py_us / len(t_py):.2f} us/tick)")
print(f"C++:    {len(t_cpp)} ticks in {cpp_us / 1000:.3f} ms  ({cpp_us / len(t_cpp):.2f} us/tick)")
print(f"Speedup: {py_us / cpp_us:.1f}x (pure compute, both exclude I/O and process startup)")
