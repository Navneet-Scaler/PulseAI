import os
import sqlite3
import json
from datetime import datetime, date
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from src.schemas.validation import TelemetryEvent, EventType, EncounterPayload, AICodingPayload, AuditorReviewPayload, ClaimSubmittedPayload, PayerRespondedPayload
from src.core.generator import SyntheticDataGenerator
from src.core.ai_coder import AICoder
from src.core.auditor import AuditorSimulator
from src.core.denial_simulator import DenialSimulator

app = FastAPI(title="Pulse AI RCM Telemetry API", version="1.0.0")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(PROJECT_ROOT, 'pulse_ai.db')}").replace("sqlite:///", "")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Initialize DB on startup
@app.on_event("startup")
def startup_db():
    schema_path = os.path.join(os.path.dirname(__file__), "../../sql/schema.sql")
    if os.path.exists(schema_path):
        with open(schema_path, "r") as f:
            schema = f.read()
        conn = sqlite3.connect(DB_PATH)
        conn.executescript(schema)
        conn.close()

class InferenceRequest(BaseModel):
    specialty: str
    symptoms: str
    clinical_notes: str
    correct_icd10: List[str]
    correct_cpt: List[str]

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/inference")
def get_inference(req: InferenceRequest):
    ai_coder = AICoder(seed=int(datetime.utcnow().timestamp()))
    encounter = {
        "specialty": req.specialty,
        "correct_icd10": req.correct_icd10,
        "correct_cpt": req.correct_cpt
    }
    prediction = ai_coder.predict(encounter)
    return prediction

@app.post("/telemetry")
def log_telemetry(event: TelemetryEvent, db = Depends(get_db)):
    cursor = db.cursor()
    try:
        payload_data = event.payload
        
        if event.event_type == EventType.ENCOUNTER_REGISTERED:
            cursor.execute(
                """INSERT OR REPLACE INTO encounters 
                   (encounter_id, patient_id, specialty, visit_date, symptoms, clinical_notes, correct_icd10, correct_cpt, charge_amount, payer_id) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.encounter_id,
                    payload_data.patient_id,
                    payload_data.specialty,
                    str(payload_data.visit_date),
                    payload_data.symptoms,
                    payload_data.clinical_notes,
                    json.dumps(payload_data.dict().get("correct_icd10", [])),
                    json.dumps(payload_data.dict().get("correct_cpt", [])),
                    payload_data.dict().get("charge_amount", 0.0),
                    payload_data.dict().get("payer_id", "Payer_Default")
                )
            )
        elif event.event_type == EventType.AI_CODING_PROCESSED:
            cursor.execute(
                """INSERT OR REPLACE INTO ai_coding_logs 
                   (encounter_id, ai_model_version, predicted_icd10, predicted_cpt, confidence_score, action_taken, processed_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.encounter_id,
                    payload_data.ai_model_version,
                    json.dumps(payload_data.predicted_icd10),
                    json.dumps(payload_data.predicted_cpt),
                    payload_data.confidence_score,
                    payload_data.action_taken,
                    event.timestamp.isoformat()
                )
            )
        elif event.event_type == EventType.AUDITOR_REVIEWED:
            cursor.execute(
                """INSERT OR REPLACE INTO audit_logs 
                   (encounter_id, auditor_id, decision, final_icd10, final_cpt, audit_duration_seconds, reviewed_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.encounter_id,
                    payload_data.auditor_id,
                    payload_data.decision,
                    json.dumps(payload_data.final_icd10),
                    json.dumps(payload_data.final_cpt),
                    payload_data.audit_duration_seconds,
                    event.timestamp.isoformat()
                )
            )
        elif event.event_type == EventType.PAYER_RESPONDED:
            cursor.execute(
                """INSERT OR REPLACE INTO claims 
                   (encounter_id, payer_id, status, denial_reason, allowed_amount, paid_amount, submitted_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.encounter_id,
                    payload_data.payer_id,
                    payload_data.status,
                    payload_data.denial_reason,
                    payload_data.allowed_amount,
                    payload_data.paid_amount,
                    event.timestamp.isoformat()
                )
            )
            
        db.commit()
        return {"status": "success", "event_id": str(event.event_id)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simulation/run")
def run_simulation_step(db = Depends(get_db)):
    """
    Run one complete cycle: generate encounter, predict, audit if needed, process claim.
    """
    ts = datetime.utcnow()
    seed = int(ts.timestamp() * 1000) % 100000
    generator = SyntheticDataGenerator(seed=seed)
    ai_coder = AICoder(seed=seed)
    auditor_sim = AuditorSimulator(seed=seed)
    denial_sim = DenialSimulator(seed=seed)
    
    # 1. Generate encounter
    encounter_id = f"ENC_{uuid4().hex[:8].upper()}"
    encounter = generator.generate_encounter(encounter_id, date.today())
    
    # Write encounter to DB
    cursor = db.cursor()
    cursor.execute(
        """INSERT INTO encounters 
           (encounter_id, patient_id, specialty, visit_date, symptoms, clinical_notes, correct_icd10, correct_cpt, charge_amount, payer_id) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            encounter_id,
            encounter["patient_id"],
            encounter["specialty"],
            str(encounter["visit_date"]),
            encounter["symptoms"],
            encounter["clinical_notes"],
            json.dumps(encounter["correct_icd10"]),
            json.dumps(encounter["correct_cpt"]),
            encounter["charge_amount"],
            encounter["payer_id"]
        )
    )
    
    # 2. AI Coding
    ai_pred = ai_coder.predict(encounter)
    cursor.execute(
        """INSERT INTO ai_coding_logs 
           (encounter_id, ai_model_version, predicted_icd10, predicted_cpt, confidence_score, action_taken, processed_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            encounter_id,
            ai_pred["ai_model_version"],
            json.dumps(ai_pred["predicted_icd10"]),
            json.dumps(ai_pred["predicted_cpt"]),
            ai_pred["confidence_score"],
            ai_pred["action_taken"],
            ts.isoformat()
        )
    )
    
    # 3. Audit if routed
    final_icd = ai_pred["predicted_icd10"]
    final_cpt = ai_pred["predicted_cpt"]
    audit_data = None
    
    if ai_pred["action_taken"] == "routed_to_audit":
        audit_data = auditor_sim.review(encounter, ai_pred)
        final_icd = audit_data["final_icd10"]
        final_cpt = audit_data["final_cpt"]
        cursor.execute(
            """INSERT INTO audit_logs 
               (encounter_id, auditor_id, decision, final_icd10, final_cpt, audit_duration_seconds, reviewed_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                encounter_id,
                audit_data["auditor_id"],
                audit_data["decision"],
                json.dumps(final_icd),
                json.dumps(final_cpt),
                audit_data["audit_duration_seconds"],
                ts.isoformat()
            )
        )
        
    # 4. Payer Processing
    claim_res = denial_sim.process_claim(encounter, final_icd, final_cpt)
    cursor.execute(
        """INSERT INTO claims 
           (encounter_id, payer_id, status, denial_reason, allowed_amount, paid_amount, submitted_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            encounter_id,
            claim_res["payer_id"],
            claim_res["status"],
            claim_res["denial_reason"],
            claim_res["allowed_amount"],
            claim_res["paid_amount"],
            ts.isoformat()
        )
    )
    
    db.commit()
    
    return {
        "encounter_id": encounter_id,
        "encounter": encounter,
        "ai_prediction": ai_pred,
        "audit": audit_data,
        "claim": claim_res
    }
