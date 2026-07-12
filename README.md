# Pulse AI - Revenue Cycle Management (RCM) Intelligence Platform

Pulse AI is an enterprise-grade Revenue Cycle Management (RCM) billing intelligence and simulation platform. The system models autonomous AI-driven medical coding (predicting CPT/ICD-10 codes from clinical notes), human-in-the-loop audit workflows, and insurance payer claim adjudication. It features real-time API telemetry ingestion, advanced SQL KPI calculations, A/B testing analysis, and a high-density, professional operational command center dashboard.

---

## Core System Architecture

The platform simulates a real-world healthcare billing pipeline containing four distinct lifecycle stages:

1. **Clinical Encounter Ingestion**: Patient visits are registered with clinical notes, primary symptoms, medical specialty, and ground-truth codes.
2. **Autonomous AI Coding**: A simulated AI coder analyzes clinical documentation, predicting ICD-10 diagnostic codes and CPT procedural codes, assigning an internal confidence score.
3. **Operational Quality Audit**: Claims with AI confidence scores falling below a tunable threshold are routed to human auditor queues. Auditors review and correct coding errors.
4. **Payer Adjudication (Denial Simulator)**: Claims are submitted to payers. Claims carrying uncorrected coding errors are denied at a high rate (90%), while clean claims are paid out at contracted allowed rates, subject to payer-specific baseline denial rates.

---

## Key Platform Features

* **High-Density Corporate Dashboard**: Structured using a dark slate, high-contrast theme focused on core operational metrics.
* **Dynamic Confidence Threshold Tuning**: Interactive optimization simulation allowing administrators to adjust AI routing thresholds to find the sweet spot maximizing net payouts (balancing prevented denials vs. human auditor labor costs).
* **Advanced RCM Metrics**: Calculates critical financial metrics:
  * **Days in Accounts Receivable (AR Days)**: Mean outstanding collection cycle time.
  * **Clean Claim Rate (CCR)**: Percentage of claims paid on first submission without audit.
  * **Auditor Labor ROI**: Financial returns of human reviews vs. audit labor overhead.
  * **Contractual Underpayment Audits**: Highlights instances where insurers paid below the contracted allowed rate.
* **AR Aging Buckets**: Dynamic categorization of outstanding claims (0-10 Days, 11-20 Days, 21+ Days) in a stacked bar chart to identify cash flow blockages.
* **Payer Denial Heatmaps**: Visual correlation matrices plotting underwriters against specific denial reasons.

---

## Directory Structure

```
Pulse AI/
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI pipeline
├── sql/
│   ├── schema.sql             # SQLite database schemas
│   └── kpi_calculations.sql   # Advanced KPI analytics queries
├── schemas/
│   └── telemetry_event.json   # Telemetry event JSON Schema
├── notebooks/
│   └── ab_testing_analysis.ipynb # A/B testing & power analysis notebook
├── src/
│   ├── api/
│   │   └── main.py            # FastAPI Web Server
│   ├── core/
│   │   ├── ai_coder.py        # Autonomous AI Coder stub
│   │   ├── auditor.py         # Human Auditor simulation
│   │   ├── denial_simulator.py # Insurance Adjudication simulator
│   │   └── generator.py       # Patient visit generator
│   ├── schemas/
│   │   └── validation.py      # Pydantic v2 validation classes
│   ├── utils/
│   │   ├── backfill.py        # Database backfill script (2,550 claims)
│   │   ├── export.py          # Table exporter to CSV
│   │   └── replay.py          # API ingestion replay stream
│   └── app.py                 # Streamlit Command Center
├── tests/
│   └── test_rcm.py            # Pytest test suite
├── requirements.txt           # Platform python dependencies
├── .env.example               # Configuration environment settings
├── LICENSE                    # MIT License
└── README.md                  # This file
```

---

## Setup & Run Instructions

### 1. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Populate Database
Initialize the SQLite database and backfill it with 2,550 historical claims spanning 30 days:
```bash
python3 -m src.utils.backfill
```

### 3. Run the Dashboard
Start the Streamlit RCM dashboard:
```bash
python3 -m streamlit run src/app.py
```

### 4. Run the API Server
Start the FastAPI telemetry server:
```bash
python3 -m uvicorn src.api.main:app --reload
```
Once started, view the interactive Swagger API documentation at:
* **Interactive Docs**: `http://127.0.0.1:8000/docs`
* **Health Check**: `http://127.0.0.1:8000/health`

---

## Testing

Execute the test suite to verify generator logic, API routing, and validation schemas:
```bash
python3 -m pytest
```

---

## License
This project is licensed under the MIT License - see the LICENSE file for details.
