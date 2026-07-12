-- Pulse AI RCM KPI Calculations and Analytics queries

-- 1. Main Executive KPIs
-- Calculates Denial Rate, Clean Claim Rate, Automation Rate, and Total Financials
SELECT 
    COUNT(*) as total_claims,
    SUM(e.charge_amount) as total_charges,
    SUM(c.paid_amount) as total_payments,
    SUM(e.charge_amount - c.paid_amount) as total_leakage,
    
    -- Denial Rate
    ROUND(CAST(SUM(CASE WHEN c.status = 'denied' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100, 2) as denial_rate,
    
    -- AI Automation Rate (routed directly to billing without human audit)
    ROUND(CAST(SUM(CASE WHEN ai.action_taken = 'auto_billed' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100, 2) as automation_rate,
    
    -- Clean Claim Rate (Paid claims that did not go to audit)
    ROUND(CAST(SUM(CASE WHEN c.status = 'paid' AND ai.action_taken = 'auto_billed' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100, 2) as clean_claim_rate
FROM claims c
JOIN encounters e ON c.encounter_id = e.encounter_id
JOIN ai_coding_logs ai ON c.encounter_id = ai.encounter_id;


-- 2. AI Coder Calibration & Accuracy
-- Calculates AI accuracy vs. confidence bins
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


-- 3. Denial Reason Breakdown
-- Focuses on high-impact denial causes
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


-- 4. Auditor Productivity and Workload
SELECT 
    a.auditor_id,
    COUNT(*) as claims_reviewed,
    AVG(a.audit_duration_seconds) as avg_duration_seconds,
    SUM(CASE WHEN a.decision = 'corrected' THEN 1 ELSE 0 END) as corrections_made,
    ROUND(CAST(SUM(CASE WHEN a.decision = 'corrected' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100, 2) as correction_rate
FROM audit_logs a
GROUP BY auditor_id
ORDER BY claims_reviewed DESC;


-- 5. Revenue Leakage by Specialty
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
