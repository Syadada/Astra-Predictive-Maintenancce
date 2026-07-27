# MASUKAN FRONTEND & PROJECT INTEGRATION
## Anomaly Hunters - Kerry Group Predictive Maintenance

---

## **PART I: MASALAH FRONTEND YANG MUNGKIN KALIAN ALAMI**

### **Problem Statement: "Frontend kurang relevan dengan data yang ada"**

Ini adalah issue umum di ML project. Mari kita diagnosa:

---

## **A. TIPICAL FRONTEND ISSUES DI PREDICTIVE MAINTENANCE DASHBOARD**

### **Issue #1: Data-Visualization Mismatch**

**Gejala:**
- ❌ Dashboard show generic charts (bar, line graph) tapi data monitoring sensors itu **continuous, multi-dimensional**
- ❌ Real-time alert system tidak terintegrasi dengan anomaly detection output
- ❌ XAI explanation (SHAP values) displayed as table, bukan visual yang intuitive

**Solusi Frontend yang HARUS ada:**

```
RECOMENDED DASHBOARD LAYOUT:

┌─────────────────────────────────────────────────────────┐
│ ANOMALY HUNTERS - KERRY GROUP PREDICTIVE MAINTENANCE   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ [REAL-TIME EQUIPMENT STATUS]  [CRITICAL ALERTS (5)]    │
│ ┌──────────────────┐         ┌──────────────────────┐  │
│ │ PUMP-01: 78% ok  │         │ MIXER-03: RUL 48h   │  │
│ │ MIXER-02: 45% ok │         │ SPRAY-01: Anomaly   │  │
│ │ SPRAY-01: ⚠️ 15% │         │ COMPRESSOR: High T  │  │
│ └──────────────────┘         └──────────────────────┘  │
│                                                          │
│ [REAL-TIME SENSOR STREAMS] (Multi-Equipment View)      │
│ ┌──────────────────────────────────────────────────┐   │
│ │ Equipment: PUMP-01 [SELECT ANOTHER ▼]           │   │
│ │                                                  │   │
│ │ Vibration (Hz/g)  Temperature (°C)  Current (A) │   │
│ │ ┌──────────────┐  ┌──────────────┐  ┌────────┐ │   │
│ │ │ [REAL-TIME   │  │ [TREND LINE  │  │ [GAUGE]│ │   │
│ │ │  WAVEFORM]   │  │  72H HISTORY]│  │ NORMAL │ │   │
│ │ │ Normal range │  │ Peak: 78°C   │  │ 12.5A  │ │   │
│ │ │ 8-10 mm/s    │  │ Alert: >85°C │  │ ±2%    │ │   │
│ │ └──────────────┘  └──────────────┘  └────────┘ │   │
│ └──────────────────────────────────────────────────┘   │
│                                                          │
│ [XAI EXPLANATION] (WHY is this equipment failing?)    │
│ ┌──────────────────────────────────────────────────┐   │
│ │ Alert: PUMP-01 Anomaly Detected (87% confidence)│   │
│ │                                                  │   │
│ │ Contributing Factors (SHAP):                    │   │
│ │ ████████ Vibration >12mm/s (52% contribution)  │   │
│ │ ████████ Temperature rising trend (28%)         │   │
│ │ ██ Current draw increased (15%)                │   │
│ │ █ Production load higher (5%)                  │   │
│ │                                                  │   │
│ │ Similar historical pattern:                    │   │
│ │ Failure date 2024-02-10 (Bearing replacement)  │   │
│ │ Time to failure: 48 hours (±12 hours)          │   │
│ │                                                  │   │
│ │ [RECOMMENDED ACTION] ▼                          │   │
│ │ Replace bearing assembly (Part #PMP-001-B)     │   │
│ │ Cost if ignored: $2,500 + 4h downtime          │   │
│ │ Schedule window: Tomorrow 22:00-02:00 UTC      │   │
│ │ [SEND TO MAINTENANCE TEAM] [APPROVE ACTION]    │   │
│ └──────────────────────────────────────────────────┘   │
│                                                          │
│ [CCP CRITICAL CONTROL POINT ALERTS]                   │
│ ┌──────────────────────────────────────────────────┐   │
│ │ 🔴 Pasteurization Pump (CRITICAL): Anomaly      │   │
│ │    Action Required: Immediate validation         │   │
│ │    HACCP Log Entry: AUTO-GENERATED [VERIFY]      │   │
│ │                                                  │   │
│ │ 🟡 Mixing Tank (HIGH): Temperature High         │   │
│ │    Action: Monitor next 2h, alert if >90°C      │   │
│ │                                                  │   │
│ │ 🟢 Compressor (NORMAL): No anomaly              │   │
│ └──────────────────────────────────────────────────┘   │
│                                                          │
│ [ACTION LOG & HISTORY]                                 │
│ ┌──────────────────────────────────────────────────┐   │
│ │ 14:32 - Alert created: PUMP-01 anomaly          │   │
│ │ 14:33 - SMS sent to Team Lead: Rudi             │   │
│ │ 14:35 - WhatsApp notification: Team             │   │
│ │ [EXPORT LOG] [SEND REPORT] [PDF DOWNLOAD]       │   │
│ └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘

BOTTOM SECTION: [HISTORICAL ANALYTICS] [OEE TRENDS] [COST SAVED]
```

---

### **Issue #2: Data Flow Disconnect**

**Gejala:**
- ❌ Backend generate prediction (anomaly score: 0.87) tapi frontend hanya show raw number
- ❌ SHAP values calculated tapi tidak ditampilkan secara meaningful
- ❌ Real-time sensor data masuk Kafka/InfluxDB tapi frontend use cached data

**Fix Required:**

```python
# BACKEND SIDE (Python/FastAPI)
# =============================

from fastapi import FastAPI, WebSocket
from typing import Dict
import json

app = FastAPI()

# 1. Real-time sensor data via WebSocket
@app.websocket("/ws/sensors/{equipment_id}")
async def websocket_endpoint(websocket: WebSocket, equipment_id: str):
    await websocket.accept()
    while True:
        # Stream dari InfluxDB
        sensor_data = get_latest_sensor_data(equipment_id)
        
        # Compute anomaly score (LSTM Autoencoder)
        anomaly_score = anomaly_detector.predict(sensor_data)
        
        # Compute SHAP explanation
        shap_values = explainer.shap_values(sensor_data)
        shap_features = {
            'vibration': shap_values[0],
            'temperature': shap_values[1],
            'current': shap_values[2]
        }
        
        # Compute RUL (Temporal Fusion Transformer)
        rul_hours = rul_model.predict(sensor_data)
        rul_confidence = rul_model.confidence_interval()  # 90% CI
        
        # Generate recommendation (Phi-3 Mini LLM)
        recommendation = copilot_llm.generate(
            anomaly_score, 
            shap_features, 
            rul_hours,
            equipment_type='pump',
            ccp_status='critical'  # If pasteurization pump
        )
        
        # Send to frontend
        response = {
            'timestamp': datetime.now().isoformat(),
            'equipment_id': equipment_id,
            'sensor': {
                'vibration_mms': sensor_data['vibration'],
                'temperature_c': sensor_data['temperature'],
                'current_a': sensor_data['current']
            },
            'anomaly': {
                'score': float(anomaly_score),
                'is_anomaly': bool(anomaly_score > 0.6),
                'confidence': float(anomaly_score)
            },
            'explainability': {
                'shap_contributions': shap_features,
                'top_factors': sorted(shap_features.items(), 
                                     key=lambda x: abs(x[1]), 
                                     reverse=True)[:3],
                'historical_similar': {
                    'failure_date': '2024-02-10',
                    'similarity': 0.87,
                    'time_to_failure_hours': 48
                }
            },
            'rul': {
                'hours': int(rul_hours),
                'confidence_lower': int(rul_confidence[0]),
                'confidence_upper': int(rul_confidence[1])
            },
            'recommendation': {
                'action': recommendation['action'],
                'part_number': recommendation['part_number'],
                'cost_if_ignored': recommendation['cost'],
                'downtime_hours': recommendation['downtime']
            },
            'ccp_alert': {
                'is_ccp': True,
                'ccp_type': 'Pasteurization',
                'priority': 'CRITICAL' if anomaly_score > 0.8 else 'HIGH'
            }
        }
        
        await websocket.send_json(response)
        await asyncio.sleep(5)  # Update every 5 seconds

# 2. REST endpoint untuk historical data
@app.get("/api/equipment/{equipment_id}/history")
async def get_equipment_history(equipment_id: str, hours: int = 72):
    """Get historical data for trend analysis"""
    return {
        'equipment_id': equipment_id,
        'timerange_hours': hours,
        'sensor_history': get_influxdb_data(equipment_id, hours),
        'anomaly_history': get_anomalies(equipment_id, hours),
        'rul_trend': get_rul_predictions(equipment_id, hours),
        'maintenance_events': get_maintenance_log(equipment_id, hours)
    }

# 3. Alert generation endpoint
@app.post("/api/alerts/{equipment_id}/create")
async def create_alert(equipment_id: str, alert_data: AlertPayload):
    """Create and dispatch alert"""
    # Log to PostgreSQL
    alert = Alert(
        equipment_id=equipment_id,
        anomaly_score=alert_data.anomaly_score,
        shap_explanation=alert_data.shap,
        rul_estimate=alert_data.rul,
        recommendation=alert_data.recommendation,
        priority=alert_data.priority,
        ccp_status=alert_data.ccp_status
    )
    db.session.add(alert)
    db.session.commit()
    
    # Send to WhatsApp, Email, SMS
    if alert.priority == 'CRITICAL':
        send_whatsapp_alert(alert)
        send_sms_alert(alert)
    send_email_alert(alert)
    
    return {'alert_id': alert.id, 'status': 'created'}
```

```javascript
// FRONTEND SIDE (React)
// =====================

import React, { useEffect, useState } from 'react';
import { LineChart, Line, AreaChart, Area } from 'recharts';
import { AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';

export const DashboardPage = () => {
  const [equipmentList, setEquipmentList] = useState([]);
  const [selectedEquipment, setSelectedEquipment] = useState('PUMP-01');
  const [realTimeData, setRealTimeData] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [alerts, setAlerts] = useState([]);

  // WebSocket connection untuk real-time data
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/sensors/${selectedEquipment}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setRealTimeData(data);
      
      // Trigger alert if anomaly detected
      if (data.anomaly.is_anomaly) {
        addAlert(data);
      }
    };

    return () => ws.close();
  }, [selectedEquipment]);

  // Fetch historical data
  useEffect(() => {
    fetch(`/api/equipment/${selectedEquipment}/history?hours=72`)
      .then(r => r.json())
      .then(data => setHistoricalData(data.sensor_history));
  }, [selectedEquipment]);

  if (!realTimeData) return <div>Loading...</div>;

  return (
    <div className="dashboard-container p-6 bg-gray-50 min-h-screen">
      
      {/* HEADER */}
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">
          PredictaGuard - Kerry Group
        </h1>
        <p className="text-gray-600">Predictive Maintenance Dashboard</p>
      </header>

      {/* EQUIPMENT SELECTOR */}
      <div className="mb-4 flex gap-2 flex-wrap">
        {['PUMP-01', 'MIXER-02', 'SPRAY-01', 'COMPRESSOR'].map(eq => (
          <button
            key={eq}
            onClick={() => setSelectedEquipment(eq)}
            className={`px-4 py-2 rounded ${
              selectedEquipment === eq 
                ? 'bg-blue-600 text-white' 
                : 'bg-white border border-gray-300 text-gray-900'
            }`}
          >
            {eq}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        
        {/* REAL-TIME METRICS */}
        <div className="lg:col-span-1 space-y-4">
          
          {/* Status Card */}
          <div className={`p-4 rounded-lg border-2 ${
            realTimeData.anomaly.is_anomaly 
              ? 'bg-red-50 border-red-300' 
              : 'bg-green-50 border-green-300'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              {realTimeData.anomaly.is_anomaly ? (
                <AlertCircle className="w-6 h-6 text-red-600" />
              ) : (
                <CheckCircle className="w-6 h-6 text-green-600" />
              )}
              <h3 className="font-semibold">Equipment Status</h3>
            </div>
            <p className="text-2xl font-bold text-gray-900 mb-1">
              {realTimeData.anomaly.is_anomaly ? '⚠️ ANOMALY' : '✓ NORMAL'}
            </p>
            <p className="text-sm text-gray-600">
              Confidence: {(realTimeData.anomaly.confidence * 100).toFixed(1)}%
            </p>
          </div>

          {/* RUL Card */}
          <div className="p-4 rounded-lg bg-blue-50 border border-blue-300">
            <h3 className="font-semibold mb-3 text-gray-900">
              Remaining Useful Life (RUL)
            </h3>
            <div className="text-center">
              <p className="text-4xl font-bold text-blue-600 mb-1">
                {realTimeData.rul.hours}h
              </p>
              <p className="text-xs text-gray-600 mb-3">
                90% CI: {realTimeData.rul.confidence_lower}h - {realTimeData.rul.confidence_upper}h
              </p>
              <div className="w-full bg-gray-200 rounded h-2">
                <div 
                  className="bg-blue-600 h-2 rounded"
                  style={{
                    width: `${Math.min(100, (realTimeData.rul.hours / 720) * 100)}%`
                  }}
                ></div>
              </div>
            </div>
          </div>

          {/* CCP Alert */}
          {realTimeData.ccp_alert.is_ccp && (
            <div className={`p-4 rounded-lg border-2 ${
              realTimeData.ccp_alert.priority === 'CRITICAL'
                ? 'bg-red-100 border-red-500'
                : 'bg-yellow-100 border-yellow-500'
            }`}>
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="w-5 h-5" />
                <span className="font-semibold">CCP: {realTimeData.ccp_alert.ccp_type}</span>
              </div>
              <p className="text-sm text-gray-700">
                Priority: <strong>{realTimeData.ccp_alert.priority}</strong>
              </p>
              <p className="text-xs text-gray-600 mt-2">
                HACCP audit log auto-generated
              </p>
            </div>
          )}
        </div>

        {/* SENSOR METRICS */}
        <div className="lg:col-span-2 grid grid-cols-3 gap-4 mb-6">
          
          {/* Vibration */}
          <div className="p-4 rounded-lg bg-white border border-gray-200">
            <h4 className="text-sm font-semibold text-gray-600 mb-3">
              Vibration (mm/s)
            </h4>
            <p className="text-3xl font-bold text-gray-900 mb-1">
              {realTimeData.sensor.vibration_mms.toFixed(2)}
            </p>
            <div className="flex items-center justify-between text-xs text-gray-600">
              <span>Normal: 8-10</span>
              <span className={realTimeData.sensor.vibration_mms > 12 ? 'text-red-600 font-bold' : ''}>
                {realTimeData.sensor.vibration_mms > 12 ? '🔴 HIGH' : '🟢 OK'}
              </span>
            </div>
          </div>

          {/* Temperature */}
          <div className="p-4 rounded-lg bg-white border border-gray-200">
            <h4 className="text-sm font-semibold text-gray-600 mb-3">
              Temperature (°C)
            </h4>
            <p className="text-3xl font-bold text-gray-900 mb-1">
              {realTimeData.sensor.temperature_c.toFixed(1)}
            </p>
            <div className="flex items-center justify-between text-xs text-gray-600">
              <span>Threshold: 85</span>
              <span className={realTimeData.sensor.temperature_c > 85 ? 'text-red-600 font-bold' : ''}>
                {realTimeData.sensor.temperature_c > 85 ? '🔴 HIGH' : '🟢 OK'}
              </span>
            </div>
          </div>

          {/* Current */}
          <div className="p-4 rounded-lg bg-white border border-gray-200">
            <h4 className="text-sm font-semibold text-gray-600 mb-3">
              Current (A)
            </h4>
            <p className="text-3xl font-bold text-gray-900 mb-1">
              {realTimeData.sensor.current_a.toFixed(1)}
            </p>
            <div className="flex items-center justify-between text-xs text-gray-600">
              <span>Deviation: ±2%</span>
              <span>🟢 OK</span>
            </div>
          </div>
        </div>
      </div>

      {/* EXPLAINABILITY SECTION (XAI) */}
      <div className="bg-white p-6 rounded-lg border border-gray-200 mb-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-orange-600" />
          Why is this equipment at risk? (SHAP Explanation)
        </h2>

        {/* SHAP Contribution Bar */}
        <div className="mb-6">
          <p className="text-sm text-gray-700 mb-3">
            Anomaly Detection Factors (descending importance):
          </p>
          <div className="space-y-2">
            {realTimeData.explainability.top_factors.map(([factor, value], idx) => (
              <div key={idx} className="flex items-center gap-3">
                <span className="text-sm font-semibold w-24 text-gray-700 capitalize">
                  {factor}
                </span>
                <div className="flex-1 h-6 bg-gray-100 rounded overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-orange-400 to-red-600 flex items-center px-2"
                    style={{ width: `${Math.abs(value) * 100}%` }}
                  >
                    <span className="text-xs text-white font-semibold ml-auto">
                      {(Math.abs(value) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Historical Similar Pattern */}
        <div className="p-4 bg-blue-50 rounded border border-blue-300 mb-6">
          <p className="text-sm font-semibold text-gray-900 mb-2">
            📊 Similar Historical Pattern Found:
          </p>
          <p className="text-sm text-gray-700">
            <strong>Date:</strong> 2024-02-10 | 
            <strong className="ml-2">Similarity Score:</strong> {(realTimeData.explainability.historical_similar.similarity * 100).toFixed(0)}% | 
            <strong className="ml-2">Time to Failure:</strong> {realTimeData.explainability.historical_similar.time_to_failure_hours}h
          </p>
        </div>

        {/* Recommendation */}
        <div className="p-4 bg-yellow-50 rounded border border-yellow-300">
          <p className="text-sm font-semibold text-gray-900 mb-2">
            ✅ Recommended Action:
          </p>
          <div className="space-y-1 text-sm text-gray-700">
            <p><strong>Action:</strong> {realTimeData.recommendation.action}</p>
            <p><strong>Part Number:</strong> {realTimeData.recommendation.part_number}</p>
            <p><strong>Cost if Ignored:</strong> ${realTimeData.recommendation.cost_if_ignored}</p>
            <p><strong>Potential Downtime:</strong> {realTimeData.recommendation.downtime} hours</p>
          </div>
          <button className="mt-4 w-full bg-blue-600 text-white py-2 rounded font-semibold hover:bg-blue-700">
            📲 Send to Maintenance Team
          </button>
        </div>
      </div>

      {/* TREND CHARTS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        
        {/* Sensor Time-Series */}
        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-3">
            Vibration Trend (72 Hours)
          </h3>
          {/* Using Recharts or similar */}
          {/* Placeholder untuk chart */}
          <div className="h-40 bg-gray-100 rounded flex items-center justify-center">
            [Sensor time-series chart here - Recharts/Plotly]
          </div>
        </div>

        {/* RUL Projection */}
        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-3">
            RUL Projection (Next 30 Days)
          </h3>
          <div className="h-40 bg-gray-100 rounded flex items-center justify-center">
            [RUL forecast chart here]
          </div>
        </div>
      </div>

      {/* ALERT LOG */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Action Log</h2>
        <div className="space-y-2 text-sm">
          <p className="text-gray-700">
            <span className="text-gray-500">14:32</span> - Alert created: {selectedEquipment} anomaly detected
          </p>
          <p className="text-gray-700">
            <span className="text-gray-500">14:33</span> - SMS sent to Team Lead: Rudi
          </p>
          <p className="text-gray-700">
            <span className="text-gray-500">14:35</span> - WhatsApp notification: Team group
          </p>
        </div>
        <div className="flex gap-2 mt-4">
          <button className="px-3 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300">
            Export Log
          </button>
          <button className="px-3 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300">
            Download PDF
          </button>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
```

**Key Points:**
- ✓ WebSocket connection untuk real-time data
- ✓ SHAP values visualized sebagai bar chart
- ✓ RUL shown dengan confidence interval
- ✓ Recommendations konkrit dengan part number + cost
- ✓ CCP alerts prioritized
- ✓ Action log terintegrasi

---

## **B. DATA PIPELINE ISSUES**

### **Issue #3: Dataset Structure Disconnect**

Jika dataset kalian seperti ini:
```csv
timestamp,equipment_id,vibration,temperature,current,maintenance_date,failure_type,mtbf_hours,mttr_hours
2024-01-15 10:00,PUMP-01,9.2,67.3,12.1,2024-01-10,bearing_replacement,720,4
2024-01-15 10:05,PUMP-01,9.4,67.8,12.0,,,
2024-01-15 10:10,PUMP-01,10.1,68.2,12.2,,,
```

**Masalah:**
- ❌ Raw sensor data (continuous) tapi maintenance events (discrete)
- ❌ Gap antara "normal operations" dan "failure mode"
- ❌ Frontend perlu tahu: "Mana timestamp yang anomaly?" tapi model output hanya anomaly_score per row

**Solusi: Data Preprocessing Pipeline**

```python
# preprocessing.py

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

class DataPipeline:
    def __init__(self, raw_csv_path):
        self.df = pd.read_csv(raw_csv_path)
        self.scaler = StandardScaler()
        
    def create_sequences(self, data, window_size=60):
        """
        Convert raw sensor data into sequences untuk LSTM
        Input: [9.2, 9.4, 10.1, ..., 11.5]  (60 timesteps)
        Output: (60, 3) array untuk [vibration, temperature, current]
        """
        X, y = [], []
        for i in range(len(data) - window_size):
            X.append(data[i:i+window_size])
            y.append(data[i+window_size])
        return np.array(X), np.array(y)
    
    def prepare_training_data(self):
        """
        Prepare data untuk training anomaly detection + RUL model
        """
        # 1. Filter by equipment
        equipment_ids = self.df['equipment_id'].unique()
        
        train_data = {}
        for eq_id in equipment_ids:
            eq_df = self.df[self.df['equipment_id'] == eq_id].copy()
            
            # 2. Normalize sensor data
            sensor_cols = ['vibration', 'temperature', 'current']
            eq_df[sensor_cols] = self.scaler.fit_transform(eq_df[sensor_cols])
            
            # 3. Create label: 1 if failure in next 72 hours, else 0
            eq_df['failure_in_72h'] = 0
            for idx, row in eq_df.iterrows():
                if pd.notna(row['maintenance_date']):
                    time_diff = pd.to_datetime(row['maintenance_date']) - pd.to_datetime(row['timestamp'])
                    if time_diff.total_seconds() < 72*3600:
                        eq_df.loc[idx, 'failure_in_72h'] = 1
            
            # 4. Create sequences
            sensor_data = eq_df[sensor_cols].values
            X, y = self.create_sequences(sensor_data, window_size=60)
            
            # 5. Create RUL labels (hours to next failure)
            rul_labels = []
            for idx in range(len(eq_df)):
                remaining_time = 999  # Default: no failure
                for jdx, row in eq_df.iterrows():
                    if pd.notna(row['maintenance_date']) and jdx > idx:
                        remaining_time = min(remaining_time, 
                                           (pd.to_datetime(row['maintenance_date']) - 
                                            pd.to_datetime(eq_df.iloc[idx]['timestamp'])).total_seconds() / 3600)
                rul_labels.append(remaining_time)
            
            train_data[eq_id] = {
                'X': X,
                'y_anomaly': y[:len(X)],
                'y_rul': np.array(rul_labels[:len(X)]),
                'timestamps': eq_df['timestamp'].values[:len(X)]
            }
        
        return train_data
    
    def prepare_inference_data(self, recent_sensor_batch):
        """
        Untuk real-time inference
        recent_sensor_batch: last 60 timesteps dari WebSocket
        """
        sensor_df = pd.DataFrame(recent_sensor_batch)
        sensor_cols = ['vibration', 'temperature', 'current']
        
        # Normalize dengan training scaler
        sensor_df[sensor_cols] = self.scaler.transform(sensor_df[sensor_cols])
        
        # Format untuk model
        X_inference = sensor_df[sensor_cols].values.reshape(1, 60, 3)
        
        return X_inference

# Usage
pipeline = DataPipeline('kerry_sensor_data.csv')
train_data = pipeline.prepare_training_data()

# Train anomaly model
lstm_encoder = LSTMAutoencoder(input_dim=3, latent_dim=8)
lstm_encoder.fit(train_data['PUMP-01']['X'], epochs=50)

# Train RUL model
rul_transformer = TemporalFusionTransformer()
rul_transformer.fit(train_data['PUMP-01']['X'], 
                   train_data['PUMP-01']['y_rul'])
```

---

### **Issue #4: Synthetic Data Integration**

Jika historical data sparse, synthetic data penting tapi **HARUS coherent** dengan real data.

```python
# synthetic_data_augmentation.py

import numpy as np
from scipy.interpolate import interp1d

class SyntheticDataGenerator:
    """
    Generate synthetic degradation curves berdasarkan equipment manufacturer specs
    """
    
    def __init__(self, equipment_specs):
        self.specs = equipment_specs
        # Example: {'PUMP': {'ttf_mean': 720, 'ttf_std': 100, ...}}
    
    def generate_degradation_curve(self, equipment_type, num_samples=500):
        """
        Generate synthetic time-to-failure curve
        """
        ttf = np.random.normal(
            self.specs[equipment_type]['ttf_mean'],
            self.specs[equipment_type]['ttf_std'],
            num_samples
        )
        
        # Create degradation trajectory
        degradation = []
        for t in ttf:
            # S-curve: slow start → rapid degradation → failure
            time_points = np.linspace(0, t, 100)
            degradation_curve = 1 / (1 + np.exp(-(time_points - t/2) / (t/10)))
            degradation.append(degradation_curve)
        
        return np.array(degradation)
    
    def generate_sensor_signals(self, degradation_curve, equipment_type):
        """
        Map degradation curve ke sensor signals (vibration, temp, current)
        """
        vibration = degradation_curve * self.specs[equipment_type]['vib_max']
        temperature = 60 + degradation_curve * 30  # 60°C normal → 90°C failure
        current = 12 + degradation_curve * 3  # 12A normal → 15A failure
        
        # Add realistic noise
        vibration += np.random.normal(0, 0.5, vibration.shape)
        temperature += np.random.normal(0, 1.5, temperature.shape)
        current += np.random.normal(0, 0.3, current.shape)
        
        return vibration, temperature, current

# Usage
specs = {
    'PUMP': {'ttf_mean': 720, 'ttf_std': 100, 'vib_max': 15},
    'MIXER': {'ttf_mean': 600, 'ttf_std': 80, 'vib_max': 12},
    'SPRAY': {'ttf_mean': 480, 'ttf_std': 60, 'vib_max': 18},
}

generator = SyntheticDataGenerator(specs)
degradation = generator.generate_degradation_curve('PUMP', num_samples=100)
vib_syn, temp_syn, curr_syn = generator.generate_sensor_signals(
    degradation[0], 'PUMP'
)

# Combine real + synthetic
X_train = np.vstack([X_real, X_synthetic])
y_train = np.hstack([y_real, y_synthetic])
```

---

## **ACTIONABLE TO-DO LIST UNTUK FRONTEND FIX**

### **High Priority (Before Presentation - 30 June):**

- [ ] **Build XAI explanation component** 
  - SHAP bar chart visualization
  - Historical similar pattern display
  - Recommendation card dengan action details

- [ ] **Real-time sensor dashboard**
  - Multi-equipment selector
  - Gauge/progress bars untuk vibration, temp, current
  - Status indicator (Normal / Warning / Alert)

- [ ] **WebSocket integration**
  - Backend: Setup FastAPI WebSocket endpoint
  - Frontend: Implement React useEffect hook untuk WebSocket
  - Send real-time data every 5 seconds

- [ ] **CCP Alert prioritization UI**
  - Visual badge untuk CRITICAL vs HIGH
  - Auto-generate HACCP log entry

### **Medium Priority (Before Full Prototype - 31 July):**

- [ ] **Trend charts** (Recharts or Plotly)
  - 72-hour vibration trend
  - RUL projection (30-day forecast)
  - OEE trend

- [ ] **Alert history log**
  - Timestamp, action, recipient, status
  - Export PDF capability

- [ ] **Mobile responsive design**
  - Dashboard harus bisa di WhatsApp, tablet
  - Simplified alert view untuk mobile

### **Nice-to-Have (After MVP):**

- [ ] **Admin panel** untuk model retraining
- [ ] **Integration dengan ERP** untuk spare parts auto-order
- [ ] **Advanced analytics** (ML feature importance, model drift detection)

---

## **SUMMARY: FRONTEND RECOMMENDATIONS**

**Problem:** Frontend generic, tidak leverage unique ML outputs

**Solution:**
1. ✓ XAI explanation visual (SHAP bars + historical patterns)
2. ✓ Real-time WebSocket data pipeline
3. ✓ Multi-dimensional sensor visualization
4. ✓ CCP-aware alert system
5. ✓ Actionable recommendations (not just warnings)

**Target:** Dashboard yang bercerita data → insight → action → compliance

