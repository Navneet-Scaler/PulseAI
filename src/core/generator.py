import random
from datetime import date, timedelta
from typing import Dict, Any, List

SPECIALTIES_DATA = {
    "Cardiology": [
        {
            "symptoms": "Chest pain radiating to the left arm, shortness of breath, palpitations.",
            "clinical_notes": "Patient presents with acute onset retrosternal chest pressure. ECG shows minor ST changes. Troponin level ordered.",
            "correct_icd10": ["I20.9", "R07.9"],  # Angina, Chest pain
            "correct_cpt": ["93000", "99214"],    # ECG, Office visit level 4
            "avg_charge": 1200.00
        },
        {
            "symptoms": "Shortness of breath on exertion, bilateral ankle swelling.",
            "clinical_notes": "History of congestive heart failure. Mild jugular venous distention present. Prescribed increased dose of Furosemide.",
            "correct_icd10": ["I50.9"],           # Heart failure
            "correct_cpt": ["99213", "93306"],    # Office visit level 3, Echocardiogram
            "avg_charge": 2500.00
        }
    ],
    "Orthopedics": [
        {
            "symptoms": "Right knee pain after twisting it during a soccer match. Inability to bear weight fully.",
            "clinical_notes": "Positive McMurray test. Mild joint effusion noted. Patient referred for MRI of the right knee.",
            "correct_icd10": ["M23.22", "S83.241A"], # Meniscus tear, Tear of lateral meniscus
            "correct_cpt": ["99213", "73562"],    # Office visit level 3, X-ray knee
            "avg_charge": 450.00
        },
        {
            "symptoms": "Chronic lower back pain radiating down the right thigh.",
            "clinical_notes": "Lasegue sign positive on right side. L4-L5 radiculopathy suspected. Scheduled for physical therapy.",
            "correct_icd10": ["M54.5", "M54.16"], # Low back pain, Lumbar radiculopathy
            "correct_cpt": ["99214", "97110"],    # Office visit level 4, Therapeutic exercises
            "avg_charge": 350.00
        }
    ],
    "Neurology": [
        {
            "symptoms": "Severe throbbing unilateral headache accompanied by nausea and photophobia.",
            "clinical_notes": "Patient reports 3 episodes per week. Symptoms resolved with triptans in past. Neurological exam normal.",
            "correct_icd10": ["G43.909"],          # Migraine without aura
            "correct_cpt": ["99213"],             # Office visit level 3
            "avg_charge": 200.00
        },
        {
            "symptoms": "Sudden onset of numbness in the left arm and leg lasting for about 45 minutes, now resolved.",
            "clinical_notes": "Transient ischemic attack suspected. Patient started on baby Aspirin daily. Carotid ultrasound scheduled.",
            "correct_icd10": ["G45.9"],           # Transient cerebral ischemic attack
            "correct_cpt": ["99214", "93880"],    # Office visit level 4, Carotid duplex scan
            "avg_charge": 1500.00
        }
    ],
    "General Medicine": [
        {
            "symptoms": "High grade fever, dry cough, sore throat, generalized body aches.",
            "clinical_notes": "Vitals show T 102F, BP 120/80. Chest clear to auscultation. Flu swab positive for Influenza A.",
            "correct_icd10": ["J11.1"],           # Influenza due to unidentified influenza virus
            "correct_cpt": ["99213", "87804"],    # Office visit level 3, Flu test
            "avg_charge": 180.00
        },
        {
            "symptoms": "Polyuria, polydipsia, fatigue.",
            "clinical_notes": "Routine lab work shows HbA1c of 8.5%. Patient educated on lifestyle modifications and Metformin started.",
            "correct_icd10": ["E11.9"],           # Type 2 diabetes mellitus without complications
            "correct_cpt": ["99214", "83036"],    # Office visit level 4, HbA1c test
            "avg_charge": 220.00
        }
    ]
}

PAYERS = ["Payer_BlueCross", "Payer_Aetna", "Payer_UnitedHealth", "Payer_Medicare"]

class SyntheticDataGenerator:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.random = random.Random(seed)

    def generate_encounter(self, encounter_id: str, visit_date: date) -> Dict[str, Any]:
        specialty = self.random.choice(list(SPECIALTIES_DATA.keys()))
        case = self.random.choice(SPECIALTIES_DATA[specialty])
        
        patient_id = f"PAT_{self.random.randint(10000, 99999)}"
        payer = self.random.choice(PAYERS)
        
        # Add some random noise or variance to charge amount
        charge = round(case["avg_charge"] * self.random.uniform(0.9, 1.1), 2)
        
        return {
            "encounter_id": encounter_id,
            "patient_id": patient_id,
            "specialty": specialty,
            "visit_date": visit_date,
            "symptoms": case["symptoms"],
            "clinical_notes": case["clinical_notes"],
            "correct_icd10": case["correct_icd10"],
            "correct_cpt": case["correct_cpt"],
            "payer_id": payer,
            "charge_amount": charge
        }

    def generate_batch(self, start_date: date, count: int) -> List[Dict[str, Any]]:
        batch = []
        for i in range(count):
            enc_id = f"ENC_{start_date.strftime('%Y%m%d')}_{1000 + i}"
            visit_date = start_date + timedelta(days=self.random.randint(-30, 0))
            batch.append(self.generate_encounter(enc_id, visit_date))
        return batch
