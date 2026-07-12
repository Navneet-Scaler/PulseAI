## Build spec

Build a local-first synthetic healthcare coding observability system called **PulseAI** that simulates EHR chart ingestion, AI medical coding, human auditor review, claim submission, and denial outcomes. The system must expose full event-level telemetry, analytics SQL, a Power BI-ready dataset, and a Jupyter notebook for A/B testing of explainability features. Healthcare RCM dashboards commonly track denial rate, days in AR, payer mix, clean claim rate, and net revenue per visit, so include those as first-class outputs. [medicalbillersandcoders](https://www.medicalbillersandcoders.com/rcm-dashboard)

## Core modules

- Synthetic chart generator.
- LLM coding engine wrapper.
- Telemetry event logger.
- Auditor review simulator.
- Claims and denial simulator.
- Analytical SQL layer.
- Dashboard export layer.
- Experimentation notebook.
- Streamlit demo app.
- FastAPI backend.

## Tech stack

- Python 3.11.
- Streamlit for interactive demo.
- FastAPI for model and event APIs.
- PostgreSQL or DuckDB for analytics.
- JSON Lines for raw event logs.
- Pydantic for schema validation.
- SQLAlchemy or psycopg for DB writes.
- Plotly for local charts.
- Power BI for final dashboard consumption.
- Jupyter + scipy.stats + statsmodels for experiments.
- Optional local LLM via Ollama.

## Data model

Use these core entities:

- `chart`: one EHR encounter.
- `patient`: synthetic patient profile.
- `encounter`: visit metadata.
- `ai_run`: one model inference.
- `audit_action`: human review action.
- `claim`: submitted billing claim.
- `denial`: payer rejection event.
- `experiment_assignment`: A/B test group.

Include these fields at minimum:

- `chart_id`.
- `encounter_id`.
- `patient_id`.
- `specialty`.
- `department`.
- `payer_type`.
- `payer_mix_type`.
- `encounter_type`.
- `unstructured_char_count`.
- `note_text`.
- `chart_tags`.
- `model_name`.
- `model_version`.
- `confidence_score`.
- `latency_ms`.
- `tokens_consumed`.
- `suggested_codes`.
- `suggested_modifiers`.
- `rationale_snippet`.
- `auditor_action_type`.
- `overridden_codes`.
- `added_codes`.
- `time_to_resolve_sec`.
- `submitted_codes`.
- `claim_amount_usd`.
- `denial_reason`.
- `financial_loss_usd`.
- `appealed_flag`.

## Event tracking plan

Log every major step as a typed JSON event.

- `Chart_Ingested`.
- `AI_Code_Generation_Finalized`.
- `Auditor_Review_Action`.
- `Claim_Submitted`.
- `Denial_Event`.
- `Experiment_Assigned`.

Each event should contain:

- `event_id`.
- `event_ts`.
- `chart_id`.
- `transaction_id`.
- `event_type`.
- `payload`.
- `schema_version`.
- `source_system`.
- `trace_id`.

Add strict validation so malformed events fail fast.

## Clinical simulation logic

Generate synthetic charts that stress coding specificity.

Include scenarios like:

- Diabetes with CKD stage 3.
- CHF with acute exacerbation.
- Chest pain with nitroglycerin response.
- COPD with hypoxia.
- Sepsis rule-out versus confirmed sepsis.
- E/M level differences across ED, cardiology, endocrinology, nephrology, and primary care.

Generate notes with:

- varying severity language,
- ambiguous documentation,
- missing laterality,
- missing stage specificity,
- conflicting evidence,
- payer-sensitive cases.

This is important because explainable coding systems are expected to show evidence behind each code, and coding tools are increasingly differentiated by transparency rather than only raw accuracy. [blog.nym](https://blog.nym.health/transparent-ai-for-medical-coding)

## AI coding engine

Implement the coding engine as a wrapper around either:

- a local Ollama model,
- a stubbed deterministic model,
- or an API-based mock.

The engine should output:

- ICD-10 codes.
- CPT / E/M codes.
- HCPCS or modifiers when applicable.
- confidence score.
- rationale snippet.
- evidence spans from the note.
- top alternative codes.
- latency and token usage.

Add a noise layer that can simulate:

- low-confidence outputs,
- hallucinated modifiers,
- undercoding,
- overcoding,
- latency spikes,
- specialty-specific error patterns.

## Auditor simulator

Simulate a human coder/auditor with policy-based behavior.

Inputs:

- confidence score.
- specialty.
- payer type.
- code complexity.
- number of missing specifics.
- prior override history.

Outputs:

- approve.
- modify.
- reject.
- flag for escalation.

Track:

- time to resolve,
- changed codes,
- reason category,
- whether the AI explanation helped,
- whether the final claim was cleaner.

## Denial simulator

Create denial events using synthetic payer rules.

Use denial reason buckets such as:

- `Medical_Necessity`.
- `Missing_Modifier`.
- `CCI_Edit_Conflict`.
- `Invalid_DX_PX_Pair`.
- `Unsupported_E_M_Level`.
- `Missing_Specificity`.
- `Authorization_Issue`.

Attach:

- denial amount,
- appeal outcome,
- recovery amount,
- days-to-resolution,
- downstream revenue loss.

RCM dashboards should clearly surface denial rate, days in AR, payer mix, and clean claim performance, since these are standard operational metrics in healthcare revenue-cycle reporting. [impactinnovations](https://www.impactinnovations.ai/blog/top-7-rcm-kpis-every-practice-should-track-revenue-cycle-management-metrics-how-to-use-them)

## Analytics layer

Store raw events and derived tables.

Create these derived tables:

- `fact_chart`.
- `fact_ai_run`.
- `fact_audit`.
- `fact_claim`.
- `fact_denial`.
- `agg_confidence_bucket`.
- `agg_specialty_kpi`.
- `agg_physician_leakage`.
- `agg_experiment_results`.

Add these metrics:

- automation rate.
- first-pass acceptance rate.
- denial rate.
- average time to resolve.
- claim value preserved.
- claim value lost.
- pre-A/R days proxy.
- override rate.
- undercode rate.
- overcode rate.
- leakage per physician.
- confidence-to-denial calibration.

## SQL requirements

Write production-style SQL with:

- CTEs.
- window functions.
- conditional aggregation.
- percentile buckets.
- rolling averages.
- cohort comparisons.
- specialty-level slicing.

Implement these analyses:

- trust horizon curve: find confidence threshold where `P(modify) < 0.05`.
- leakage detection: compare chart specificity to final submitted codes.
- denial calibration: confidence bucket vs denial rate.
- auditor friction analysis: time to resolve by specialty and code complexity.
- experiment analysis: treatment vs control on resolution time and denial rate.

## Trust horizon logic

Define the trust horizon as the lowest confidence bucket where modification rate drops below 5 percent.

Compute:

- modifications per bucket,
- total charts per bucket,
- modification probability,
- cumulative modification curve,
- confidence cutoff,
- confidence deciles,
- confidence-binned denial rate.

Then use the cutoff as the autonomous billing threshold.

## Specificity leakage logic

Detect cases where the note supports a more specific diagnosis but the submitted claim uses a weaker code.

Examples:

- CKD stage 3 documented, but submitted as unspecified CKD.
- diabetes with complications documented, but coded as plain Type 2 diabetes.
- modifier 25 needed but missing.
- E/M level lowered without documentation evidence.

Output:

- chart_id,
- missing specificity type,
- expected code,
- submitted code,
- estimated revenue leakage,
- physician or department owner.

## Power BI pages

Create these pages:

- Executive RCM overview.
- AI confidence calibration.
- E/M distribution by department.
- Denial reasons and root causes.
- Revenue leakage explorer.
- Auditor workload and override patterns.
- Experiment results.

Each page should include slicers for:

- date range,
- specialty,
- payer type,
- department,
- model version,
- confidence bucket,
- auditor action type.

## Executive KPIs

Include these KPIs on the main page:

- Automation Rate.
- First-Pass Acceptance Rate.
- Denial Rate.
- Days in AR proxy.
- Revenue Leakage.
- Override Rate.
- Mean Audit Time.

Use these as CFO-style metrics, because these are the kinds of fields actual RCM dashboards surface. [lets-viz](https://lets-viz.com/dashboards/power-bi-revenue-cycle)

## Experiment notebook

Run a 14-day A/B test for an inline explainability feature.

Control:
- normal code output.

Treatment:
- show exact chart snippet supporting each suggested code.

Measure:

- `time_to_resolve_sec`.
- denial rate.
- override rate.
- appeal rate.
- confidence in AI suggestions.

Use:

- sample size estimate,
- 80 percent power,
- alpha = 0.05,
- independent two-sample t-test,
- Welch’s t-test if variances differ,
- effect size,
- confidence intervals,
- non-inferiority check on denial rate.

## Streamlit app

Build the app with these views:

- chart generator.
- inference panel.
- raw event log viewer.
- code diff viewer.
- auditor action simulator.
- KPI summary.
- SQL query runner.
- experiment dashboard.

Must support:

- generating one chart,
- batch generating many charts,
- replaying one chart through the pipeline,
- exporting events to CSV,
- exporting Power BI-ready tables.

## Repo structure

Use a tutorial-style repo layout like a step-by-step build log.

- `01_chart_generator/`
- `02_model_wrapper/`
- `03_event_schema/`
- `04_audit_simulator/`
- `05_claim_denial_simulator/`
- `06_sql_analytics/`
- `07_powerbi_exports/`
- `08_ab_experiment/`
- `09_streamlit_demo/`
- `README.md`

Each folder should contain:

- one main script,
- one sample input file,
- one output artifact,
- one short explanation file.

## Presentation style

Present the project like a build tutorial, not a polished SaaS landing page.

Use:

- numbered steps,
- small milestones,
- plain technical language,
- visible intermediate outputs,
- schema definitions,
- SQL snippets,
- screenshots or tables,
- before/after results.

The tone should feel like a systems build log: “ingest chart,” “run model,” “write event,” “aggregate metrics,” “inspect leakage,” “test threshold.”

## Resume-safe output

Use measurable bullets only.

- Built a synthetic autonomous coding telemetry engine processing 75,000+ EHR charts across six specialties.
- Instrumented JSON event tracking for chart ingestion, AI inference, auditor actions, claims, and denial outcomes.
- Wrote SQL pipelines to compute trust horizon, specificity leakage, and confidence-to-denial calibration.
- Built Power BI dashboards for automation rate, first-pass acceptance rate, denial rate, and revenue leakage.
- Ran a 14-day A/B test on explainability UI and measured auditor time reduction with no increase in denial rate.

## Extra features to add

- code versioning and model version tracking.
- audit trail UI with highlighted evidence spans.
- rule-based code validator.
- payer-specific denial simulation.
- specialty-specific prompt templates.
- latency SLO tracking.
- confidence drift monitoring.
- alerting when override rate spikes.
- cohort comparison by physician or department.
- exportable RCA report.
- synthetic data seed control for reproducibility.
- deterministic replay mode.
- anomaly detection on denial surges.
- note-to-code diff viewer.
- claims lifecycle timeline.
- threshold tuning panel.
- human override reason taxonomy.
- CSV/Parquet export for BI.
- daily batch metrics table.
- backfill script for recomputing KPIs.

## Grounding notes

Actual healthcare coding and RCM reporting commonly centers on denial rate, days in AR, clean claim performance, payer mix, and explainable audit trails. Medical coding tools are also being positioned around exact chart citations and transparent AI rather than black-box outputs, so your build should emphasize evidence spans and defensible reviewability. [docreport](https://docreport.us/us/medical-coding-assistant)
