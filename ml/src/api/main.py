"""
PredictaGuard — FastAPI application.

Run from ml/ directory:
    python -X utf8 -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload

Then open http://localhost:8000/overview.html in your browser.
"""
try:
    import src.api.local_config
except ImportError:
    pass

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from typing import Optional
from pydantic import BaseModel

from src.api.schemas import (
    HealthResponse, InferenceRequest, InferenceResponse,
    EquipmentStatusResponse, AlertsResponse, SimulateStepResponse,
    SensorReadingRequest, StreamIngestResponse, StreamStatusResponse,
    StreamAggregation, SensorAggregation, SensorAggregationRMS,
    StreamConfigItem, StreamConfigResponse,
)
from src.api.predictor import Predictor
from src.api.simulator import Simulator
from src.api.stream_buffer import StreamBuffer
from src.api.db_manager import DBManager



# Per-equipment streaming configuration (hybrid recommendation)
#
# Rationale:
#   CCP equipment (pasteurizer, pump, mixer) → stride 5 s: food safety requires
#   fast anomaly detection; a 60-second delay is unacceptable at CCP stages.
#
#   Non-CCP equipment (compressor, spray dryer) → stride 30 s: degradation is
#   gradual; 30-second predictions are sufficient and reduce compute load.
#
#   RUL (shift report) is handled by /api/predict/inference on-demand and
#   does not need a per-second streaming buffer.

_STREAM_CONFIG: dict[str, dict] = {
    "ASTRA-MTR-101": {
        "window_size": 60,
        "stride":      5,
        "is_ccp":      False,
        "ccp_type":    "N/A",
        "reason":      "Conveyor motor — bearing fault risk — fast detection needed",
        "mode":        "sliding",
    },
    "ASTRA-MTR-204": {
        "window_size": 60,
        "stride":      5,
        "is_ccp":      True,
        "ccp_type":    "Cooling Fan / Thermal Control",
        "reason":      "CCP stage — cooling fan failure risks system overheating",
        "mode":        "sliding",
    },
    "ASTRA-MTR-300": {
        "window_size": 60,
        "stride":      30,
        "is_ccp":      False,
        "ccp_type":    "N/A",
        "reason":      "Water Pump motor — gradual wear, 30-s stride sufficient",
        "mode":        "sliding",
    },
    "ASTRA-MTR-305": {
        "window_size": 60,
        "stride":      30,
        "is_ccp":      False,
        "ccp_type":    "N/A",
        "reason":      "Air Compressor motor — gradual wear",
        "mode":        "sliding",
    },
    "ASTRA-MTR-100": {
        "window_size": 60,
        "stride":      5,
        "is_ccp":      True,
        "ccp_type":    "Pasteurisation Drive",
        "reason":      "CCP — underpasteurised product due to motor slip is a direct health hazard",
        "mode":        "sliding",
    },
}
_DEFAULT_CFG: dict = {
    "window_size": 60,
    "stride":      5,
    "is_ccp":      False,
    "ccp_type":    "N/A",
    "reason":      "Default — apply fast stride as safe fallback",
    "mode":        "sliding",
}


# Resolve paths relative to this file's location
# ml/src/api/main.py  →  PROJECT_ROOT = d:/Kerry

_THIS_DIR    = os.path.dirname(os.path.abspath(__file__))
_ML_DIR      = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", ".."))  # d:/Kerry/ml/../.. = d:/Kerry? No
# Actually: this file is at d:/Kerry/ml/src/api/main.py
# Parent chain: api → src → ml → Kerry (PROJECT_ROOT)
_ML_DIR      = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))        # d:/Kerry/ml
_DATA_DIR    = os.path.join(_ML_DIR, "data")
_DASH_DIR    = os.path.abspath(os.path.join(_ML_DIR, "..","dashboard"))    # d:/Kerry/dashboard



# Application state

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models once at startup; clean up on shutdown."""
    print("Project ASTRA API: initializing database...")
    db = DBManager(project_root=_ML_DIR)
    state["db"] = db

    print("Project ASTRA API: loading models...")
    predictor  = Predictor(ml_dir=_ML_DIR)
    simulator  = Simulator(predictor=predictor, ml_dir=_ML_DIR, data_dir=_DATA_DIR, db_manager=db)
    state["predictor"] = predictor
    state["simulator"] = simulator
    print("Project ASTRA API: ready.")
    yield
    state.clear()


app = FastAPI(
    title="Project ASTRA API",
    description="On-Premise Induction Motor Predictive Maintenance",
    version="1.0.0",
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# API routes (must be registered before StaticFiles mount)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    pred = state.get("predictor")
    return HealthResponse(
        status="ok",
        models_loaded=pred is not None,
        model_info=pred.model_info if pred else {},
    )


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
def auth_login(req: LoginRequest):
    db: DBManager = state.get("db")
    if db is None:
        raise HTTPException(status_code=503, detail="Database manager not initialized")
    user = db.verify_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Access denied. Invalid credentials.")
    return user


class UpdateProfileRequest(BaseModel):
    name: str
    title: str
    new_email: str
    avatar: Optional[str] = None


@app.put("/api/users/profile/{email}")
def update_user_profile_route(email: str, req: UpdateProfileRequest):
    import psycopg2.extras
    db: DBManager = state.get("db")
    if db is None:
        raise HTTPException(status_code=503, detail="Database manager not initialized")
    success = db.update_user_profile(email, req.name, req.title, req.new_email, req.avatar)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
        
    conn = db.get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT email, name, role, clearance, title, avatar FROM users WHERE LOWER(email) = LOWER(%s)", (req.new_email.strip(),))
        row = cursor.fetchone()
        if row:
            return dict(row)
        raise HTTPException(status_code=404, detail="User profile not found after update")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
def predict_inference(req: InferenceRequest) -> InferenceResponse:
    pred: Predictor = state.get("predictor")
    if pred is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    return pred.infer_from_sliders(
        vibration_rms=req.vibration_rms,
        motor_current=req.motor_current,
        temperature=req.temperature,
        flow_rate=req.flow_rate,
    )


@app.get("/api/equipment/status", response_model=EquipmentStatusResponse)
def equipment_status() -> EquipmentStatusResponse:
    sim: Simulator = state.get("simulator")
    if sim is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    return sim.get_equipment_status()


@app.get("/api/alerts", response_model=AlertsResponse)
def alerts() -> AlertsResponse:
    sim: Simulator = state.get("simulator")
    if sim is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    return sim.get_alerts()


@app.get("/api/simulate/step", response_model=SimulateStepResponse)
def simulate_step() -> SimulateStepResponse:
    sim: Simulator = state.get("simulator")
    if sim is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    return sim.step()



# Streaming endpoints — real-time per-second ingestion (Sir Ronny feedback)


def _build_stream_aggregation(agg: dict) -> StreamAggregation:
    return StreamAggregation(
        vibration_rms=SensorAggregationRMS(**agg["vibration_rms"]),
        motor_current=SensorAggregation(**agg["motor_current"]),
        temperature=SensorAggregation(**agg["temperature"]),
        flow_rate=SensorAggregation(**agg["flow_rate"]),
    )


@app.post("/api/stream/ingest", response_model=StreamIngestResponse)
def stream_ingest(req: SensorReadingRequest) -> StreamIngestResponse:
    """
    Accept one sensor reading from the field (OLTP-style, every second).

    - Maintains a per-machine rolling buffer of the last `window_size` readings.
    - Computes avg / max / min / rms per sensor after every reading.
    - Triggers ML inference automatically every `prediction_stride` readings.

    This implements Sir Ronny's Option 2 (sliding window / streaming).
    For Option 1 (batch), set `prediction_stride = window_size` when creating
    the buffer, or simply collect all readings and call /api/predict/inference once.
    """
    pred: Predictor = state.get("predictor")
    if pred is None:
        raise HTTPException(status_code=503, detail="Models not loaded")

    buffers: dict[str, StreamBuffer] = state.setdefault("stream_buffers", {})
    if req.machine_id not in buffers:
        cfg = _STREAM_CONFIG.get(req.machine_id, _DEFAULT_CFG)
        buffers[req.machine_id] = StreamBuffer(
            machine_id=req.machine_id,
            window_size=cfg["window_size"],
            prediction_stride=cfg["stride"],
        )

    buf = buffers[req.machine_id]
    should_predict = buf.add_reading(
        vibration_rms=req.vibration_rms,
        motor_current=req.motor_current,
        temperature=req.temperature,
        flow_rate=req.flow_rate,
        timestamp=req.timestamp,
    )

    # ─── AUTO-ALERT SYSTEM ON PARAMETER BREACH ─────────────────────────────
    breach_messages = []
    if req.temperature >= 140.0:
        breach_messages.append(f"Temperature reached {req.temperature}°C (Limit: 140°C)")
    if req.vibration_rms >= 8.0:
        breach_messages.append(f"Vibration RMS reached {req.vibration_rms} mm/s (Limit: 8.0 mm/s)")
    if req.motor_current >= 15.0:
        breach_messages.append(f"Motor current reached {req.motor_current} A (Limit: 15.0 A)")

    if breach_messages:
        details_str = ", ".join(breach_messages)
        print(f"[ALERT-BREACH] Safety threshold violated on {req.machine_id}: {details_str}!")
        try:
            from src.api.notifier import trigger_alert_notifications
            trigger_alert_notifications(
                machine_id=req.machine_id,
                alert_type="safety_limit_breach",
                title="SAFETY CRITICAL LIMIT BREACH",
                details=f"Machine {req.machine_id} critical thresholds breached: {details_str}.",
                force=False  # Cooldown rate-limit applies (5 mins)
            )
        except Exception as e:
            print(f"[ALERT-BREACH] Failed to auto-dispatch notifications: {e}")

    inference_result: InferenceResponse | None = None
    if should_predict:
        inputs = buf.get_inference_inputs()
        if inputs is not None:
            vib, cur, tmp, flw = inputs
            inference_result = pred.infer_from_sliders(
                vibration_rms=vib,
                motor_current=cur,
                temperature=tmp,
                flow_rate=flw,
            )
            buf.store_prediction(
                result=inference_result.model_dump(),
                aggregation=buf.latest_aggregation,
            )

    agg = buf.latest_aggregation
    return StreamIngestResponse(
        machine_id=req.machine_id,
        buffer_fill=buf.buffer_fill,
        window_size=buf.window_size,
        readings_until_next_prediction=buf.readings_until_next_prediction,
        prediction_triggered=should_predict,
        aggregation=_build_stream_aggregation(agg) if agg else None,
        prediction=inference_result,
    )
@app.post("/api/db/insert")
def db_insert(req: SensorReadingRequest):
    """
    Manually insert a telemetry reading into the SQLite database.
    This simulates sensor ingestion from a machine in the field.
    """
    db: DBManager = state.get("db")
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    # Process through the cleaning & preprocessing pipeline and save to DB
    cleaned_v, cleaned_c, cleaned_t, cleaned_f = db.insert_telemetry(
        req.machine_id, req.vibration_rms, req.motor_current, req.temperature, req.flow_rate
    )
    
    return {
        "status": "success",
        "cleaned_data": {
            "machine_id": req.machine_id,
            "vibration_rms": cleaned_v,
            "motor_current": cleaned_c,
            "temperature": cleaned_t,
            "flow_rate": cleaned_f,
        }
    }


@app.get("/api/stream/status/{machine_id}", response_model=StreamStatusResponse)
def stream_status(machine_id: str) -> StreamStatusResponse:
    """
    Return the current rolling-window state and latest prediction for one machine.

    `prediction_trend` is a list of the last N risk_level strings (oldest first),
    so the dashboard can render the normal-normal-not-normal pattern as coloured dots.
    """
    buffers: dict[str, StreamBuffer] = state.get("stream_buffers", {})
    if machine_id not in buffers:
        raise HTTPException(
            status_code=404,
            detail=f"No stream buffer found for '{machine_id}'. "
                   f"POST at least one reading to /api/stream/ingest first.",
        )

    buf = buffers[machine_id]
    agg = buf.latest_aggregation
    last_pred_entry = buf.last_prediction
    last_inference: InferenceResponse | None = None
    if last_pred_entry:
        last_inference = InferenceResponse(**last_pred_entry["prediction"])

    return StreamStatusResponse(
        machine_id=machine_id,
        buffer_fill=buf.buffer_fill,
        window_size=buf.window_size,
        is_ready=buf.is_ready,
        aggregation=_build_stream_aggregation(agg) if agg else None,
        last_prediction=last_inference,
        seconds_since_last_prediction=buf.seconds_since_last_prediction,
        prediction_trend=buf.prediction_trend,
    )


@app.get("/api/stream/config", response_model=StreamConfigResponse)
def stream_config() -> StreamConfigResponse:
    """
    Return the per-equipment streaming configuration table.
    Frontend uses this to display the correct stride / CCP badge per machine.
    """
    items = []
    for machine_id, cfg in _STREAM_CONFIG.items():
        items.append(StreamConfigItem(
            machine_id=machine_id,
            window_size=cfg["window_size"],
            prediction_stride=cfg["stride"],
            is_ccp=cfg["is_ccp"],
            ccp_type=cfg["ccp_type"],
            reason=cfg["reason"],
            mode=cfg["mode"],
        ))
    return StreamConfigResponse(equipment=items)


class WorkOrderRequest(BaseModel):
    asset_id: str
    asset_name: str
    description: str
    assigned_tech: Optional[str] = 'Unassigned'


@app.get("/api/workorders")
def get_work_orders():
    db: DBManager = state.get("db")
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return {"work_orders": db.get_work_orders()}


@app.post("/api/workorders")
def create_work_order(req: WorkOrderRequest):
    db: DBManager = state.get("db")
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db.create_work_order(req.asset_id, req.asset_name, req.description, req.assigned_tech)


class UpdateWorkOrderRequest(BaseModel):
    status: str
    description: Optional[str] = None
    assigned_tech: Optional[str] = None


@app.put("/api/workorders/{wo_id}")
def update_work_order_route(wo_id: str, req: UpdateWorkOrderRequest):
    db: DBManager = state.get("db")
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    success = db.update_work_order(wo_id, req.status, req.description, req.assigned_tech)
    if not success:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    return {"status": "success", "message": f"Work order {wo_id} updated"}


@app.delete("/api/workorders/{wo_id}")
def delete_work_order_route(wo_id: str):
    db: DBManager = state.get("db")
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    success = db.delete_work_order(wo_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    return {"status": "success", "message": f"Work order {wo_id} deleted"}


class DispatchAlertRequest(BaseModel):
    machine_id: str
    message: str

@app.post("/api/alerts/dispatch")
def dispatch_alert(req: DispatchAlertRequest):
    from src.api.notifier import trigger_alert_notifications
    # Trigger instant Email/WhatsApp dispatch bypass cooldown
    trigger_alert_notifications(
        machine_id=req.machine_id,
        alert_type="manual_dispatch",
        title="Manual Operator Dispatch",
        details=req.message,
        force=True
    )
    return {"status": "success", "message": f"Alert dispatched for {req.machine_id}"}


class NotificationSettingsRequest(BaseModel):
    smtp_server: str
    smtp_port: int
    sender_email: str
    sender_password: Optional[str] = None
    recipient_email: str
    twilio_account_sid: str
    twilio_auth_token: Optional[str] = None
    twilio_whatsapp_from: str
    recipient_whatsapp: str

@app.get("/api/settings/notifications")
def get_notification_settings_endpoint():
    db: DBManager = state.get("db")
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    settings = db.get_notification_settings()
    if settings:
        # Mask password and auth token for security
        if settings.get("sender_password"):
            settings["sender_password"] = "********"
        if settings.get("twilio_auth_token"):
            settings["twilio_auth_token"] = "********"
    return settings

@app.post("/api/settings/notifications")
def save_notification_settings_endpoint(req: NotificationSettingsRequest):
    db: DBManager = state.get("db")
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    existing = db.get_notification_settings()
    
    pwd = req.sender_password
    if pwd == "********" or not pwd:
        pwd = existing.get("sender_password") if existing else None
        
    token = req.twilio_auth_token
    if token == "********" or not token:
        token = existing.get("twilio_auth_token") if existing else None
        
    settings_dict = req.model_dump()
    settings_dict["sender_password"] = pwd
    settings_dict["twilio_auth_token"] = token
    
    db.save_notification_settings(settings_dict)
    return {"status": "success", "message": "Notification settings saved successfully."}



# Static file serving — dashboard/ at root (register LAST, after API routes)

if os.path.isdir(_DASH_DIR):
    app.mount("/", StaticFiles(directory=_DASH_DIR, html=True), name="dashboard")
