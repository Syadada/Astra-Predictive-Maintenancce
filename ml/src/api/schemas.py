"""
PredictaGuard API — Pydantic request/response schemas.
"""
from typing import Any, Optional
from pydantic import BaseModel


class InferenceRequest(BaseModel):
    vibration_rms: float   # 0.188–0.60 g (CWRU range)
    motor_current: float   # 0.85–4.00 A
    temperature: float     # 75–110 °C
    flow_rate: float       # 100–130 L/min


class SHAPValues(BaseModel):
    vibration: float
    temperature: float
    current: float
    flow: float


class HistoricalMatch(BaseModel):
    date: str              # "2024-02-10"
    similarity: float      # 0.87
    failure_type: str      # "Outer race fault — bearing replacement"
    rul_at_event: int      # hours to failure when this historical event occurred


class RecommendationDetail(BaseModel):
    action: str
    part_number: str
    cost_if_ignored_usd: int
    downtime_hours: int
    maintenance_window: str


class CCPAlert(BaseModel):
    is_ccp: bool
    ccp_type: str          # "Pasteurization" | "Mixing" | "N/A"
    priority: str          # "CRITICAL" | "HIGH" | "NORMAL"


class InferenceResponse(BaseModel):
    anomaly_score: float       # 0–1
    risk_level: str            # "minimal" | "elevated" | "critical"
    fault_class: str
    fault_confidence: float
    rul_cycles: int
    rul_hours: int
    recommendation: str
    shap_values: SHAPValues
    historical_match: Optional[HistoricalMatch] = None
    recommendation_detail: RecommendationDetail
    ccp_alert: CCPAlert


class EquipmentItem(BaseModel):
    id: str
    name: str
    location: str
    status: str            # "optimal" | "warning" | "critical"
    rul_hours: int
    health_index: float    # 0–1
    anomaly_score: float   # 0–1
    fault_class: str
    sensor_sparkline: list[float]


class KPIs(BaseModel):
    overall_health: int
    at_risk: int
    predicted_failures: int
    downtime_avoided_h: float


class EquipmentStatusResponse(BaseModel):
    kpis: KPIs
    equipment: list[EquipmentItem]


class FeatureImpact(BaseModel):
    name: str
    impact: float
    color: str   # "red" | "amber" | "muted"


class AlertItem(BaseModel):
    id: str
    severity: str          # "critical" | "warning"
    asset_id: str
    asset_name: str
    title: str
    value: float
    unit: str
    threshold: float
    minutes_ago: int
    confidence: float
    feature_impacts: list[FeatureImpact]
    recommendations: list[str]


class AlertSummary(BaseModel):
    critical: int
    warning: int


class AlertsResponse(BaseModel):
    summary: AlertSummary
    alerts: list[AlertItem]


class SimulateStepResponse(BaseModel):
    cursor: int
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    model_info: dict[str, Any]



# Streaming / real-time schemas (Sir Ronny Option 1 + Option 2)


class SensorReadingRequest(BaseModel):
    """One sensor reading pushed by OLTP pipeline (e.g. every second)."""
    machine_id: str
    vibration_rms: float   # g
    motor_current: float   # A
    temperature: float     # °C
    flow_rate: float       # L/min
    timestamp: Optional[float] = None  # Unix epoch; server time used if omitted


class SensorAggregation(BaseModel):
    avg: float
    max: float
    min: float


class SensorAggregationRMS(SensorAggregation):
    rms: float


class StreamAggregation(BaseModel):
    """avg / max / min (+ rms for vibration) over the current rolling window."""
    vibration_rms: SensorAggregationRMS
    motor_current: SensorAggregation
    temperature:   SensorAggregation
    flow_rate:     SensorAggregation


class StreamIngestResponse(BaseModel):
    """Returned by POST /api/stream/ingest on every call."""
    machine_id: str
    buffer_fill: int                    # how many readings are in the window
    window_size: int                    # total window capacity (seconds)
    readings_until_next_prediction: int
    prediction_triggered: bool          # True when ML inference ran this call
    aggregation: Optional[StreamAggregation] = None
    prediction: Optional[InferenceResponse] = None


class StreamStatusResponse(BaseModel):
    """Returned by GET /api/stream/status/{machine_id}."""
    machine_id: str
    buffer_fill: int
    window_size: int
    is_ready: bool
    aggregation: Optional[StreamAggregation] = None
    last_prediction: Optional[InferenceResponse] = None
    seconds_since_last_prediction: Optional[float] = None
    prediction_trend: list[str]         # ["normal","normal","warning","critical"]


class StreamConfigItem(BaseModel):
    """Streaming configuration for one piece of equipment."""
    machine_id: str
    window_size: int           # seconds in rolling window
    prediction_stride: int     # predict every N readings
    is_ccp: bool               # Critical Control Point?
    ccp_type: str              # "Pasteurisation" | "Mixing" | "N/A"
    reason: str                # why this stride was chosen
    mode: str                  # "sliding" | "batch"


class StreamConfigResponse(BaseModel):
    """Returned by GET /api/stream/config."""
    equipment: list[StreamConfigItem]
