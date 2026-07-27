import os
import sys
import numpy as np
from collections import namedtuple

# Add project path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.decision.engine import DecisionEngine

# Mock Motor
Motor = namedtuple('Motor', ['motor_id', 'name', 'location', 'nominal_rpm', 'nominal_current'])
mock_motor = Motor(motor_id="MTR-01", name="Conveyor Drive", location="Line 1", nominal_rpm=1500, nominal_current=22.0)

# Instantiate engine
engine = DecisionEngine(scaler_dir='models')

# Create a mock sequence with 120 steps and 25 features.
# Make the feature at index 0 (temp_mean) have a large positive value at the last step.
sequence = np.zeros((120, 25))
# Set temp_mean (index 0) to be large
sequence[-1, 0] = 5.0  # standard deviations away from normal

print("--- Testing Anomaly Detection without False Alarm suppression ---")
context_normal = {
    'shift': 'morning',
    'load_level': 'normal',
    'recently_maintained': False,
    'long_running': True,
    'sensor_malfunction': False,
    'ambient_shift': False,
    'in_transient_phase': False,
    'in_shift_handover': False
}

decision = engine.decide(
    motor=mock_motor,
    anomaly_score=0.95,
    fault_type='OR_007_6_1',
    rul_days=2.0,
    health_score=15.0,
    context=context_normal,
    sequence=sequence
)
print(f"Normal Context Severity: {decision['severity']}")
print(f"Normal Context Rec: {decision['recommendation']}")
print(f"Normal Context Cause: {decision['top_cause']}")
print("-" * 50)

# Test 1: Sensor Malfunction
print("\n--- Test 1: Sensor Malfunction ---")
context_malfunction = context_normal.copy()
context_malfunction['sensor_malfunction'] = True
context_malfunction['sensor_malfunction_reason'] = "Temperature sensor flatline detected at 85.0°C"

decision_mal = engine.decide(
    motor=mock_motor,
    anomaly_score=0.95,
    fault_type='OR_007_6_1',
    rul_days=2.0,
    health_score=15.0,
    context=context_malfunction,
    sequence=sequence
)
print(f"Malfunction Severity: {decision_mal['severity']}")
print(f"Malfunction Rec: {decision_mal['recommendation']}")
print(f"Malfunction Cause: {decision_mal['top_cause'].splitlines()[0]}")
assert decision_mal['severity'] == 'WARNING'
assert 'Sensor Fault' in decision_mal['top_cause']

# Test 2: Transient startup phase
print("\n--- Test 2: Transient Phase ---")
context_transient = context_normal.copy()
context_transient['in_transient_phase'] = True

# For transient phase, it checks features: Average Motor Current, Vibration RMS, Vibration Peak Acceleration.
# Let's make index 5 (vib_rms) the dominant feature.
seq_transient = np.zeros((120, 25))
seq_transient[-1, 5] = 5.0 # Vibration RMS

decision_trans = engine.decide(
    motor=mock_motor,
    anomaly_score=0.95,
    fault_type='OR_007_6_1',
    rul_days=2.0,
    health_score=15.0,
    context=context_transient,
    sequence=seq_transient
)
print(f"Transient Severity: {decision_trans['severity']}")
print(f"Transient Rec: {decision_trans['recommendation']}")
print(f"Transient Cause: {decision_trans['top_cause'].splitlines()[0]}")
assert decision_trans['severity'] == 'NORMAL'
assert 'start-up/stop' in decision_trans['recommendation'].lower()

# Test 3: Ambient Temperature Shift
print("\n--- Test 3: Ambient Temp Shift ---")
context_ambient = context_normal.copy()
context_ambient['ambient_shift'] = True

decision_amb = engine.decide(
    motor=mock_motor,
    anomaly_score=0.95,
    fault_type='OR_007_6_1',
    rul_days=2.0,
    health_score=15.0,
    context=context_ambient,
    sequence=sequence
)
print(f"Ambient Severity: {decision_amb['severity']}")
print(f"Ambient Rec: {decision_amb['recommendation']}")
print(f"Ambient Cause: {decision_amb['top_cause'].splitlines()[0]}")
assert decision_amb['severity'] == 'WARNING'
assert 'ambient temperature shift' in decision_amb['top_cause'].lower()

print("\nALL DECISION ENGINE TEST CASES PASSED SUCCESSFULLY!")
