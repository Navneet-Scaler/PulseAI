import random
from typing import Dict, Any, List

AUDITORS = ["Auditor_Sarah", "Auditor_John", "Auditor_Emma", "Auditor_David"]

class AuditorSimulator:
    def __init__(self, seed: int = 42):
        self.random = random.Random(seed)

    def review(self, encounter: Dict[str, Any], ai_prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate human auditor correcting codes and logging performance metrics.
        Human auditor corrects the AI coding if it differs from correct ground truth.
        """
        auditor = self.random.choice(AUDITORS)
        
        # Ground truth codes
        correct_icd = encounter["correct_icd10"]
        correct_cpt = encounter["correct_cpt"]
        
        # AI codes
        pred_icd = ai_prediction["predicted_icd10"]
        pred_cpt = ai_prediction["predicted_cpt"]
        
        # Check if correction is needed
        is_correct = (set(correct_icd) == set(pred_icd)) and (set(correct_cpt) == set(pred_cpt))
        
        decision = "agreed" if is_correct else "corrected"
        
        # Simulating time spent (seconds) based on encounter complexity
        specialty = encounter["specialty"]
        base_time = 90 if specialty in ["Cardiology", "Neurology"] else 45
        duration = int(base_time * self.random.uniform(0.6, 2.5))
        
        return {
            "auditor_id": auditor,
            "decision": decision,
            "final_icd10": correct_icd,
            "final_cpt": correct_cpt,
            "audit_duration_seconds": duration
        }
