-- SQLite Database Schema for Pulse AI RCM platform

CREATE TABLE IF NOT EXISTS encounters (
    encounter_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    specialty TEXT NOT NULL,
    visit_date DATE NOT NULL,
    symptoms TEXT,
    clinical_notes TEXT,
    correct_icd10 TEXT, -- JSON array represented as string
    correct_cpt TEXT,   -- JSON array represented as string
    charge_amount REAL NOT NULL,
    payer_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_coding_logs (
    encounter_id TEXT PRIMARY KEY,
    ai_model_version TEXT NOT NULL,
    predicted_icd10 TEXT NOT NULL,
    predicted_cpt TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    action_taken TEXT NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(encounter_id) REFERENCES encounters(encounter_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    encounter_id TEXT PRIMARY KEY,
    auditor_id TEXT NOT NULL,
    decision TEXT NOT NULL, -- 'agreed' or 'corrected'
    final_icd10 TEXT NOT NULL,
    final_cpt TEXT NOT NULL,
    audit_duration_seconds INTEGER NOT NULL,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(encounter_id) REFERENCES encounters(encounter_id)
);

CREATE TABLE IF NOT EXISTS claims (
    encounter_id TEXT PRIMARY KEY,
    payer_id TEXT NOT NULL,
    status TEXT NOT NULL, -- 'paid' or 'denied'
    denial_reason TEXT,
    allowed_amount REAL NOT NULL,
    paid_amount REAL NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(encounter_id) REFERENCES encounters(encounter_id)
);
