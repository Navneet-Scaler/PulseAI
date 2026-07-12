import random
from typing import Dict, Any, List, Tuple

class AICoder:
    def __init__(self, model_version: str = "PulseCoder-v2.1", seed: int = 42):
        self.model_version = model_version
        self.random = random.Random(seed)

    def predict(self, encounter: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate AI predicting ICD-10 and CPT codes based on correct answers.
        We inject error and confidence scores:
        - High confidence (>0.70): mostly correct.
        - Low confidence (<0.70): higher chance of error.
        """
        correct_icd = encounter["correct_icd10"]
        correct_cpt = encounter["correct_cpt"]
        specialty = encounter["specialty"]
        
        # Determine baseline difficulty by specialty
        # Cardiology/Neurology are more complex than General Med
        if specialty in ["Cardiology", "Neurology"]:
            base_confidence = self.random.uniform(0.55, 0.95)
        else:
            base_confidence = self.random.uniform(0.70, 0.99)
            
        confidence = round(base_confidence, 2)
        
        # Decide if the AI makes a coding mistake
        # Mistakes are more common with lower confidence
        make_mistake = self.random.random() > (confidence ** 0.5)
        
        predicted_icd = list(correct_icd)
        predicted_cpt = list(correct_cpt)
        
        if make_mistake:
            # Swap or mutate one code
            if self.random.choice([True, False]) and predicted_icd:
                # Modify last char of ICD-10 code to simulate minor mismatch
                last_char = predicted_icd[0][-1]
                mutated_char = str((int(last_char) + 1) % 10) if last_char.isdigit() else "9"
                predicted_icd[0] = predicted_icd[0][:-1] + mutated_char
            else:
                # Change CPT code slightly
                predicted_cpt[0] = str(int(predicted_cpt[0]) + 1)

        # Route to audit if confidence is less than 0.75
        action_taken = "routed_to_audit" if confidence < 0.75 else "auto_billed"
        
        return {
            "ai_model_version": self.model_version,
            "predicted_icd10": predicted_icd,
            "predicted_cpt": predicted_cpt,
            "confidence_score": confidence,
            "action_taken": action_taken
        }
