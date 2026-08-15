import os
import sys
# pyrefly: ignore [missing-import]
import joblib
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import src.api.local_config
except ImportError:
    pass

from src.pipeline.sequence import FEATURE_COLS

def train_model():
    print("[Model A2] Starting Fault Classification Gradient Boosting Classifier training...")
    
    DB_HOST = os.getenv("ASTRA_DB_HOST", "localhost")
    DB_PORT = int(os.getenv("ASTRA_DB_PORT", "5432"))
    DB_USER = os.getenv("ASTRA_DB_USER", "rasyaad")
    DB_PASSWORD = os.getenv("ASTRA_DB_PASSWORD", "Sellevolerei1")
    DB_NAME = "astra_predictive_maintenance"
    
    engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
    
    # Query feature windows for the bearing motors (MTR-01, MTR-02, MTR-03, MTR-06)
    query = """
        SELECT * FROM feature_windows 
        WHERE motor_id IN ('MTR-01', 'MTR-02', 'MTR-03', 'MTR-06') 
        ORDER BY window_end ASC
    """
    df = pd.read_sql(query, engine)
    
    if len(df) == 0:
        print("[Model A2] No feature windows found for bearing classification.")
        return
        
    print(f"[Model A2] Loaded {len(df)} feature windows.")
    
    # Map motor_id to class label
    label_map = {
        'MTR-01': 'healthy',
        'MTR-02': 'outer_race',
        'MTR-03': 'inner_race',
        'MTR-06': 'roller'
    }
    df['fault_type'] = df['motor_id'].map(label_map)
    
    # Exclude rows with NaN values in target features
    df_clean = df.dropna(subset=FEATURE_COLS).copy()
    
    X = df_clean[FEATURE_COLS].values
    y = df_clean['fault_type'].values
    
    # Encode target labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    print(f"[Model A2] Data distribution: {df_clean['fault_type'].value_value_counts() if hasattr(df_clean['fault_type'], 'value_value_counts') else pd.Series(y).value_counts().to_dict()}")
    
    # Chronological/stratified split per class to make sure every class is represented in train/test
    # Since we have time-series, let's take first 80% of each motor's windows as train, and last 20% as test
    train_indices = []
    test_indices = []
    
    for motor in ['MTR-01', 'MTR-02', 'MTR-03', 'MTR-06']:
        motor_idx = df_clean[df_clean['motor_id'] == motor].index.tolist()
        split_point = int(len(motor_idx) * 0.8)
        train_indices.extend(motor_idx[:split_point])
        test_indices.extend(motor_idx[split_point:])
        
    # Translate indices back to array indices
    df_clean['original_index'] = range(len(df_clean))
    train_arr_idx = df_clean.loc[train_indices, 'original_index'].values
    test_arr_idx = df_clean.loc[test_indices, 'original_index'].values
    
    X_train, y_train = X[train_arr_idx], y_encoded[train_arr_idx]
    X_test, y_test = X[test_arr_idx], y_encoded[test_arr_idx]
    
    print(f"[Model A2] Split: Train size = {len(X_train)}, Test size = {len(X_test)}")
    
    # Train Gradient Boosting Classifier
    model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    
    # Evaluate
    print("\n--- Classification Report ---")
    print(classification_report(y_test, y_pred, target_names=le.classes_))
    
    print("--- Confusion Matrix ---")
    print(confusion_matrix(y_test, y_pred))
    
    # Feature importances
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    print("\n--- Top 10 Most Important Features ---")
    for i in range(min(10, len(FEATURE_COLS))):
        print(f"{i+1}. {FEATURE_COLS[indices[i]]}: {importances[indices[i]]:.4f}")
        
    # Save Model & Label Encoder
    os.makedirs('models', exist_ok=True)
    joblib.dump(model, 'models/model_a2_v1.pkl')
    joblib.dump(le, 'models/label_encoder_a2.pkl')
    print("\n[Model A2] Model saved to 'models/model_a2_v1.pkl' and label encoder saved to 'models/label_encoder_a2.pkl'.")

if __name__ == '__main__':
    train_model()
