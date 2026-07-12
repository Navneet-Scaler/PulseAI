import os
import sqlite3
import json
import random
from datetime import datetime, date, timedelta
from uuid import uuid4

from src.core.generator import SyntheticDataGenerator
from src.core.ai_coder import AICoder
from src.core.auditor import AuditorSimulator
from src.core.denial_simulator import DenialSimulator

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(PROJECT_ROOT, "pulse_ai.db")

def run_backfill(num_days: int = 30, events_per_day: int = 85):
    print(f"Starting backfill for the last {num_days} days. Total target: {num_days * events_per_day} encounters.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Initialize schema
    schema_path = os.path.join(os.path.dirname(__file__), "../../sql/schema.sql")
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Database schema file not found at: {schema_path}")
        
    with open(schema_path, "r") as f:
        schema = f.read()
    cursor.executescript(schema)
        
    start_date = date.today() - timedelta(days=num_days)
    
    generator = SyntheticDataGenerator(seed=1337)
    # Generate different versions of coder for A/B testing dashboard later:
    # A/B test: v1 (Traditional / older model) vs v2 (Advanced coder)
    # v1 will have slightly higher errors and lower confidence
    ai_coder_v1 = AICoder(model_version="PulseCoder-v1.8", seed=101)
    ai_coder_v2 = AICoder(model_version="PulseCoder-v2.1", seed=202)
    
    auditor_sim = AuditorSimulator(seed=303)
    denial_sim = DenialSimulator(seed=404)
    
    total_inserted = 0
    
    for day in range(num_days):
        current_date = start_date + timedelta(days=day)
        print(f"Backfilling date: {current_date}")
        
        for i in range(events_per_day):
            encounter_id = f"ENC_{current_date.strftime('%Y%m%d')}_{1000 + i}"
            encounter = generator.generate_encounter(encounter_id, current_date)
            
            # Insert encounter
            cursor.execute(
                """INSERT OR REPLACE INTO encounters 
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
            
            # Select model version (A/B Test assignment)
            # 50/50 split between Model V1 and Model V2
            is_group_a = random.choice([True, False])
            coder = ai_coder_v1 if is_group_a else ai_coder_v2
            
            ai_pred = coder.predict(encounter)
            
            processed_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=random.randint(8, 17))
            
            cursor.execute(
                """INSERT OR REPLACE INTO ai_coding_logs 
                   (encounter_id, ai_model_version, predicted_icd10, predicted_cpt, confidence_score, action_taken, processed_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    encounter_id,
                    ai_pred["ai_model_version"],
                    json.dumps(ai_pred["predicted_icd10"]),
                    json.dumps(ai_pred["predicted_cpt"]),
                    ai_pred["confidence_score"],
                    ai_pred["action_taken"],
                    processed_time.isoformat()
                )
            )
            
            final_icd = ai_pred["predicted_icd10"]
            final_cpt = ai_pred["predicted_cpt"]
            
            if ai_pred["action_taken"] == "routed_to_audit":
                audit_data = auditor_sim.review(encounter, ai_pred)
                final_icd = audit_data["final_icd10"]
                final_cpt = audit_data["final_cpt"]
                cursor.execute(
                    """INSERT OR REPLACE INTO audit_logs 
                       (encounter_id, auditor_id, decision, final_icd10, final_cpt, audit_duration_seconds, reviewed_at) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        encounter_id,
                        audit_data["auditor_id"],
                        audit_data["decision"],
                        json.dumps(final_icd),
                        json.dumps(final_cpt),
                        audit_data["audit_duration_seconds"],
                        (processed_time + timedelta(minutes=random.randint(5, 60))).isoformat()
                    )
                )
                
            claim_res = denial_sim.process_claim(encounter, final_icd, final_cpt)
            cursor.execute(
                """INSERT OR REPLACE INTO claims 
                   (encounter_id, payer_id, status, denial_reason, allowed_amount, paid_amount, submitted_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    encounter_id,
                    claim_res["payer_id"],
                    claim_res["status"],
                    claim_res["denial_reason"],
                    claim_res["allowed_amount"],
                    claim_res["paid_amount"],
                    (processed_time + timedelta(hours=random.randint(12, 48))).isoformat()
                )
            )
            
            total_inserted += 1
            
    conn.commit()
    conn.close()
    print(f"Backfill successfully completed! Created {total_inserted} claims database records.")

if __name__ == "__main__":
    run_backfill()
