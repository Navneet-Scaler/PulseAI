import os
import sqlite3
import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as ob
import streamlit as st
from datetime import datetime, date

# Set page config with dark/premium theme styling
st.set_page_config(
    page_title="Pulse AI - RCM Intelligence Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Custom CSS styling
st.markdown(
    """
    <style>
    /* Gradient Background and Dark theme accents */
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #161a24 100%);
        color: #e2e8f0;
    }
    
    /* Premium Headers */
    h1, h2, h3 {
        font-family: 'Outfit', 'Inter', sans-serif;
        font-weight: 700;
        background: linear-gradient(to right, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Styled Metric Cards */
    div[data-testid="metric-container"] {
        background: rgba(30, 41, 59, 0.45);
        border: 1px solid rgba(129, 140, 248, 0.2);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        border-color: rgba(129, 140, 248, 0.5);
    }
    
    /* Custom Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #0b0e14;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Custom tab headers */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(30, 41, 59, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px 8px 0px 0px;
        padding: 8px 16px;
        color: #94a3b8;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: rgba(129, 140, 248, 0.15) !important;
        border-color: rgba(129, 140, 248, 0.4) !important;
        color: #38bdf8 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///pulse_ai.db").replace("sqlite:///", "")

# Verify database exists and has data, if not backfill it
if not os.path.exists(DB_PATH):
    st.info("Database not found. Generating premium synthetic RCM data...")
    from src.utils.backfill import run_backfill
    run_backfill(num_days=30, events_per_day=20)

def load_data():
    conn = sqlite3.connect(DB_PATH)
    
    enc_df = pd.read_sql_query("SELECT * FROM encounters", conn)
    ai_df = pd.read_sql_query("SELECT * FROM ai_coding_logs", conn)
    audit_df = pd.read_sql_query("SELECT * FROM audit_logs", conn)
    claims_df = pd.read_sql_query("SELECT * FROM claims", conn)
    
    conn.close()
    
    # Merge datasets for analysis
    merged = enc_df.merge(ai_df, on="encounter_id", how="left")
    merged = merged.merge(audit_df, on="encounter_id", how="left")
    merged = merged.merge(claims_df, on="encounter_id", how="left", suffixes=('_enc', '_claim'))
    
    # Convert dates/times
    merged["visit_date"] = pd.to_datetime(merged["visit_date"], format='mixed', errors='coerce')
    merged["processed_at"] = pd.to_datetime(merged["processed_at"], format='mixed', errors='coerce')
    merged["submitted_at"] = pd.to_datetime(merged["submitted_at"], format='mixed', errors='coerce')
    merged["reviewed_at"] = pd.to_datetime(merged["reviewed_at"], format='mixed', errors='coerce')
    
    # Calculate accuracy
    # Evaluate list equality on JSON strings
    def check_accuracy(row):
        try:
            correct_icd = set(json.loads(row["correct_icd10"]))
            pred_icd = set(json.loads(row["predicted_icd10"])) if pd.notna(row["predicted_icd10"]) else set()
            
            correct_cpt = set(json.loads(row["correct_cpt"]))
            pred_cpt = set(json.loads(row["predicted_cpt"])) if pd.notna(row["predicted_cpt"]) else set()
            
            return correct_icd == pred_icd and correct_cpt == pred_cpt
        except Exception:
            return False
            
    merged["is_accurate"] = merged.apply(check_accuracy, axis=1)
    
    return merged, enc_df, ai_df, audit_df, claims_df

df, encounters, ai_logs, audit_logs, claims = load_data()

# ----------------- SIDEBAR FILTERS & ACTIONS -----------------
st.sidebar.image("https://img.icons8.com/nolan/96/artificial-intelligence.png", width=60)
st.sidebar.title("Pulse AI Platform")
st.sidebar.caption("Revenue Cycle Telemetry")

st.sidebar.subheader("Filters")
# Specialty Filter
specialties = ["All"] + sorted(df["specialty"].dropna().unique().tolist())
selected_specialty = st.sidebar.selectbox("Medical Specialty", specialties)

# Payer Filter
payers = ["All"] + sorted(df["payer_id_enc"].dropna().unique().tolist())
selected_payer = st.sidebar.selectbox("Insurance Payer", payers)

# Model Filter
models = ["All"] + sorted(df["ai_model_version"].dropna().unique().tolist())
selected_model = st.sidebar.selectbox("AI Model Version", models)

# Date Filter
min_date = df["visit_date"].min().date()
max_date = df["visit_date"].max().date()
selected_dates = st.sidebar.slider("Date Range", min_value=min_date, max_value=max_date, value=(min_date, max_date))

# Filter DataFrame
filtered_df = df[
    (df["visit_date"].dt.date >= selected_dates[0]) & 
    (df["visit_date"].dt.date <= selected_dates[1])
]
if selected_specialty != "All":
    filtered_df = filtered_df[filtered_df["specialty"] == selected_specialty]
if selected_payer != "All":
    filtered_df = filtered_df[filtered_df["payer_id_enc"] == selected_payer]
if selected_model != "All":
    filtered_df = filtered_df[filtered_df["ai_model_version"] == selected_model]

st.sidebar.subheader("Actions")
if st.sidebar.button("Trigger Live Simulation Run"):
    import requests
    try:
        # Run simulation step directly
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        from src.api.main import get_db
        # We can simulate inline to avoid network dependencies
        from fastapi import FastAPI
        # Call simulation logic locally to update DB safely
        from src.api.main import run_simulation_step
        db_gen = next(get_db())
        res = run_simulation_step(db_gen)
        st.sidebar.success(f"Success! Created Encounter: {res['encounter_id']}")
        # Reload dataset
        df, encounters, ai_logs, audit_logs, claims = load_data()
        st.experimental_rerun()
    except Exception as e:
        st.sidebar.error(f"Error triggering simulation: {e}")

# ----------------- MAIN LAYOUT & TABS -----------------
st.title("⚡ Pulse AI - Autonomous RCM Command Center")
st.markdown("Real-time telemetry, confidence calibration, denial intelligence, and A/B billing analysis.")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📈 Executive RCM",
    "🎯 AI Calibration",
    "❌ Denial Analytics",
    "💸 Revenue Leakage",
    "🧑‍💻 Auditor Workload",
    "🔬 Experiment Results",
    "📘 KPI Definitions"
])

# ----------------- TAB 1: EXECUTIVE RCM -----------------
with tab1:
    st.subheader("Key Performance Indicators")
    
    total_enc = len(filtered_df)
    total_charges = filtered_df["charge_amount"].sum()
    total_paid = filtered_df["paid_amount"].sum()
    leakage = total_charges - total_paid
    leakage_pct = (leakage / total_charges * 100) if total_charges > 0 else 0
    
    # Denial rate
    denied_claims = len(filtered_df[filtered_df["status"] == "denied"])
    denial_rate = (denied_claims / total_enc * 100) if total_enc > 0 else 0
    
    # Automation rate
    auto_billed = len(filtered_df[filtered_df["action_taken"] == "auto_billed"])
    automation_rate = (auto_billed / total_enc * 100) if total_enc > 0 else 0
    
    # Clean Claim Rate (Paid and auto-billed)
    clean_claims = len(filtered_df[(filtered_df["status"] == "paid") & (filtered_df["action_taken"] == "auto_billed")])
    clean_claim_rate = (clean_claims / total_enc * 100) if total_enc > 0 else 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Automation Rate", f"{automation_rate:.1f}%", help="Claims routed directly to billing without auditor review")
    col2.metric("Payer Denial Rate", f"{denial_rate:.1f}%", help="Percentage of total claims denied by payer")
    col3.metric("Clean Claim Rate", f"{clean_claim_rate:.1f}%", help="Claims paid successfully without manual audit intervention")
    col4.metric("Total Payments", f"${total_paid:,.2f}")
    col5.metric("Revenue Leakage", f"${leakage:,.2f}", f"{leakage_pct:.1f}% Leakage", delta_color="inverse")
    
    # Billing timelines
    st.markdown("### Financial Trends")
    timeline_df = filtered_df.groupby(filtered_df["visit_date"].dt.date).agg(
        charges=("charge_amount", "sum"),
        payments=("paid_amount", "sum")
    ).reset_index()
    
    fig_timeline = px.line(
        timeline_df, 
        x="visit_date", 
        y=["charges", "payments"], 
        labels={"value": "Amount ($)", "visit_date": "Date"},
        title="Charge Capture vs Payments Received Over Time",
        color_discrete_sequence=["#818cf8", "#38bdf8"],
        template="plotly_dark"
    )
    st.plotly_chart(fig_timeline, use_container_width=True)

# ----------------- TAB 2: AI CONFIDENCE CALIBRATION -----------------
with tab2:
    st.subheader("Model Confidence & Calibration")
    st.markdown("Evaluate how the AI model's self-assessed confidence correlates with its actual ground-truth coding accuracy.")
    
    col_cal_left, col_cal_right = st.columns(2)
    
    with col_cal_left:
        # Confidence score distribution
        fig_conf = px.histogram(
            filtered_df, 
            x="confidence_score", 
            nbins=20,
            title="Distribution of AI Confidence Scores",
            color_discrete_sequence=["#818cf8"],
            template="plotly_dark"
        )
        st.plotly_chart(fig_conf, use_container_width=True)
        
    with col_cal_right:
        # Bin confidence and compute accuracy
        filtered_df["conf_bin"] = pd.cut(filtered_df["confidence_score"], bins=np.arange(0, 1.05, 0.1))
        calib = filtered_df.groupby("conf_bin").agg(
            total=("encounter_id", "count"),
            accurate=("is_accurate", "sum")
        ).reset_index()
        
        # Calculate midpoints for display
        calib["midpoint"] = calib["conf_bin"].apply(lambda x: x.mid)
        calib["accuracy"] = calib["accurate"] / calib["total"]
        calib = calib.dropna()
        
        fig_calib = px.scatter(
            calib, 
            x="midpoint", 
            y="accuracy", 
            size="total",
            trendline="ols",
            title="Calibration Curve (Confidence vs Ground-Truth Accuracy)",
            labels={"midpoint": "Confidence Level", "accuracy": "Coding Accuracy"},
            color_discrete_sequence=["#38bdf8"],
            template="plotly_dark"
        )
        st.plotly_chart(fig_calib, use_container_width=True)

# ----------------- TAB 3: DENIAL REASON BREAKDOWN -----------------
with tab3:
    st.subheader("Denial Intelligence & Categorization")
    
    denied_df = filtered_df[filtered_df["status"] == "denied"]
    if len(denied_df) == 0:
        st.warning("No payer denials match the current filter selection.")
    else:
        col_den_1, col_den_2 = st.columns(2)
        with col_den_1:
            reasons = denied_df.groupby("denial_reason").agg(
                count=("encounter_id", "count"),
                charges=("charge_amount", "sum")
            ).reset_index().sort_values(by="count", ascending=True)
            
            fig_reasons = px.bar(
                reasons, 
                y="denial_reason", 
                x="count", 
                orientation="h",
                title="Denial Reasons Count",
                color_discrete_sequence=["#f87171"],
                template="plotly_dark"
            )
            st.plotly_chart(fig_reasons, use_container_width=True)
            
        with col_den_2:
            payer_denials = denied_df.groupby("payer_id_claim").size().reset_index(name="denials")
            fig_payer = px.pie(
                payer_denials,
                values="denials",
                names="payer_id_claim",
                title="Denial Distribution by Payer",
                color_discrete_sequence=px.colors.sequential.Plasma,
                template="plotly_dark"
            )
            st.plotly_chart(fig_payer, use_container_width=True)

# ----------------- TAB 4: REVENUE LEAKAGE EXPLORER -----------------
with tab4:
    st.subheader("Revenue Leakage Analysis")
    st.markdown("Identify areas where clinical charges are not fully recovered due to denials and coding errors.")
    
    col_leak_1, col_leak_2 = st.columns(2)
    
    with col_leak_1:
        specialty_leak = filtered_df.groupby("specialty").agg(
            charges=("charge_amount", "sum"),
            payments=("paid_amount", "sum")
        ).reset_index()
        specialty_leak["leakage"] = specialty_leak["charges"] - specialty_leak["payments"]
        specialty_leak["leakage_pct"] = (specialty_leak["leakage"] / specialty_leak["charges"] * 100)
        
        fig_spec_leak = px.bar(
            specialty_leak.sort_values(by="leakage", ascending=False),
            x="specialty",
            y="leakage",
            title="Revenue Leakage ($) by Medical Specialty",
            color_discrete_sequence=["#fb923c"],
            template="plotly_dark"
        )
        st.plotly_chart(fig_spec_leak, use_container_width=True)
        
    with col_leak_2:
        payer_leak = filtered_df.groupby("payer_id_enc").agg(
            charges=("charge_amount", "sum"),
            payments=("paid_amount", "sum")
        ).reset_index()
        payer_leak["leakage"] = payer_leak["charges"] - payer_leak["payments"]
        
        fig_payer_leak = px.bar(
            payer_leak.sort_values(by="leakage", ascending=False),
            x="payer_id_enc",
            y="leakage",
            title="Revenue Leakage ($) by Insurance Payer",
            color_discrete_sequence=["#f472b6"],
            template="plotly_dark"
        )
        st.plotly_chart(fig_payer_leak, use_container_width=True)

# ----------------- TAB 5: AUDITOR WORKLOAD -----------------
with tab5:
    st.subheader("Auditor Productivity & Queue Latency")
    st.markdown("Human-in-the-loop audit metrics for claims routed due to low AI confidence (<0.75).")
    
    audited_df = filtered_df[filtered_df["action_taken"] == "routed_to_audit"]
    
    if len(audited_df) == 0:
        st.warning("No audited claims found under the active filter configuration.")
    else:
        auditor_metrics = audited_df.groupby("auditor_id").agg(
            total_reviews=("encounter_id", "count"),
            avg_duration=("audit_duration_seconds", "mean"),
            corrections=("decision", lambda x: (x == "corrected").sum())
        ).reset_index()
        
        auditor_metrics["correction_rate"] = (auditor_metrics["corrections"] / auditor_metrics["total_reviews"] * 100)
        
        col_aud_1, col_aud_2 = st.columns(2)
        
        with col_aud_1:
            fig_dur = px.bar(
                auditor_metrics.sort_values(by="avg_duration"),
                x="auditor_id",
                y="avg_duration",
                title="Average Audit Review Time (Seconds)",
                color_discrete_sequence=["#34d399"],
                template="plotly_dark"
            )
            st.plotly_chart(fig_dur, use_container_width=True)
            
        with col_aud_2:
            st.markdown("### Auditor Performance Summary")
            st.dataframe(
                auditor_metrics.style.format({
                    "avg_duration": "{:.1f}s",
                    "correction_rate": "{:.1f}%"
                }),
                use_container_width=True
            )

# ----------------- TAB 6: EXPERIMENT RESULTS -----------------
with tab6:
    st.subheader("A/B Billing Workflow Experimentation")
    st.markdown("Analysis of the active A/B test: **Control Group (v1.8 Coder)** vs **Treatment Group (v2.1 Coder)**.")
    
    # Calculate group-level statistics
    ab_stats = filtered_df.groupby("ai_model_version").agg(
        total_claims=("encounter_id", "count"),
        auto_billed=("action_taken", lambda x: (x == "auto_billed").sum()),
        accurate_predictions=("is_accurate", "sum"),
        denied_claims=("status", lambda x: (x == "denied").sum()),
        total_charges=("charge_amount", "sum"),
        total_paid=("paid_amount", "sum")
    ).reset_index()
    
    ab_stats["automation_rate"] = (ab_stats["auto_billed"] / ab_stats["total_claims"] * 100)
    ab_stats["accuracy_rate"] = (ab_stats["accurate_predictions"] / ab_stats["total_claims"] * 100)
    ab_stats["denial_rate"] = (ab_stats["denied_claims"] / ab_stats["total_claims"] * 100)
    ab_stats["leakage_rate"] = (1 - (ab_stats["total_paid"] / ab_stats["total_charges"])) * 100
    
    st.dataframe(
        ab_stats.style.format({
            "total_charges": "${:,.2f}",
            "total_paid": "${:,.2f}",
            "automation_rate": "{:.2f}%",
            "accuracy_rate": "{:.2f}%",
            "denial_rate": "{:.2f}%",
            "leakage_rate": "{:.2f}%"
        }),
        use_container_width=True
    )
    
    st.markdown("### Statistical Significance Checks")
    
    from statsmodels.stats.proportion import proportions_ztest
    
    # Extract cohorts
    group_names = ab_stats["ai_model_version"].tolist()
    if len(group_names) >= 2:
        n_a, n_b = ab_stats["total_claims"].iloc[0], ab_stats["total_claims"].iloc[1]
        
        # Test 1: Denial Rate Significance
        den_a, den_b = ab_stats["denied_claims"].iloc[0], ab_stats["denied_claims"].iloc[1]
        stat_den, p_den = proportions_ztest([den_a, den_b], [n_a, n_b])
        
        # Test 2: Automation Rate Significance
        auto_a, auto_b = ab_stats["auto_billed"].iloc[0], ab_stats["auto_billed"].iloc[1]
        stat_auto, p_auto = proportions_ztest([auto_a, auto_b], [n_a, n_b])
        
        c_sig_1, c_sig_2 = st.columns(2)
        with c_sig_1:
            st.metric(
                label="Payer Denial Rate p-value",
                value=f"{p_den:.4f}",
                delta="Statistically Significant" if p_den < 0.05 else "Not Significant",
                delta_color="normal" if p_den < 0.05 else "off"
            )
            st.info(f"Comparing denial rates: **{ab_stats['denial_rate'].iloc[0]:.2f}%** vs **{ab_stats['denial_rate'].iloc[1]:.2f}%**.")
            
        with c_sig_2:
            st.metric(
                label="AI Automation Rate p-value",
                value=f"{p_auto:.4f}",
                delta="Statistically Significant" if p_auto < 0.05 else "Not Significant",
                delta_color="normal" if p_auto < 0.05 else "off"
            )
            st.info(f"Comparing automation rates: **{ab_stats['automation_rate'].iloc[0]:.2f}%** vs **{ab_stats['automation_rate'].iloc[1]:.2f}%**.")
    else:
        st.warning("Not enough data to calculate A/B test proportions. Please backfill or select 'All' models.")

# ----------------- TAB 7: KPI DEFINITIONS -----------------
with tab7:
    st.subheader("RCM Metric Reference Guide")
    
    st.markdown(
        """
        - **AI Automation Rate**: Percentage of overall patient visits processed, coded, and submitted autonomously without human auditor intervention.
        - **Clean Claim Rate**: The proportion of medical billing claims submitted and paid in full by insurance companies on the first attempt without corrections or prior denials.
        - **Payer Denial Rate**: The percentage of claims rejected or unpaid by payers relative to total claims submitted.
        - **Revenue Leakage**: Unrecovered cash due to insurance claim denials, lower contractual allowed rates, and coding errors.
        - **AI Accuracy**: Ratio of AI-predicted ICD-10 and CPT codes matching the clinician's ground-truth codes exactly.
        - **Auditor Correction Rate**: Percentage of claims reviewed by human auditors where the AI-predicted codes were altered.
        """
    )
