import requests
import json

def verify():
    url = "http://localhost:8000/api/predict/inference"
    payload = {
        "vibration_rms": 0.24,
        "motor_current": 1.25,
        "temperature": 82.4,
        "flow_rate": 200.0
    }
    
    print("Making request to:", url)
    print("Payload:", json.dumps(payload, indent=2))
    
    try:
        res = requests.post(url, json=payload)
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print("Response:")
            print(json.dumps(data, indent=2))
            rul_hours = data.get("rul_hours", 0)
            if rul_hours > 0:
                print(f"\nSUCCESS: RUL estimate is non-zero: {rul_hours}h!")
            else:
                print("\nFAILURE: RUL estimate is 0h!")
        else:
            print(f"Error Response: {res.text}")
    except Exception as e:
        print(f"Error making request: {e}")

if __name__ == "__main__":
    verify()
