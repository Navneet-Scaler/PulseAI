from datetime import date

from src.core.generator import SyntheticDataGenerator
from src.core.ai_coder import AICoder
from src.core.auditor import AuditorSimulator
from src.core.denial_simulator import DenialSimulator


def test_generate_batch_count_and_unique_ids():
    gen = SyntheticDataGenerator(seed=7)
    batch = gen.generate_batch(date(2026, 7, 1), count=25)
    assert len(batch) == 25
    assert len({e["encounter_id"] for e in batch}) == 25
    for enc in batch:
        assert enc["charge_amount"] > 0
        assert enc["specialty"] in {"Cardiology", "Orthopedics", "Neurology", "General Medicine"}


def test_ai_coder_routing_matches_confidence_threshold():
    encounter = {
        "specialty": "General Medicine",
        "correct_icd10": ["E11.9"],
        "correct_cpt": ["99214"]
    }
    seen_actions = set()
    for seed in range(50):
        pred = AICoder(seed=seed).predict(encounter)
        seen_actions.add(pred["action_taken"])
        expected = "routed_to_audit" if pred["confidence_score"] < 0.75 else "auto_billed"
        assert pred["action_taken"] == expected
    # Across enough seeds we should observe both routing outcomes at least once.
    assert seen_actions == {"auto_billed", "routed_to_audit"}


def test_auditor_agrees_when_ai_matches_ground_truth():
    auditor = AuditorSimulator(seed=5)
    encounter = {"specialty": "General Medicine", "correct_icd10": ["E11.9"], "correct_cpt": ["99214"]}
    ai_prediction = {"predicted_icd10": ["E11.9"], "predicted_cpt": ["99214"]}
    result = auditor.review(encounter, ai_prediction)
    assert result["decision"] == "agreed"
    assert result["final_icd10"] == ["E11.9"]
    assert result["audit_duration_seconds"] > 0


def test_auditor_corrects_when_ai_diverges_from_ground_truth():
    auditor = AuditorSimulator(seed=5)
    encounter = {"specialty": "Cardiology", "correct_icd10": ["I20.9"], "correct_cpt": ["93000"]}
    ai_prediction = {"predicted_icd10": ["I20.8"], "predicted_cpt": ["93000"]}
    result = auditor.review(encounter, ai_prediction)
    assert result["decision"] == "corrected"
    assert result["final_icd10"] == ["I20.9"]
    assert result["final_cpt"] == ["93000"]


def test_denial_simulator_flags_coding_mismatch_as_high_risk():
    encounter = {"payer_id": "Payer_Aetna", "charge_amount": 500.0, "correct_icd10": ["I20.9"], "correct_cpt": ["93000"]}
    trials = 40
    denied = 0
    for seed in range(trials):
        res = DenialSimulator(seed=seed).process_claim(encounter, ["I20.8"], ["93000"])
        if res["status"] == "denied":
            denied += 1
            assert res["denial_reason"] == "Incorrect Coding Mismatch"
            assert res["paid_amount"] == 0.0
    # Mismatched codes are denied ~90% of the time per the simulator's design.
    assert denied / trials > 0.7


def test_denial_simulator_pays_correct_claims_with_bounded_allowed_amount():
    encounter = {"payer_id": "Payer_Medicare", "charge_amount": 1000.0, "correct_icd10": ["I20.9"], "correct_cpt": ["93000"]}
    saw_paid = False
    for seed in range(20):
        res = DenialSimulator(seed=seed).process_claim(encounter, ["I20.9"], ["93000"])
        if res["status"] == "paid":
            saw_paid = True
            assert 0 < res["allowed_amount"] <= encounter["charge_amount"]
            assert 0 < res["paid_amount"] <= res["allowed_amount"]
        else:
            assert res["allowed_amount"] == 0.0
            assert res["paid_amount"] == 0.0
    assert saw_paid
