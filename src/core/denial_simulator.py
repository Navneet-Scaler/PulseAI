import random
from typing import Dict, Any, List

DENIAL_REASONS = [
    "Medical Necessity Mismatch",
    "Missing Modifier",
    "Prior Authorization Required",
    "Incorrect Coding Mismatch",
    "Coordination of Benefits",
    "Duplicate Claim"
]

class DenialSimulator:
    def __init__(self, seed: int = 42):
        self.random = random.Random(seed)

    def process_claim(self, encounter: Dict[str, Any], final_icd10: List[str], final_cpt: List[str]) -> Dict[str, Any]:
        """
        Simulate payer process. Evaluates correctness and decides paid vs denied status.
        """
        payer = encounter["payer_id"]
        charge = encounter["charge_amount"]
        
        # Check if the final codes match correct codes
        correct_icd = encounter["correct_icd10"]
        correct_cpt = encounter["correct_cpt"]
        
        is_coding_correct = (set(correct_icd) == set(final_icd10)) and (set(correct_cpt) == set(final_cpt))
        
        status = "paid"
        denial_reason = None
        allowed_amount = 0.0
        paid_amount = 0.0
        
        if not is_coding_correct:
            # Coding error bypassed audit! Extremely high chance of denial
            if self.random.random() < 0.90:
                status = "denied"
                denial_reason = "Incorrect Coding Mismatch"
            else:
                status = "paid"
        else:
            # Random baseline denials (payer friction)
            # Medicare denies less than commercial payers generally
            denial_prob = 0.15 if payer == "Payer_Medicare" else 0.22
            
            if self.random.random() < denial_prob:
                status = "denied"
                denial_reason = self.random.choice([
                    "Medical Necessity Mismatch",
                    "Missing Modifier",
                    "Prior Authorization Required",
                    "Coordination of Benefits",
                    "Duplicate Claim"
                ])
                
        if status == "paid":
            # Allowed amount is a fraction of charge (e.g. contract rate)
            allowed_rate = self.random.uniform(0.60, 0.85)
            allowed_amount = round(charge * allowed_rate, 2)
            # Paid amount is mostly close to allowed amount
            paid_amount = round(allowed_amount * self.random.uniform(0.95, 1.0), 2)
        else:
            # Denied claim
            allowed_amount = 0.0
            paid_amount = 0.0
            
        return {
            "payer_id": payer,
            "status": status,
            "denial_reason": denial_reason,
            "allowed_amount": allowed_amount,
            "paid_amount": paid_amount
        }
