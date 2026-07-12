import time
import requests
import sys

def run_replay(url: str, interval: float = 2.0, count: int = 20):
    print(f"Replaying simulation events against: {url}")
    print(f"Interval: {interval}s, Count: {count}")
    
    for i in range(count):
        try:
            r = requests.post(f"{url}/simulation/run")
            if r.status_code == 200:
                data = r.json()
                print(f"[{i+1}/{count}] Simulated: Encounter {data['encounter_id']} for specialty {data['encounter']['specialty']}. AI Confidence: {data['ai_prediction']['confidence_score']}. Decision: {data['ai_prediction']['action_taken']}. Status: {data['claim']['status']}")
            else:
                print(f"Error calling simulation endpoint: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"Connection failed: {e}")
            
        time.sleep(interval)

if __name__ == "__main__":
    api_url = "http://127.0.0.1:8000"
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    run_replay(api_url)
