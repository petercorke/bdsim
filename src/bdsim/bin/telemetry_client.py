#!/usr/bin/env python3
"""Simple Tkinter strip-chart client for bdsim TELEMETRY UDP packets.

Usage:
    bdsim-telemetry-client --listen 0.0.0.0:5001
"""

from __future__ import annotations

import argparse
import json
import math
import queue
import socket
import threading
import time
from collections import deque
from typing import Any

import tkinter as tk


class StripChartApp:
    COLORS = [
        "#1f77b4",
        "#d62728",
        "#2ca02c",
        "#ff7f0e",
        "#17becf",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
    ]

    def __init__(
        self,
        host: str,
        port: int,
        history_sec: float,
        refresh_ms: int,
        width: int,
        height: int,
        require_schema: bool,
        grid_dx_sec: float,
        grid_dy_val: float,
    ) -> None:
        self.host = host
        self.port = port
        self.history_sec = history_sec
        self.refresh_ms = refresh_ms
        self.require_schema = require_schema
        self.grid_dx_sec = max(1e-9, float(grid_dx_sec))
        self.grid_dy_val = max(1e-9, float(grid_dy_val))

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.sock.settimeout(1.0)  # blocking with timeout for recv thread

        # Background thread stamps arrival time immediately and enqueues raw bytes.
        self._recv_queue: queue.Queue[tuple[int, bytes]] = queue.Queue()
        self._recv_thread = threading.Thread(
            target=self._recv_loop, daemon=True, name="udp-recv"
        )
        self._recv_thread.start()

        self.root = tk.Tk()
        self.root.title(f"bdsim TELEMETRY client {host}:{port}")

        self.canvas = tk.Canvas(self.root, width=width, height=height, bg="#111111")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.status = tk.StringVar(value="waiting for telemetry...")
        self.status_label = tk.Label(
            self.root,
            textvariable=self.status,
            anchor="w",
            bg="#202020",
            fg="#f0f0f0",
            padx=8,
            pady=4,
        )
        self.status_label.pack(fill=tk.X)

        self.signal_names_by_index: dict[int, str] = {}
        self.have_schema = False
        self.series: dict[str, deque[tuple[float, float]]] = {}
        self.last_recv_wall = 0.0
        self.last_recv_sim_t = 0.0
        self.last_recv_seq: int | None = None
        self.dropped_samples_no_schema = 0
        self.last_sender_mono_ns: int | None = None
        self.last_arrival_mono_ns: int | None = None
        self.link_jitter_n: int = 0
        self.link_jitter_sum_ns: float = 0.0
        self.link_jitter_sum_sq_ns2: float = 0.0
        self.link_jitter_abs_max_ns: float = 0.0

        self.root.after(self.refresh_ms, self._tick)

    def _reset_series(self) -> None:
        self.series.clear()
        self.last_recv_sim_t = 0.0
        self.last_recv_seq = None
        self.last_sender_mono_ns = None
        self.last_arrival_mono_ns = None

    def _focus_on_stream_start(self) -> None:
        # Raise/focus the scope when packets resume after an idle gap.
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.focus_force()
            self.root.after(150, lambda: self.root.attributes("-topmost", False))
        except Exception:
            pass

    def _decode_sample_value(self, base_name: str, value: Any) -> dict[str, float]:
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return {base_name: float(value)}

        if isinstance(value, dict) and value.get("kind") == "ndarray":
            shape = value.get("shape", [])
            data = value.get("data", [])
            if not isinstance(shape, list) or not isinstance(data, list):
                return {}

            out: dict[str, float] = {}
            for i, entry in enumerate(data):
                try:
                    v = float(entry)
                except Exception:
                    continue
                if not math.isfinite(v):
                    continue
                if len(shape) == 1:
                    name = f"{base_name}[{i}]"
                else:
                    name = f"{base_name}[{i}]"
                out[name] = v
            return out

        try:
            v = float(value)
        except Exception:
            return {}
        if not math.isfinite(v):
            return {}
        return {base_name: v}

    def _ingest_packet(
        self, payload: dict[str, Any], arrival_mono_ns: int | None = None
    ) -> None:
        ptype = payload.get("type")
        if ptype == "schema":
            signals = payload.get("signals", [])
            self.signal_names_by_index = {}
            if isinstance(signals, list):
                for entry in signals:
                    if not isinstance(entry, dict):
                        continue
                    idx = entry.get("index")
                    name = entry.get("name")
                    if isinstance(idx, int) and isinstance(name, str):
                        self.signal_names_by_index[idx] = name
            self.have_schema = True
            return

        if ptype != "sample":
            return

        if self.require_schema and not self.have_schema:
            self.dropped_samples_no_schema += 1
            return

        sim_t = float(payload.get("t", 0.0))
        seq_raw = payload.get("seq")
        seq = seq_raw if isinstance(seq_raw, int) else None
        sender_mono_raw = payload.get("sender_mono_ns")
        sender_mono_ns = sender_mono_raw if isinstance(sender_mono_raw, int) else None
        if arrival_mono_ns is None:
            arrival_mono_ns = (
                time.monotonic_ns()
            )  # fallback if not stamped by recv thread

        # New run/stream restart (eg producer restarted from t~=0): clear old
        # points so we don't draw a diagonal retrace from old tail to new head.
        if self.last_recv_wall:
            backwards = self.last_recv_sim_t - sim_t
            if backwards > max(1.0, 0.1 * self.history_sec):
                self._reset_series()

        values = payload.get("values", [])
        if not isinstance(values, list):
            return

        for i, raw in enumerate(values):
            base_name = self.signal_names_by_index.get(i, f"u{i}")
            decoded = self._decode_sample_value(base_name, raw)
            for name, v in decoded.items():
                if name not in self.series:
                    self.series[name] = deque()
                self.series[name].append((sim_t, v))

        self.last_recv_wall = time.time()
        self.last_recv_sim_t = sim_t
        self.last_recv_seq = seq

        # Sync-free link jitter estimate: compare sender inter-packet delta to
        # receiver arrival inter-packet delta. Absolute offset is irrelevant.
        if sender_mono_ns is not None:
            if (
                self.last_sender_mono_ns is not None
                and self.last_arrival_mono_ns is not None
            ):
                sender_dt = sender_mono_ns - self.last_sender_mono_ns
                arrival_dt = arrival_mono_ns - self.last_arrival_mono_ns
                if sender_dt > 0 and arrival_dt > 0:
                    delta_err_ns = float(arrival_dt - sender_dt)
                    self.link_jitter_n += 1
                    self.link_jitter_sum_ns += delta_err_ns
                    self.link_jitter_sum_sq_ns2 += delta_err_ns * delta_err_ns
                    self.link_jitter_abs_max_ns = max(
                        self.link_jitter_abs_max_ns, abs(delta_err_ns)
                    )
            self.last_sender_mono_ns = sender_mono_ns
            self.last_arrival_mono_ns = arrival_mono_ns

        # Keep only the requested trailing history in simulation time.
        t_min = sim_t - self.history_sec
        for q in self.series.values():
            while q and q[0][0] < t_min:
                q.popleft()

    def _recv_loop(self) -> None:
        """Background thread: recv immediately, stamp arrival time, enqueue."""
        while True:
            try:
                data, _addr = self.sock.recvfrom(65535)
                arrival_ns = time.monotonic_ns()
                self._recv_queue.put_nowait((arrival_ns, data))
            except TimeoutError:
                continue  # keepalive; check daemon exit via thread.daemon
            except OSError:
                break  # socket closed on shutdown

    def _drain_socket(self) -> int:
        count = 0
        while True:
            try:
                arrival_ns, data = self._recv_queue.get_nowait()
            except queue.Empty:
                break

            try:
                payload = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            if isinstance(payload, dict):
                self._ingest_packet(payload, arrival_ns)
                count += 1
        return count

    def _draw(self) -> None:
        self.canvas.delete("all")

        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        pad = 35

        self.canvas.create_rectangle(pad, 10, w - 10, h - pad, outline="#555555")

        if not self.series:
            self.canvas.create_text(
                w / 2,
                h / 2,
                text="No samples yet",
                fill="#bbbbbb",
                font=("Helvetica", 14),
            )
            return

        all_pts = [v for q in self.series.values() for _, v in q]
        if not all_pts:
            return

        y_min = min(all_pts)
        y_max = max(all_pts)
        if y_min == y_max:
            y_min -= 1.0
            y_max += 1.0
        span = y_max - y_min
        y_min -= 0.1 * span
        y_max += 0.1 * span

        t_now = self.last_recv_sim_t
        t_min = t_now - self.history_sec

        def x_of(t: float) -> float:
            if self.history_sec <= 1e-9:
                return float(pad)
            return pad + (t - t_min) / self.history_sec * (w - pad - 10)

        def y_of(v: float) -> float:
            return 10 + (y_max - v) / (y_max - y_min) * (h - pad - 10)

        # Draw major grid (50% gray): vertical every grid_dx_sec, horizontal
        # every grid_dy_val in signal units.
        gx = self.grid_dx_sec
        gy = self.grid_dy_val

        # Keep vertical grid lines fixed on screen (scope-style graticule)
        # while traces scroll left as time advances.
        x_span_px = float(w - pad - 10)
        if self.history_sec > 1e-9:
            x_step_px = gx / self.history_sec * x_span_px
            if x_step_px >= 1.0:
                x = w - 10
                while x >= pad:
                    self.canvas.create_line(
                        x, 10, x, h - pad, fill="#808080", width=1, tags=("grid",)
                    )
                    x -= x_step_px

        y_tick = math.floor(y_min / gy) * gy
        while y_tick <= y_max:
            y = y_of(y_tick)
            if 10 <= y <= (h - pad):
                self.canvas.create_line(
                    pad, y, w - 10, y, fill="#808080", width=1, tags=("grid",)
                )
            y_tick += gy

        self.canvas.create_text(
            6,
            12,
            text=f"{y_max:.3g}",
            fill="#bbbbbb",
            anchor="w",
            font=("Helvetica", 9),
        )
        self.canvas.create_text(
            6,
            h - pad,
            text=f"{y_min:.3g}",
            fill="#bbbbbb",
            anchor="w",
            font=("Helvetica", 9),
        )

        names = sorted(self.series.keys())
        for idx, name in enumerate(names):
            color = self.COLORS[idx % len(self.COLORS)]
            q = self.series[name]
            if len(q) < 2:
                continue
            pts: list[float] = []
            for t, v in q:
                pts.extend([x_of(t), y_of(v)])
            self.canvas.create_line(*pts, fill=color, width=2, tags=("trace",))

        self.canvas.tag_lower("grid", "trace")

        x_legend = pad + 5
        y_legend = h - pad + 6
        for idx, name in enumerate(names[:8]):
            color = self.COLORS[idx % len(self.COLORS)]
            self.canvas.create_text(
                x_legend,
                y_legend,
                text=name,
                fill=color,
                anchor="w",
                font=("Helvetica", 9, "bold"),
            )
            x_legend += 120

    def _tick(self) -> None:
        was_streaming = bool(
            self.last_recv_wall and (time.time() - self.last_recv_wall) < 1.0
        )
        n = self._drain_socket()
        if n > 0 and not was_streaming:
            self._focus_on_stream_start()

        age = time.time() - self.last_recv_wall if self.last_recv_wall else None
        if self.require_schema and not self.have_schema:
            self.status.set(
                f"listening on {self.host}:{self.port} | waiting for schema | "
                f"dropped_samples={self.dropped_samples_no_schema}"
            )
        elif age is None:
            self.status.set(f"listening on {self.host}:{self.port} | waiting...")
        else:
            if self.link_jitter_n > 0:
                jitter_mean_ns = self.link_jitter_sum_ns / self.link_jitter_n
                jitter_var_ns2 = max(
                    0.0,
                    (self.link_jitter_sum_sq_ns2 / self.link_jitter_n)
                    - (jitter_mean_ns * jitter_mean_ns),
                )
                jitter_std_ns = math.sqrt(jitter_var_ns2)
                jitter_text = (
                    f" | dt_err_mean={jitter_mean_ns / 1e6:.2f}ms"
                    f" std={jitter_std_ns / 1e6:.2f}ms"
                    f" maxabs={self.link_jitter_abs_max_ns / 1e6:.2f}ms"
                )
            else:
                jitter_text = ""
            self.status.set(
                f"listening on {self.host}:{self.port} | samples={n} | "
                f"signals={len(self.series)} | last_t={self.last_recv_sim_t:.3f}s | "
                f"age={age:.2f}s"
                f"{jitter_text}"
            )

        self._draw()
        self.root.after(self.refresh_ms, self._tick)

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    def parse_endpoint(text: str) -> tuple[str, int]:
        host, sep, port_text = text.strip().rpartition(":")
        if not sep or not host or not port_text.isdigit():
            raise argparse.ArgumentTypeError(
                "endpoint must be 'host:port' (eg 0.0.0.0:5001)"
            )
        port = int(port_text)
        if not (0 <= port <= 65535):
            raise argparse.ArgumentTypeError("endpoint port must be in 0..65535")
        return host, port

    def parse_grid(text: str) -> tuple[float, float]:
        left, sep, right = text.strip().partition(",")
        if not sep:
            raise argparse.ArgumentTypeError("grid must be 'dx,dy' (eg 0.5,0.1)")
        try:
            dx = float(left)
            dy = float(right)
        except ValueError as err:
            raise argparse.ArgumentTypeError("grid values must be numeric") from err
        if dx <= 0 or dy <= 0:
            raise argparse.ArgumentTypeError("grid values must be > 0")
        return dx, dy

    parser = argparse.ArgumentParser(
        description="Tkinter strip-chart listener for bdsim TELEMETRY UDP packets",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--listen",
        "--endpoint",
        type=parse_endpoint,
        default=("0.0.0.0", 5001),
        metavar="host:port",
        help="UDP bind endpoint for this client (interface address + port)",
    )
    parser.add_argument(
        "--history",
        type=float,
        default=10.0,
        help="time window shown in the strip chart (seconds)",
    )
    parser.add_argument(
        "--refresh-ms",
        "--refresh",
        dest="refresh_ms",
        type=int,
        default=33,
        help="UI redraw period in milliseconds",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1100,
        help="initial window width in pixels",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=500,
        help="initial window height in pixels",
    )
    parser.add_argument(
        "--grid",
        type=parse_grid,
        default=(0.5, 0.1),
        metavar="dx,dy",
        help=(
            "grid spacing: dx seconds for vertical graticule lines, "
            "dy signal units for horizontal lines"
        ),
    )
    parser.add_argument(
        "--allow-unnamed",
        action="store_true",
        help="plot samples before schema arrives using fallback names (u0, u1, ...)",
    )
    args = parser.parse_args()
    host, port = args.listen

    app = StripChartApp(
        host=host,
        port=port,
        history_sec=args.history,
        refresh_ms=args.refresh_ms,
        width=args.width,
        height=args.height,
        require_schema=not args.allow_unnamed,
        grid_dx_sec=args.grid[0],
        grid_dy_val=args.grid[1],
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
