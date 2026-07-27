# PredictaGuard — ML Pipeline

AI predictive maintenance pipeline for Kerry Group manufacturing equipment.

## Requirements

- Python 3.12.x
- Windows 11 / Linux / macOS

## Setup

```bash
# 1. Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
```

## Project Structure

```
ml/
├── requirements.txt          # Pinned dependencies
├── src/
│   ├── eda/                  # Standalone EDA scripts
│   │   ├── eda_skab.py
│   │   ├── eda_cwru.py
│   │   └── eda_cmapss.py
│   ├── preprocessing/        # Preprocessing pipelines
│   │   ├── preprocess_skab.py
│   │   ├── preprocess_cwru.py
│   │   └── preprocess_cmapss.py
│   ├── synthetic/            # Synthetic Kerry equipment data generation
│   │   └── generate_kerry_data.py
│   ├── models/                # Model training (3 candidates trained per task)
│   │   ├── train_anomaly_detection.py      # SKAB: IsolationForest / RandomForest / MLP
│   │   ├── train_fault_classification.py   # CWRU: RandomForest / HistGradientBoosting / MLP
│   │   └── train_rul_prediction.py         # CMAPSS: RandomForest / HistGradientBoosting / MLP
│   ├── evaluation/            # Model evaluation & explainability
│   │   ├── evaluate_all.py            # Generates metrics + plots for all 3 tasks
│   │   ├── shap_explainability.py     # SHAP global/local explanations
│   │   └── demo_streaming.py          # CLI demo of the streaming pipeline
│   └── api/                   # FastAPI backend (serves API + dashboard)
│       ├── main.py            # Routes
│       ├── predictor.py       # Model loading & inference
│       ├── simulator.py       # Live equipment status / alert simulation
│       ├── schemas.py         # Pydantic request/response models
│       └── stream_buffer.py   # Per-machine rolling-window streaming buffer
├── data/
│   ├── processed/             # Preprocessed arrays (.npz), scalers (.joblib), EDA plots
│   │                          #   (arrays/scalers are gitignored — regenerate via preprocessing scripts)
│   └── synthetic/              # Generated Kerry equipment CSVs (gitignored — regenerate via generate_kerry_data.py)
├── models/                     # Trained model artifacts (gitignored — regenerate via training scripts)
│   └── evaluation/             # Metrics (JSON) + plots (tracked in git)
└── docs/
    ├── data_dictionary.md            # Full feature reference
    └── dataset_kerry_mapping.md      # Source-to-Kerry signal mapping
```

## Running the Pipeline

All scripts are run from the `ml/` directory:

```bash
cd d:/Kerry/ml

# EDA
python -X utf8 src/eda/eda_skab.py
python -X utf8 src/eda/eda_cwru.py
python -X utf8 src/eda/eda_cmapss.py

# Preprocessing
python -X utf8 src/preprocessing/preprocess_skab.py
python -X utf8 src/preprocessing/preprocess_cwru.py
python -X utf8 src/preprocessing/preprocess_cmapss.py

# Synthetic Kerry equipment data
python -X utf8 src/synthetic/generate_kerry_data.py

# Model training
python -X utf8 src/models/train_anomaly_detection.py
python -X utf8 src/models/train_fault_classification.py
python -X utf8 src/models/train_rul_prediction.py

# Evaluation & explainability
python -X utf8 src/evaluation/evaluate_all.py
python -X utf8 src/evaluation/shap_explainability.py
```

Note: `-X utf8` is required on Windows to avoid `cp1252` encoding errors in console output.

## Running the API + Dashboard

```bash
cd d:/Kerry/ml
python -X utf8 -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

- Dashboard: http://localhost:8000/
- Interactive API docs: http://localhost:8000/docs

### Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/health` | Model load status |
| `POST /api/predict/inference` | Run inference from slider values (vibration, current, temp, flow) — returns risk, SHAP explanation, historical match, recommendation, and CCP alert |
| `GET /api/equipment/status` | Live equipment status from the simulator |
| `GET /api/alerts` | Active alerts from the simulator |
| `GET /api/simulate/step` | Advance the simulation cursor |
| `POST /api/stream/ingest` | Ingest one per-second sensor reading into a machine's rolling window; triggers inference automatically every N readings |
| `GET /api/stream/status/{machine_id}` | Current rolling-window state, latest prediction, and risk-level trend for a machine |
| `GET /api/stream/config` | Per-equipment streaming config (window size, stride, CCP flag) |

Streaming stride is tuned per equipment: CCP stages (mixer, pasteurizer) predict every 5s for fast food-safety detection; non-CCP equipment (compressor, spray dryer) predicts every 30s since degradation is gradual.

## Datasets

Raw datasets are **not tracked in this repo** (see root `.gitignore`) — download from their original sources and place under `../dataset/`:

| Dataset | Location | Role |
|---|---|---|
| SKAB | `../dataset/SCAB/` | Anomaly detection, sensor simulation |
| CWRU | `../dataset/CWRU/` | Bearing fault classification |
| NASA CMAPSS | `../dataset/CMaps/` | Remaining Useful Life (RUL) prediction |

## Model Results

3 candidate models are trained per task; the best is selected per the metric below.

| Task | Dataset | Best Model | Key Metric |
|---|---|---|---|
| Anomaly Detection | SKAB | RandomForestClassifier | F1 = 0.913, ROC-AUC = 0.938, Precision(anomaly) = 1.00 |
| Fault Classification | CWRU | MLPClassifier | Accuracy = 0.934, Macro F1 = 0.933 (10 classes) |
| RUL Prediction | CMAPSS FD001 | MLPRegressor | RMSE = 14.15 cycles, MAE = 10.24, R² = 0.773, NASA score = 46,481 |

Full metrics: [models/evaluation/summary_report.json](models/evaluation/summary_report.json). Plots: [models/evaluation/](models/evaluation/).

## Outputs (gitignored, regenerate locally)

- `data/processed/*.npz`, `data/processed/*.joblib` — preprocessed arrays & scalers
- `data/synthetic/*.csv` — synthetic Kerry equipment data (pump, mixer, compressor, spray dryer)
- `models/*.joblib` — trained model artifacts

`data/processed/eda_plots/` and `models/evaluation/` (plots + metrics JSON) are tracked in git since they're small and demonstrate results directly.
