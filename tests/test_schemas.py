from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.schemas.validation import TelemetryEvent, EventType


def _base_ai_coding_payload(**overrides):
    payload = {
        "ai_model_version": "PulseCoder-v2.1",
        "predicted_icd10": ["I20.9"],
        "predicted_cpt": ["93000"],
        "confidence_score": 0.9,
        "action_taken": "auto_billed"
    }
    payload.update(overrides)
    return payload


def test_telemetry_event_parses_typed_payload_by_event_type():
    event = TelemetryEvent(
        event_id=uuid4(),
        event_type=EventType.AI_CODING_PROCESSED,
        timestamp=datetime.utcnow(),
        encounter_id="ENC_1",
        payload=_base_ai_coding_payload()
    )
    assert event.payload.confidence_score == 0.9
    assert event.payload.action_taken == "auto_billed"


def test_telemetry_event_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        TelemetryEvent(
            event_id=uuid4(),
            event_type=EventType.AI_CODING_PROCESSED,
            timestamp=datetime.utcnow(),
            encounter_id="ENC_1",
            payload=_base_ai_coding_payload(confidence_score=1.5)
        )


def test_telemetry_event_rejects_invalid_action_taken():
    with pytest.raises(ValidationError):
        TelemetryEvent(
            event_id=uuid4(),
            event_type=EventType.AI_CODING_PROCESSED,
            timestamp=datetime.utcnow(),
            encounter_id="ENC_1",
            payload=_base_ai_coding_payload(action_taken="not_a_real_action")
        )


def test_telemetry_event_rejects_negative_audit_duration():
    with pytest.raises(ValidationError):
        TelemetryEvent(
            event_id=uuid4(),
            event_type=EventType.AUDITOR_REVIEWED,
            timestamp=datetime.utcnow(),
            encounter_id="ENC_1",
            payload={
                "auditor_id": "Auditor_Sarah",
                "decision": "corrected",
                "final_icd10": ["I20.9"],
                "final_cpt": ["93000"],
                "audit_duration_seconds": -5
            }
        )
