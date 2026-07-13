from datetime import date, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api import main as api_main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Redirect the API at a scratch database so these tests never touch the
    # real pulse_ai.db used by the Streamlit dashboard.
    test_db = tmp_path / "test_pulse.db"
    monkeypatch.setattr(api_main, "DB_PATH", str(test_db))
    api_main.startup_db()
    return TestClient(api_main.app)


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_inference_endpoint_returns_valid_prediction(client):
    payload = {
        "specialty": "Cardiology",
        "symptoms": "Chest pain radiating to the left arm.",
        "clinical_notes": "Acute onset retrosternal chest pressure.",
        "correct_icd10": ["I20.9"],
        "correct_cpt": ["93000"]
    }
    res = client.post("/inference", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert 0.0 <= body["confidence_score"] <= 1.0
    assert body["action_taken"] in ("auto_billed", "routed_to_audit")


def test_simulation_run_writes_full_pipeline(client):
    res = client.post("/simulation/run")
    assert res.status_code == 200
    body = res.json()
    assert body["encounter_id"].startswith("ENC_")
    assert body["claim"]["status"] in ("paid", "denied")

    # The encounter should now be queryable back out of the scratch DB.
    follow_up = client.post("/simulation/run")
    assert follow_up.status_code == 200
    assert follow_up.json()["encounter_id"] != body["encounter_id"]


def test_telemetry_encounter_registered_persists(client):
    event = {
        "event_id": str(uuid4()),
        "event_type": "encounter_registered",
        "timestamp": datetime.utcnow().isoformat(),
        "encounter_id": "ENC_TEST_1",
        "payload": {
            "patient_id": "PAT_1",
            "specialty": "Cardiology",
            "visit_date": str(date.today()),
            "symptoms": "chest pain",
            "clinical_notes": "notes"
        }
    }
    res = client.post("/telemetry", json=event)
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_telemetry_rejects_invalid_confidence_score(client):
    event = {
        "event_id": str(uuid4()),
        "event_type": "ai_coding_processed",
        "timestamp": datetime.utcnow().isoformat(),
        "encounter_id": "ENC_TEST_2",
        "payload": {
            "ai_model_version": "PulseCoder-v2.1",
            "predicted_icd10": ["I20.9"],
            "predicted_cpt": ["93000"],
            "confidence_score": 1.5,
            "action_taken": "auto_billed"
        }
    }
    res = client.post("/telemetry", json=event)
    assert res.status_code == 422
