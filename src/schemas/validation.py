from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field, condecimal, field_validator

class EventType(str, Enum):
    ENCOUNTER_REGISTERED = "encounter_registered"
    AI_CODING_PROCESSED = "ai_coding_processed"
    AUDITOR_REVIEWED = "auditor_reviewed"
    CLAIM_SUBMITTED = "claim_submitted"
    PAYER_RESPONDED = "payer_responded"

class ActionTaken(str, Enum):
    AUTO_BILLED = "auto_billed"
    ROUTED_TO_AUDIT = "routed_to_audit"

class AuditDecision(str, Enum):
    AGREED = "agreed"
    CORRECTED = "corrected"

class PayerStatus(str, Enum):
    PAID = "paid"
    DENIED = "denied"

class EncounterPayload(BaseModel):
    patient_id: str
    specialty: str
    visit_date: date
    symptoms: str
    clinical_notes: str

class AICodingPayload(BaseModel):
    ai_model_version: str
    predicted_icd10: List[str]
    predicted_cpt: List[str]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    action_taken: ActionTaken

class AuditorReviewPayload(BaseModel):
    auditor_id: str
    decision: AuditDecision
    final_icd10: List[str]
    final_cpt: List[str]
    audit_duration_seconds: int = Field(..., ge=0)

class ClaimSubmittedPayload(BaseModel):
    payer_id: str
    charge_amount: float = Field(..., ge=0.0)

class PayerRespondedPayload(BaseModel):
    payer_id: str
    status: PayerStatus
    denial_reason: Optional[str] = None
    allowed_amount: float = Field(..., ge=0.0)
    paid_amount: float = Field(..., ge=0.0)

class TelemetryEvent(BaseModel):
    event_id: UUID
    event_type: EventType
    timestamp: datetime
    encounter_id: str
    payload: Union[
        EncounterPayload,
        AICodingPayload,
        AuditorReviewPayload,
        ClaimSubmittedPayload,
        PayerRespondedPayload
    ]

    @field_validator("payload", mode="before")
    @classmethod
    def parse_payload(cls, v, info):
        # Allow dynamic parsing of payload based on event_type if it is a dict
        if isinstance(v, dict):
            event_type = info.data.get("event_type")
            if event_type == EventType.ENCOUNTER_REGISTERED:
                return EncounterPayload(**v)
            elif event_type == EventType.AI_CODING_PROCESSED:
                return AICodingPayload(**v)
            elif event_type == EventType.AUDITOR_REVIEWED:
                return AuditorReviewPayload(**v)
            elif event_type == EventType.CLAIM_SUBMITTED:
                return ClaimSubmittedPayload(**v)
            elif event_type == EventType.PAYER_RESPONDED:
                return PayerRespondedPayload(**v)
        return v
