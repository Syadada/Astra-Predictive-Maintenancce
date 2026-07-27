"""
demo_streaming.py — Real-time prediction demo for Kerry Group presentation.

Shows Sir Ronny's two options side by side:

  Option 1 (Batch):   Collect 60 readings → compute stats → predict ONCE
  Option 2 (Sliding): Every new reading slides the window → predict every 5 s

Run from ml/ directory:
    python -X utf8 src/evaluation/demo_streaming.py

The script simulates a pump gradually degrading from NORMAL → WARNING → CRITICAL,
producing the "normal-normal-not normal" output pattern Sir Ronny described.
"""

import os
import sys
import time
import random
import numpy as np

# Resolve D:\Kerry\ml so that `from src.api...` works when script is run
# from any directory (ml/ or Kerry/).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))         # .../ml/src/evaluation
_ML_DIR   = os.path.dirname(os.path.dirname(_THIS_DIR))        # .../ml
sys.path.insert(0, _ML_DIR)

from src.api.stream_buffer import StreamBuffer

# ─── Terminal colours ────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

RISK_COLOUR = {"normal": GREEN, "minimal": GREEN, "elevated": YELLOW, "critical": RED}
RISK_SYMBOL = {"normal": "●", "minimal": "●", "elevated": "▲", "critical": "✖"}


def _colour(risk: str, text: str) -> str:
    c = RISK_COLOUR.get(risk, RESET)
    return f"{c}{text}{RESET}"


# ─── Simulated sensor stream ─────────────────────────────────────────────────

def _generate_reading(phase: str, t: int) -> dict:
    """
    Simulate sensor readings at three degradation phases.

    Phase         Vibration (g)   Current (A)   Temperature (°C)  Flow (L/min)
    ──────────    ─────────────   ───────────   ────────────────  ────────────
    normal        0.20 ± 0.02     1.5 ± 0.1     85 ± 1.5          120 ± 2
    degrading     0.35 ± 0.05     2.2 ± 0.2     95 ± 2.0          112 ± 3
    critical      0.55 ± 0.06     3.6 ± 0.3     108 ± 3.0         103 ± 4
    """
    rng = random.Random(t * 7919)  # deterministic but varied per timestep
    if phase == "normal":
        return {
            "vibration_rms": rng.gauss(0.20, 0.02),
            "motor_current": rng.gauss(1.5,  0.10),
            "temperature":   rng.gauss(85.0, 1.50),
            "flow_rate":     rng.gauss(120.0, 2.0),
        }
    elif phase == "degrading":
        return {
            "vibration_rms": rng.gauss(0.35, 0.05),
            "motor_current": rng.gauss(2.2,  0.20),
            "temperature":   rng.gauss(95.0, 2.0),
            "flow_rate":     rng.gauss(112.0, 3.0),
        }
    else:  # critical
        return {
            "vibration_rms": rng.gauss(0.55, 0.06),
            "motor_current": rng.gauss(3.6,  0.30),
            "temperature":   rng.gauss(108.0, 3.0),
            "flow_rate":     rng.gauss(103.0, 4.0),
        }


def _simple_predict(vib: float, cur: float, tmp: float, flw: float) -> dict:
    """
    Lightweight rule-based classifier for demo purposes
    (doesn't need the ML models to be loaded).

    In production, this is replaced by Predictor.infer_from_sliders().
    """
    # Compute weighted anomaly score
    vib_score = min(1.0, max(0.0, (vib - 0.18) / 0.42))   # 0 at 0.18 g, 1 at 0.60 g
    cur_score = min(1.0, max(0.0, (cur - 0.85) / 3.15))    # 0 at 0.85 A, 1 at 4.00 A
    tmp_score = min(1.0, max(0.0, (tmp - 75.0) / 35.0))    # 0 at 75°C, 1 at 110°C
    flw_score = min(1.0, max(0.0, (120.0 - flw) / 20.0))   # 0 at 120, 1 at 100 L/min

    score = 0.40 * vib_score + 0.25 * cur_score + 0.20 * tmp_score + 0.15 * flw_score

    if score < 0.25:
        risk = "normal"
        fault = "Normal — no fault"
        rul_h = 2000
    elif score < 0.55:
        risk = "elevated"
        fault = "Ball element wear (early)"
        rul_h = 500
    else:
        risk = "critical"
        fault = "Inner race fault (severe)"
        rul_h = 80

    # SHAP-like dominant sensor (which sensor contributed most?)
    impacts = {
        "Vibration": round(vib_score * 0.40, 3),
        "Current":   round(cur_score * 0.25, 3),
        "Temp":      round(tmp_score * 0.20, 3),
        "Flow":      round(flw_score * 0.15, 3),
    }
    dominant = max(impacts, key=impacts.get)

    return {
        "anomaly_score": round(score, 3),
        "risk_level":    risk,
        "fault_class":   fault,
        "rul_hours":     rul_h,
        "dominant_sensor": dominant,
        "sensor_impacts":  impacts,
    }


# ─── Option 1: Batch ─────────────────────────────────────────────────────────

def demo_option1_batch():
    print(f"\n{BOLD}{CYAN}══════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{CYAN}  OPTION 1 — BATCH (collect all → predict once)       {RESET}")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════{RESET}")
    print("  Scenario: pump runs normally for 60 s, then data is sent in one batch.\n")

    readings = []
    for t in range(60):
        readings.append(_generate_reading("normal", t))

    # Aggregate (Sir Ronny's avg / max / min)
    vibs = [r["vibration_rms"] for r in readings]
    curs = [r["motor_current"]  for r in readings]
    tmps = [r["temperature"]    for r in readings]
    flws = [r["flow_rate"]      for r in readings]

    print(f"  Collected {len(readings)} readings (1 Hz × 60 s)")
    print(f"\n  {BOLD}Aggregation over 60-second window:{RESET}")
    print(f"  {'Sensor':<18} {'avg':>8} {'max':>8} {'min':>8}")
    print(f"  {'──────':<18} {'───':>8} {'───':>8} {'───':>8}")

    def fmt_row(name, arr):
        return f"  {name:<18} {np.mean(arr):>8.3f} {np.max(arr):>8.3f} {np.min(arr):>8.3f}"

    print(fmt_row("Vibration (g)",   vibs))
    print(fmt_row("Current (A)",     curs))
    print(fmt_row("Temperature (°C)", tmps))
    print(fmt_row("Flow (L/min)",    flws))

    # One prediction on the aggregate
    result = _simple_predict(
        float(np.sqrt(np.mean(np.array(vibs) ** 2))),  # true RMS
        float(np.mean(curs)),
        float(np.mean(tmps)),
        float(np.mean(flws)),
    )
    print(f"\n  {BOLD}Single prediction on batch aggregate:{RESET}")
    print(f"  Risk level    : {_colour(result['risk_level'], result['risk_level'].upper())}")
    print(f"  Anomaly score : {result['anomaly_score']:.3f}")
    print(f"  Fault class   : {result['fault_class']}")
    print(f"  Est. RUL      : {result['rul_hours']} hours")
    print(f"\n  {YELLOW}⚠  Drawback: if degradation started at second 55, batch misses it.{RESET}")
    print(f"     Early warning can be {BOLD}60 seconds late{RESET} in worst case.\n")


# ─── Option 2: Sliding Window ─────────────────────────────────────────────────

def demo_option2_sliding():
    print(f"\n{BOLD}{CYAN}══════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{CYAN}  OPTION 2 — SLIDING WINDOW (test one by one)         {RESET}")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════{RESET}")
    print("  Scenario: pump degrades gradually over 120 seconds.\n")
    print(f"  {'t(s)':<6} {'Phase':<12} {'Vib(g)':<10} {'Cur(A)':<10} "
          f"{'Tmp(°C)':<10} {'Flw(L)':<10} {'Risk':<12} {'RUL(h)':<8} {'Dominant'}")
    print(f"  {'────':<6} {'─────':<12} {'──────':<10} {'──────':<10} "
          f"{'───────':<10} {'──────':<10} {'────':<12} {'──────':<8} {'────────'}")

    def _run_machine(machine_id: str, name: str, stride: int, is_ccp: bool):
        ccp_label = f"{RED}★ CCP{RESET}" if is_ccp else f"{CYAN}non-CCP{RESET}"
        print(f"\n  {BOLD}{name}{RESET}  |  stride={BOLD}{stride} s{RESET}  |  {ccp_label}")
        print(f"  {'t(s)':<6} {'Phase':<12} {'Vib(g)':<10} {'Risk':<12} {'Dominant':<12} {'First warn at'}")
        print(f"  {'────':<6} {'─────':<12} {'──────':<10} {'────':<12} {'────────':<12}")

        buf = StreamBuffer(machine_id=machine_id, window_size=60, prediction_stride=stride)
        trend: list[str] = []
        first_warn_t: int | None = None

        for t in range(120):
            phase = "normal" if t < 40 else ("degrading" if t < 80 else "critical")
            reading = _generate_reading(phase, t)
            should_predict = buf.add_reading(**reading)

            if should_predict:
                inputs = buf.get_inference_inputs()
                assert inputs is not None
                result = _simple_predict(*inputs)
                trend.append(result["risk_level"])
                buf.store_prediction(result=result, aggregation=buf.latest_aggregation)

                risk = result["risk_level"]
                if risk != "normal" and first_warn_t is None:
                    first_warn_t = t

                sym   = RISK_SYMBOL.get(risk, "?")
                rline = _colour(risk, f"{sym} {risk.upper():<10}")
                warn_label = f"← first warn t={t}" if t == first_warn_t else ""
                print(
                    f"  {t:<6} {phase:<12} {reading['vibration_rms']:>8.3f}   "
                    f"{rline} {result['dominant_sensor']:<12} {warn_label}"
                )

        trend_str = "  "
        for r in trend:
            trend_str += _colour(r, RISK_SYMBOL.get(r, "?")) + " "
        print(f"\n  Trend: {trend_str}")
        delay = first_warn_t - 40 if first_warn_t else "?"
        print(f"  Detection delay after degradation started: {BOLD}{delay} s{RESET}\n")
        return first_warn_t

    t_pump = _run_machine("KERRY-PUMP-001",  "Pump P-101    (CCP-adjacent)",  stride=5,  is_ccp=False)
    t_comp = _run_machine("KERRY-COMP-300",  "Compressor C-300  (non-CCP)",   stride=30, is_ccp=False)

    print(f"  {BOLD}Comparison:{RESET}")
    print(f"  Pump (stride=5 s):        first warning at t={t_pump} s  → delay ≈ {(t_pump or 40)-40} s after degradation")
    print(f"  Compressor (stride=30 s): first warning at t={t_comp} s  → delay ≈ {(t_comp or 40)-40} s after degradation")
    print(f"\n  {GREEN}✔  Pump detects faster — correct for high-risk bearing equipment.{RESET}")
    print(f"  {CYAN}ℹ  Compressor delay is acceptable — non-CCP, gradual wear.{RESET}")

    print(f"\n  {BOLD}Pattern (Sir Ronny's example — Pump P-101):{RESET}")
    print(f"  {GREEN}● normal{RESET} → {GREEN}● normal{RESET} → {YELLOW}▲ warning{RESET} → {RED}✖ critical{RESET}")
    print(f"\n  Window keeps ROLLING — no dead time between predictions.\n")


# ─── Aggregation explainer ────────────────────────────────────────────────────

def demo_aggregation_explainer():
    print(f"\n{BOLD}{CYAN}══════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{CYAN}  HOW AGGREGATION MAPS TO ML FEATURES                 {RESET}")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════{RESET}\n")
    print("  Raw sensor (1 Hz)  →  Rolling window (60 s)  →  Aggregated features  →  ML model")
    print()
    print(f"  {'Raw value':<22} {'Aggregation used':<28} {'Why'}")
    print(f"  {'─────────':<22} {'────────────────':<28} {'───'}")
    rows = [
        ("Vibration (g)",    "RMS of window",          "Captures peak energy, not just mean"),
        ("Motor current (A)","Mean of window",          "Average load is the stable signal"),
        ("Temperature (°C)", "Mean or Max of window",  "Max catches transient spikes"),
        ("Flow rate (L/min)","Mean of window",          "Flow is relatively steady"),
    ]
    for sensor, agg, why in rows:
        print(f"  {sensor:<22} {agg:<28} {why}")

    print()
    print("  OLTP note (Sir Ronny):")
    print("  Each /api/stream/ingest call is a single row insert (like an OLTP write).")
    print("  The rolling buffer acts as an in-memory OLAP window over recent OLTP rows.")
    print("  avg / max / min per window = the aggregation layer Sir Ronny described.\n")


# ─── Recommendation table ─────────────────────────────────────────────────────

def demo_frequency_table():
    print(f"\n{BOLD}{CYAN}══════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{CYAN}  HYBRID RECOMMENDATION — PREDICTION FREQUENCY        {RESET}")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════{RESET}\n")
    rows = [
        # (equipment, CCP?, stride, mode, reason)
        ("Pasteurizer (CCP)",    True,  "5 s",   "Sliding", "Underpasteurised product = direct health hazard"),
        ("Mixer M-204 (CCP)",    True,  "5 s",   "Sliding", "Mixing stage = CCP, early fault must be caught"),
        ("Pump P-101",           False, "5 s",   "Sliding", "Bearing fault can be sudden — fast stride safer"),
        ("Compressor C-300",     False, "30 s",  "Sliding", "Non-CCP, wear is gradual — 30 s is sufficient"),
        ("Spray Dryer SD-305",   False, "30 s",  "Sliding", "Non-CCP, thermal inertia slows fault progression"),
        ("RUL report (all)",     False, "per shift", "Batch","RUL changes over hours, per-shift report enough"),
    ]
    print(f"  {'Equipment':<28} {'CCP':<6} {'Stride':<12} {'Mode':<10} {'Reason'}")
    print(f"  {'─────────':<28} {'───':<6} {'──────':<12} {'────':<10} {'──────'}")
    for eq, is_ccp, stride, mode, reason in rows:
        ccp_mark = f"{RED}★ YES{RESET}" if is_ccp else f"  no "
        print(f"  {eq:<28} {ccp_mark}  {stride:<12} {mode:<10} {reason}")
    print()
    print("  All equipment uses Option 2 (sliding window) for live monitoring.")
    print("  Option 1 (batch) is reserved for RUL shift reports only.")
    print()
    print("  Sensor sampling rate (1 Hz) is always separate from prediction frequency.")
    print("  Every reading enters the buffer; prediction fires only on stride.\n")


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{BOLD}PredictaGuard — Real-Time Streaming Demo{RESET}")
    print(f"Kerry Group Predictive Maintenance | Anomaly Hunters\n")

    demo_option1_batch()
    time.sleep(0.5)
    demo_option2_sliding()
    time.sleep(0.5)
    demo_aggregation_explainer()
    time.sleep(0.5)
    demo_frequency_table()

    print(f"{BOLD}Demo complete.{RESET}")
    print("Run the API and try: POST http://localhost:8000/api/stream/ingest")
    print("                      GET  http://localhost:8000/api/stream/status/KERRY-PUMP-001\n")
