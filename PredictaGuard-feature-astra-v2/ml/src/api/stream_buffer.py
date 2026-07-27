"""
StreamBuffer: per-machine rolling window for real-time sensor ingestion.

Architecture (Sir Ronny's feedback):
  Sensor 1Hz  →  POST /api/stream/ingest  →  StreamBuffer.add_reading()
                                               ↓
                                    Rolling window (last 60 s)
                                               ↓
                                    Aggregations: avg / max / min / rms
                                               ↓ (every `stride` readings)
                                    ML inference  →  prediction_history
                                               ↓
                                  GET /api/stream/status/{machine_id}

Option 1 (batch): set stride = window_size  → predict once per full window
Option 2 (sliding): set stride = 1..N       → predict every N new readings
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Optional

import numpy as np


class StreamBuffer:
    """
    Holds the last `window_size` sensor readings for one machine.

    Parameters
    ----------
    machine_id : str
        Unique equipment identifier (e.g. "ASTRA-MTR-101").
    window_size : int
        Number of seconds to keep in the rolling window.  Default 60.
    prediction_stride : int
        Trigger ML inference every this many new readings.
        stride=1  → predict on every reading (true streaming)
        stride=30 → predict twice per window (moderate)
        stride=60 → predict once per window (batch-equivalent)
    """

    def __init__(
        self,
        machine_id: str,
        window_size: int = 60,
        prediction_stride: int = 5,
    ) -> None:
        self.machine_id = machine_id
        self.window_size = window_size
        self.prediction_stride = prediction_stride

        # Rolling window: each entry is [vibration_rms, motor_current, temperature, flow_rate]
        self._buf: deque[list[float]] = deque(maxlen=window_size)
        self._timestamps: deque[float] = deque(maxlen=window_size)

        self._readings_since_pred: int = 0
        self._last_pred_time: Optional[float] = None

        # Prediction history — last 10 results kept for trend display
        self._MAX_HISTORY: int = 10
        self.prediction_history: list[dict[str, Any]] = []

        # Latest aggregation snapshot (updated on every add_reading call)
        self.latest_aggregation: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Core ingestion
    # ------------------------------------------------------------------

    def add_reading(
        self,
        vibration_rms: float,
        motor_current: float,
        temperature: float,
        flow_rate: float,
        timestamp: Optional[float] = None,
    ) -> bool:
        """
        Push one sensor reading into the buffer.

        Returns True when ML inference should be triggered:
          - buffer holds at least `min(window_size, 10)` readings, AND
          - `prediction_stride` new readings have arrived since last inference.
        """
        ts = timestamp if timestamp is not None else time.time()
        self._buf.append([vibration_rms, motor_current, temperature, flow_rate])
        self._timestamps.append(ts)
        self._readings_since_pred += 1

        # Recompute aggregations on every reading (cheap with numpy)
        self._update_aggregation()

        min_fill = min(self.window_size, 10)
        ready = len(self._buf) >= min_fill
        stride_reached = self._readings_since_pred >= self.prediction_stride

        should_predict = ready and stride_reached
        if should_predict:
            self._readings_since_pred = 0
            self._last_pred_time = ts
        return should_predict

    def _update_aggregation(self) -> None:
        if not self._buf:
            return
        data = np.array(self._buf)  # shape (n, 4)

        def _stats(col: int, include_rms: bool = False) -> dict[str, float]:
            arr = data[:, col]
            d: dict[str, float] = {
                "avg": float(np.mean(arr)),
                "max": float(np.max(arr)),
                "min": float(np.min(arr)),
            }
            if include_rms:
                d["rms"] = float(np.sqrt(np.mean(arr ** 2)))
            return d

        self.latest_aggregation = {
            "vibration_rms": _stats(0, include_rms=True),
            "motor_current":  _stats(1),
            "temperature":     _stats(2),
            "flow_rate":       _stats(3),
        }

    # ------------------------------------------------------------------
    # Inference helpers
    # ------------------------------------------------------------------

    def get_inference_inputs(self) -> Optional[tuple[float, float, float, float]]:
        """
        Return (vibration_rms, motor_current, temperature, flow_rate) aggregated
        values suitable for Predictor.infer_from_sliders().

        Uses:
          - vibration: true RMS of the window (captures peak energy, not just average)
          - motor_current, temperature, flow_rate: mean of window
        """
        agg = self.latest_aggregation
        if not agg:
            return None
        return (
            agg["vibration_rms"]["rms"],
            agg["motor_current"]["avg"],
            agg["temperature"]["avg"],
            agg["flow_rate"]["avg"],
        )

    def store_prediction(
        self,
        result: dict[str, Any],
        aggregation: dict[str, Any],
    ) -> None:
        """Save the latest inference result into prediction_history."""
        self.prediction_history.append({
            "timestamp": self._last_pred_time or time.time(),
            "buffer_size": len(self._buf),
            "aggregation": aggregation,
            "prediction": result,
        })
        if len(self.prediction_history) > self._MAX_HISTORY:
            self.prediction_history.pop(0)

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    @property
    def buffer_fill(self) -> int:
        return len(self._buf)

    @property
    def is_ready(self) -> bool:
        """True once the buffer has accumulated enough readings for inference."""
        return len(self._buf) >= min(self.window_size, 10)

    @property
    def readings_until_next_prediction(self) -> int:
        remaining = self.prediction_stride - self._readings_since_pred
        return max(0, remaining)

    @property
    def last_prediction(self) -> Optional[dict[str, Any]]:
        return self.prediction_history[-1] if self.prediction_history else None

    @property
    def prediction_trend(self) -> list[str]:
        """List of risk_level strings from oldest → newest, for trend display."""
        return [p["prediction"].get("risk_level", "unknown") for p in self.prediction_history]

    @property
    def seconds_since_last_prediction(self) -> Optional[float]:
        if self._last_pred_time is None:
            return None
        return time.time() - self._last_pred_time
