-- Pulse AI RCM KPI Calculations and Analytics queries

-- ==============================================================================
-- 1. Main Executive KPIs
-- Business Question: What is our overall operational and financial health across claims?
-- Output Columns:
--   - total_claims: Total count of billing claims processed.
--   - total_charges: Cumulative billed charge amount (gross revenue).
--   - total_payments: Cumulative actual cash paid/reimbursed by payers.
--   - total_leakage: Total uncollected revenue (charge amount minus paid amount).
--   - denial_rate: % of claims that resulted in a 'denied' status from the payer.
--   - automation_rate: % of claims processed autonomously without human audit routing.
--   - clean_claim_rate: % of claims paid on first submission without human intervention.
-- ==============================================================================
SELECT 
    COUNT(*) as total_claims,
    SUM(e.charge_amount) as total_charges,
    SUM(c.paid_amount) as total_payments,
    SUM(e.charge_amount - c.paid_amount) as total_leakage,
    
    -- Denial Rate (Denied Claims / Total Claims)
    ROUND(CAST(SUM(CASE WHEN c.status = 'denied' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100, 2) as denial_rate,
    
    -- AI Automation Rate (routed directly to billing without human audit)
    ROUND(CAST(SUM(CASE WHEN ai.action_taken = 'auto_billed' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100, 2) as automation_rate,
    
    -- Clean Claim Rate (Paid claims that did not go to audit)
    ROUND(CAST(SUM(CASE WHEN c.status = 'paid' AND ai.action_taken = 'auto_billed' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100, 2) as clean_claim_rate
FROM claims c
JOIN encounters e ON c.encounter_id = e.encounter_id
JOIN ai_coding_logs ai ON c.encounter_id = ai.encounter_id;


-- ==============================================================================
-- 2. AI Coder Calibration & Accuracy
-- Business Question: How accurate are the AI predictions across different confidence levels?
-- Output Columns:
--   - confidence_bucket: Categorical confidence bin (e.g., '0.9 - 1.0').
--   - claim_count: Total claims in the specific confidence bin.
--   - accuracy: % of claims in this bucket where the AI's predicted ICD-10 and CPT codes exactly matched ground truth.
-- ==============================================================================
SELECT 
    CASE 
        WHEN ai.confidence_score >= 0.9 THEN '0.9 - 1.0'
        WHEN ai.confidence_score >= 0.8 THEN '0.8 - 0.9'
        WHEN ai.confidence_score >= 0.7 THEN '0.7 - 0.8'
        ELSE '< 0.7'
    END as confidence_bucket,
    COUNT(*) as claim_count,
    ROUND(CAST(SUM(CASE WHEN (ai.predicted_icd10 = e.correct_icd10 AND ai.predicted_cpt = e.correct_cpt) THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100, 2) as accuracy
FROM ai_coding_logs ai
JOIN encounters e ON ai.encounter_id = e.encounter_id
GROUP BY confidence_bucket
ORDER BY confidence_bucket DESC;


-- ==============================================================================
-- 3. Denial Reason Breakdown
-- Business Question: What are the root causes of our claim denials and their financial impact?
-- Output Columns:
--   - denial_reason: Specific denial reason category (e.g., Medical_Necessity).
--   - denial_count: Number of times this denial reason occurred.
--   - denied_charges: Total gross billed charges impacted by these denials.
--   - pct_of_denials: % contribution of this reason to total claim denials.
-- ==============================================================================
SELECT 
    denial_reason,
    COUNT(*) as denial_count,
    SUM(e.charge_amount) as denied_charges,
    ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM claims WHERE status = 'denied') * 100, 2) as pct_of_denials
FROM claims c
JOIN encounters e ON c.encounter_id = e.encounter_id
WHERE c.status = 'denied'
GROUP BY denial_reason
ORDER BY denial_count DESC;


-- ==============================================================================
-- 4. Auditor Productivity and Workload
-- Business Question: What is the performance, workload, and accuracy correction rate of each auditor?
-- Output Columns:
--   - auditor_id: Unique identifier of the claims auditor.
--   - claims_reviewed: Total claims reviewed by this auditor.
--   - avg_duration_seconds: Average time in seconds spent auditing a claim.
--   - corrections_made: Total claims where the auditor modified the AI's predicted codes.
--   - correction_rate: % of reviewed claims that required code modifications.
-- ==============================================================================
SELECT 
    a.auditor_id,
    COUNT(*) as claims_reviewed,
    AVG(a.audit_duration_seconds) as avg_duration_seconds,
    SUM(CASE WHEN a.decision = 'corrected' THEN 1 ELSE 0 END) as corrections_made,
    ROUND(CAST(SUM(CASE WHEN a.decision = 'corrected' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100, 2) as correction_rate
FROM audit_logs a
GROUP BY auditor_id
ORDER BY claims_reviewed DESC;


-- ==============================================================================
-- 5. Revenue Leakage by Specialty
-- Business Question: Which clinical specialties suffer the highest financial leakage?
-- Output Columns:
--   - specialty: Medical specialty (e.g., Cardiology).
--   - total_claims: Total claims submitted for this specialty.
--   - total_charges: Total gross charges billed.
--   - total_paid: Total cash collected.
--   - leakage_amount: Total uncollected billed dollars.
--   - leakage_rate: % of gross charges that went unpaid.
-- ==============================================================================
SELECT
    e.specialty,
    COUNT(c.encounter_id) as total_claims,
    SUM(e.charge_amount) as total_charges,
    SUM(c.paid_amount) as total_paid,
    SUM(e.charge_amount - c.paid_amount) as leakage_amount,
    ROUND((1.0 - (SUM(c.paid_amount) / SUM(e.charge_amount))) * 100, 2) as leakage_rate
FROM encounters e
LEFT JOIN claims c ON e.encounter_id = c.encounter_id
GROUP BY e.specialty
ORDER BY leakage_amount DESC;


-- ==============================================================================
-- 6. Trust Horizon: Confidence Decile vs Auditor Correction Rate
-- Business Question: At what AI confidence score threshold does the human auditor correction rate
--                    drop below 5%, signaling a safe point for fully autonomous billing?
-- Output Columns:
--   - confidence_decile: AI confidence binned into deciles (0.0 to 1.0).
--   - claims_reviewed: Total claims audited within this decile.
--   - corrections_made: Total claims within the decile requiring auditor corrections.
--   - correction_rate_pct: Empirical auditor correction rate % for this decile.
-- ==============================================================================
SELECT
    CAST(ai.confidence_score * 10 AS INT) / 10.0 as confidence_decile,
    COUNT(*) as claims_reviewed,
    SUM(CASE WHEN a.decision = 'corrected' THEN 1 ELSE 0 END) as corrections_made,
    ROUND(
        CAST(SUM(CASE WHEN a.decision = 'corrected' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100,
        2
    ) as correction_rate_pct
FROM audit_logs a
JOIN ai_coding_logs ai ON a.encounter_id = ai.encounter_id
GROUP BY confidence_decile
ORDER BY confidence_decile DESC;
