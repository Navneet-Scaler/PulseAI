# Pulse AI - Revenue Cycle Management (RCM) Intelligence Platform

Pulse AI is a premium, portfolio-grade Revenue Cycle Management (RCM) telemetry and billing intelligence simulator. The platform models autonomous AI medical coding (mapping patient visit clinical notes to ICD-10 and CPT codes), human-in-the-loop audit workflows, and payer claim processing. It offers real-time API telemetry ingestion, advanced SQL analytics, A/B testing billing analysis, and a high-fidelity interactive Streamlit dashboard.

---

## ⚡ Key Highlights
* **Core Simulator Engine**: Simulates medical encounter creation, model inference, audit queues, and insurance billing response.
* **FastAPI Backend**: Real-time telemetry logging conforming to a strict validation layer using **Pydantic v2** models.
* **SQL KPI Engine**: Pre-baked database scripts to compute Denial Rate, Clean Claim Rate, Automation Rate, and Auditor Correction Rate.
* **Streamlit Command Center**: A rich, premium dark-themed dashboard showing executive summaries, AI confidence calibration, denial analytics, revenue leakage, auditor workload, and A/B test results.
* **A/B Testing & Power Analysis**: Jupyter notebook demonstrating cohort analysis, proportions Z-testing, and statistical power analysis for model upgrades.

---

## 📂 Directory Structure

```
Pulse AI/
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI workflow
├── sql/
│   ├── schema.sql             # SQLite schema
│   └── kpi_calculations.sql   # SQL analytics queries
├── schemas/
│   └── telemetry_event.json   # Telemetry event JSON Schema
├── notebooks/
│   └── ab_testing_analysis.ipynb # Jupyter A/B test notebook
├── src/
│   ├── api/
│   │   └── main.py            # FastAPI Web Server
│   ├── core/
│   │   ├── ai_coder.py        # AI Coding simulator stub
│   │   ├── auditor.py         # Auditor reviewer simulation
│   │   ├── denial_simulator.py # Insurance denial simulator
│   │   └── generator.py       # Patient visit synthetic data generator
│   ├── schemas/
│   │   └── validation.py      # Pydantic v2 validation classes
│   ├── utils/
│   │   ├── backfill.py        # DB populate script
│   │   ├── export.py          # Table exporter to CSV
│   │   └── replay.py          # API ingestion replay stream
│   └── app.py                 # Multi-page Streamlit Dashboard app
├── tests/
│   └── test_rcm.py            # Pytest test suite
├── requirements.txt           # Main python dependencies
├── .env.example               # Config environment settings
├── .gitignore
├── LICENSE                    # MIT License
└── README.md                  # This file
```

---

## 🚀 Setup & Run Instructions

### 1. Installation
Clone the repository and install the dependencies:
```bash
pip install -r requirements.txt
```

### 2. Backfill Historical Data
Pre-populate the SQLite database with 750 simulated patient visits and billing outcomes:
```bash
python3 -m src.utils.backfill
```

### 3. Run the Streamlit Dashboard
```bash
streamlit run src/app.py
```

### 4. Run the FastAPI Telemetry Server
```bash
uvicorn src.api.main:app --reload
```

---

## 📊 Telemetry Event Schemas

All event streams are validated via Pydantic v2. The lifecyle follows:
1. `encounter_registered`: Capture demographic information, specialty, symptoms, and clinical notes.
2. `ai_coding_processed`: AI model predicts ICD-10 & CPT codes with self-assessed confidence.
3. `auditor_reviewed`: Triggered if confidence < 0.75; human auditor corrects codes.
4. `payer_responded`: Insurance payment response showing Allowed Amount, Paid Amount, or Denial Reason.

---

## 🛡️ License
This project is licensed under the MIT License - see the [LICENSE](file:///Users/navneet/dev/projects/Pulse%20AI/LICENSE) file for details.
