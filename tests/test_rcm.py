import pytest
from datetime import date
from uuid import uuid4
from fastapi.testclient import TestClient

from src.core.generator import SyntheticDataGenerator
from src.core.ai_coder import AICoder
from src.core.auditor import AuditorSimulator
from src.core.denial_simulator import DenialSimulator
from src.schemas.validation import TelemetryEvent, EventType
from src.api.main import app

client = TestClient(app)

def test_generator_seeding():
    g1 = SyntheticDataGenerator(seed=42)
    g2 = SyntheticDataGenerator(seed=42)
    enc1 = g1.generate_encounter("ENC_1", date(2026, 7, 1))
    enc2 = g2.generate_encounter("ENC_1", date(2026, 7, 1))
    
    assert enc1["patient_id"] == enc2["patient_id"]
    assert enc1["specialty"] == enc2["specialty"]
    assert enc1["charge_amount"] == enc2["charge_amount"]

def test_ai_coder_prediction():
    coder = AICoder(seed=42)
    encounter = {
        "specialty": "Cardiology",
        "correct_icd10": ["I20.9", "R07.9"],
        "correct_cpt": ["93000", "99214"]
    }
    pred = coder.predict(encounter)
    assert "ai_model_version" in pred
    assert "predicted_icd10" in pred
    assert 0.0 <= pred["confidence_score"] <= 1.0

def test_denial_simulator():
    sim = DenialSimulator(seed=12)
    encounter = {
        "payer_id": "Payer_Medicare",
        "charge_amount": 100.0,
        "correct_icd10": ["I20.9"],
        "correct_cpt": ["93000"]
    }
    
    # Matching codes -> should have a probability of payment
    res = sim.process_claim(encounter, ["I20.9"], ["93000"])
    assert res["status"] in ["paid", "denied"]
    if res["status"] == "paid":
        assert res["paid_amount"] > 0
    else:
        assert res["paid_amount"] == 0

def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
