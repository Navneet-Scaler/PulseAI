# PulseAI Data Dictionary

This document details the database schema and event schemas for the PulseAI RCM Intelligence Platform, serving as a reference for database administration, analytics query writing, and interview preparation.

---

## 1. Database Schema (SQLite)

The PulseAI platform utilizes a local SQLite database (`pulse_ai.db`) consisting of four core transactional tables structured around patient encounters, AI outputs, auditor reviews, and claim adjudication results.

### 1.1 `encounters` Table
Stores raw EHR encounters and patient visit clinical metadata.

| Column Name | Data Type | Primary/Foreign Key | Description |
| :--- | :--- | :--- | :--- |
| `encounter_id` | TEXT | PRIMARY KEY | Unique identifier for the EHR encounter. |
| `patient_id` | TEXT | - | Unique identifier representing the patient. |
| `specialty` | TEXT | - | Medical specialty associated with the encounter (e.g., `Cardiology`, `Endocrinology`, `Nephrology`, `Neurology`, `Orthopedics`, `Primary Care`). |
| `visit_date` | DATE | - | Calendar date of the patient encounter. |
| `symptoms` | TEXT | - | Narrative description of patient symptoms. |
| `clinical_notes` | TEXT | - | Free-text EHR narrative note describing details of the visit, diagnoses, and procedures. |
| `correct_icd10` | TEXT | - | JSON array of ground-truth ICD-10 diagnostic codes as confirmed by standard clinical validation. |
| `correct_cpt` | TEXT | - | JSON array of ground-truth CPT procedural codes as confirmed by standard clinical validation. |
| `charge_amount` | REAL | - | Total gross charges billed for the encounter (USD). |
| `payer_id` | TEXT | - | Identifier for the payer entity (e.g., `Payer_Medicare`, `Payer_BlueCross`, `Payer_Aetna`, `Payer_United`). |

### 1.2 `ai_coding_logs` Table
Logs autonomous AI-driven medical coding predictions and decision routing.

| Column Name | Data Type | Primary/Foreign Key | Description |
| :--- | :--- | :--- | :--- |
| `encounter_id` | TEXT | PRIMARY KEY, FK | References `encounters(encounter_id)`. |
| `ai_model_version` | TEXT | - | The version identifier of the AI coding engine (e.g., `pulse-coder-v1`). |
| `predicted_icd10` | TEXT | - | JSON array of diagnostic ICD-10 codes predicted by the AI model. |
| `predicted_cpt` | TEXT | - | JSON array of procedural CPT codes predicted by the AI model. |
| `confidence_score` | REAL | - | Confidence metric assigned by the AI coder, ranging between `0.0` and `1.0`. |
| `action_taken` | TEXT | - | Routing decision outcome: `auto_billed` (fully autonomous submission) or `routed_to_audit` (sent to human audit queue). |
| `processed_at` | TIMESTAMP | - | UTC timestamp when the AI model inference was executed. |

### 1.3 `audit_logs` Table
Tracks corrections and decisions made by human medical auditors.

| Column Name | Data Type | Primary/Foreign Key | Description |
| :--- | :--- | :--- | :--- |
| `encounter_id` | TEXT | PRIMARY KEY, FK | References `encounters(encounter_id)`. |
| `auditor_id` | TEXT | - | Unique identifier for the human auditor who reviewed the claim (e.g., `auditor_1`). |
| `decision` | TEXT | - | Auditor's action on AI codes: `agreed` (no changes) or `corrected` (modified codes). |
| `final_icd10` | TEXT | - | JSON array of final diagnostic ICD-10 codes submitted on the claim. |
| `final_cpt` | TEXT | - | JSON array of final CPT procedural codes submitted on the claim. |
| `audit_duration_seconds`| INTEGER| - | Time in seconds elapsed during the human review process. |
| `reviewed_at` | TIMESTAMP | - | UTC timestamp when the auditor submitted the review. |

### 1.4 `claims` Table
Logs the final claim status and financial adjudication response from payers.

| Column Name | Data Type | Primary/Foreign Key | Description |
| :--- | :--- | :--- | :--- |
| `encounter_id` | TEXT | PRIMARY KEY, FK | References `encounters(encounter_id)`. |
| `payer_id` | TEXT | - | Target insurance carrier identifier. |
| `status` | TEXT | - | Claim status outcome: `paid` or `denied`. |
| `denial_reason` | TEXT | - | Specific denial code if claim was rejected (e.g., `Missing_Modifier`, `Medical_Necessity`, `CCI_Edit_Conflict`, `Unsupported_E_M_Level`, or `NULL` if paid). |
| `allowed_amount` | REAL | - | Contracted allowed reimbursement amount (USD). |
| `paid_amount` | REAL | - | Actual amount paid by the insurance carrier (matches `allowed_amount` if paid, `0` if denied) (USD). |
| `submitted_at` | TIMESTAMP | - | UTC timestamp when the claim was submitted to the payer clearinghouse. |

---

## 2. Event Telemetry Schema (JSON Lines)

Raw telemetry stream events are structured as JSON objects conforming to the system JSON Schema.

### 2.1 Standard Envelope Columns
Every telemetry event payload is wrapped in a standard tracking envelope containing metadata:

* `event_id` (string, UUID): Unique ID representing the telemetry message.
* `event_type` (string): The event category. One of:
  * `encounter_registered`
  * `ai_coding_processed`
  * `auditor_reviewed`
  * `claim_submitted`
  * `payer_responded`
* `timestamp` (string, ISO-8601 DateTime): UTC timestamp of the event trigger.
* `encounter_id` (string): Unique identifier for the related patient encounter.
* `payload` (object): Event-specific data dictionary containing values related to the event type.

### 2.2 Event Payloads

#### `encounter_registered` Payload
Emitted when a new patient encounter is registered.
```json
{
  "patient_id": "PT_1001",
  "specialty": "Cardiology",
  "visit_date": "2026-07-01",
  "symptoms": "Substernal chest pressure...",
  "clinical_notes": "Patient presents with chest pain..."
}
```

#### `ai_coding_processed` Payload
Emitted when the autonomous AI coding engine finishes analyzing clinical documentation.
```json
{
  "ai_model_version": "pulse-coder-v1",
  "predicted_icd10": ["I20.9"],
  "predicted_cpt": ["93000"],
  "confidence_score": 0.85,
  "action_taken": "auto_billed"
}
```

#### `auditor_reviewed` Payload
Emitted when a claims auditor finishes auditing a low-confidence claim.
```json
{
  "auditor_id": "auditor_3",
  "decision": "corrected",
  "final_icd10": ["I20.9", "R07.9"],
  "final_cpt": ["93000", "99214"],
  "audit_duration_seconds": 142
}
```

#### `claim_submitted` Payload
Emitted when a claim is packaged and sent to the insurance payer clearinghouse.
```json
{
  "payer_id": "Payer_Medicare",
  "charge_amount": 320.00
}
```

#### `payer_responded` Payload
Emitted when the payer adjudicates the claim.
```json
{
  "payer_id": "Payer_Medicare",
  "status": "paid",
  "denial_reason": null,
  "allowed_amount": 250.00,
  "paid_amount": 250.00
}
```
