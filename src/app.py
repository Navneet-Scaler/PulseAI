import os
import sqlite3
import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, date

# Set page config with professional high-density terminal theme styling
st.set_page_config(
    page_title="PULSE RCM OPERATIONAL TERMINAL",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Bloomberg/Palantir High-Density Terminal Styling
st.markdown(
    """
    <style>
    /* Global Terminal Background and Monospace Font Setup */
    .stApp {
        background-color: #000000;
        color: #d1d5db;
        font-family: "Consolas", "Courier New", "Roboto Mono", monospace;
    }
    
    /* Terminal Header Font Styling */
    h1, h2, h3, h4, h5, h6 {
        font-family: "Consolas", "Courier New", "Roboto Mono", monospace;
        color: #ff9900 !important; /* Bloomberg Amber */
        font-weight: bold;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        border-bottom: 1px solid #222222;
        padding-bottom: 6px;
    }
    
    /* High-Density Terminal Metric Cards */
    div[data-testid="metric-container"] {
        background-color: #080c10;
        border: 1px solid #333333;
        border-radius: 0px; /* Hard borders */
        padding: 8px 12px;
        box-shadow: none;
    }
    
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 22px;
        font-weight: bold;
        color: #00ff66; /* Neon Green */
        font-family: "Consolas", "Courier New", "Roboto Mono", monospace;
    }
    
    div[data-testid="metric-container"] [data-testid="stMetricLabel"] {
        font-size: 11px;
        color: #888888;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Customize Amber Metrics for warning variables (Denial, Leakage) */
    div[data-testid="metric-container"]:nth-of-type(2) [data-testid="stMetricValue"],
    div[data-testid="metric-container"]:nth-of-type(5) [data-testid="stMetricValue"] {
        color: #ff9900 !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #05070a;
        border-right: 1px solid #222222;
    }
    
    /* Tab Navigation - Terminal Style */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        border-bottom: 1px solid #333333;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #080c10;
        border: 1px solid #222222;
        border-radius: 0px;
        padding: 8px 14px;
        color: #888888;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 12px;
        text-transform: uppercase;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #111b24 !important;
        border-color: #ff9900 !important;
        color: #ff9900 !important;
    }
    
    /* Clean Terminal Table Styling */
    .stDataFrame {
        border: 1px solid #222222;
    }
    </style>
    """,
    unsafe_allow_html=True
)

DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///pulse_ai.db").replace("sqlite:///", "")

# Verify database exists and has data, if not backfill it
if not os.path.exists(DB_PATH):
    st.info("Database instance not found. Re-initializing telemetry dataset...")
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
st.sidebar.markdown("<h3 style='color: #ff9900; margin-top: 0px;'>PULSE OPERATIONAL MODULE</h3>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='color: #888888; font-size: 11px; margin-bottom: 20px;'>TELEMETRY MONITOR V4.1</div>", unsafe_allow_html=True)

st.sidebar.subheader("FILTERS")
# Specialty Filter
specialties = ["All Specialties"] + sorted(df["specialty"].dropna().unique().tolist())
selected_specialty = st.sidebar.selectbox("Medical Specialty", specialties)

# Payer Filter
payers = ["All Payers"] + sorted(df["payer_id_enc"].dropna().unique().tolist())
selected_payer = st.sidebar.selectbox("Insurance Payer", payers)

# Model Filter
models = ["All Models"] + sorted(df["ai_model_version"].dropna().unique().tolist())
selected_model = st.sidebar.selectbox("AI Model Version", models)

# Date Filter
min_date = df["visit_date"].min().date()
max_date = df["visit_date"].max().date()
selected_dates = st.sidebar.slider("Date Range Selection", min_value=min_date, max_value=max_date, value=(min_date, max_date))

# Filter DataFrame
filtered_df = df[
    (df["visit_date"].dt.date >= selected_dates[0]) & 
    (df["visit_date"].dt.date <= selected_dates[1])
]
if selected_specialty != "All Specialties":
    filtered_df = filtered_df[filtered_df["specialty"] == selected_specialty]
if selected_payer != "All Payers":
    filtered_df = filtered_df[filtered_df["payer_id_enc"] == selected_payer]
if selected_model != "All Models":
    filtered_df = filtered_df[filtered_df["ai_model_version"] == selected_model]

st.sidebar.subheader("COMMANDS")
if st.sidebar.button("Run Simulation Step"):
    try:
        from src.api.main import get_db, run_simulation_step
        db_gen = next(get_db())
        res = run_simulation_step(db_gen)
        st.sidebar.success(f"Encounter: {res['encounter_id']}")
        # Reload dataset
        df, encounters, ai_logs, audit_logs, claims = load_data()
        st.experimental_rerun()
    except Exception as e:
        st.sidebar.error(f"Simulation failed: {e}")

# ----------------- MAIN LAYOUT & TABS -----------------
st.markdown("<h2 style='color: #ff9900; margin-bottom: 0px;'>PULSE RCM ANALYTICS SYSTEM</h2>", unsafe_allow_html=True)
st.markdown("<div style='color: #888888; font-size: 12px; margin-bottom: 24px;'>SECURE TELEMETRY LINK ESTABLISHED</div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "EXECUTIVE OVERVIEW",
    "AI CONFIDENCE CALIBRATION",
    "DENIAL ANALYSIS",
    "REVENUE LEAKAGE EXPLORER",
    "AUDITOR PERFORMANCE",
    "A/B WORKFLOW EVALUATION",
    "METRICS REFERENCE"
])

# ----------------- TAB 1: EXECUTIVE OVERVIEW -----------------
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
    col1.metric("Automation Rate", f"{automation_rate:.1f}%")
    col2.metric("Payer Denial Rate", f"{denial_rate:.1f}%")
    col3.metric("Clean Claim Rate", f"{clean_claim_rate:.1f}%")
    col4.metric("Total Payments", f"${total_paid:,.2f}")
    col5.metric("Revenue Leakage", f"${leakage:,.2f}", f"{leakage_pct:.1f}% leakage", delta_color="inverse")
    
    # Billing timelines
    st.markdown("### Financial Performance Trends")
    timeline_df = filtered_df.groupby(filtered_df["visit_date"].dt.date).agg(
        charges=("charge_amount", "sum"),
        payments=("paid_amount", "sum")
    ).reset_index()
    
    fig_timeline = px.line(
        timeline_df, 
        x="visit_date", 
        y=["charges", "payments"], 
        labels={"value": "Amount ($)", "visit_date": "Date", "variable": "Metric"},
        title="Charge Capture vs Payments Received Over Time",
        color_discrete_sequence=["#00ff66", "#ff9900"],
        template="plotly_dark"
    )
    fig_timeline.update_layout(
        plot_bgcolor="#000000",
        paper_bgcolor="#000000",
        font_family="Consolas, monospace"
    )
    st.plotly_chart(fig_timeline, use_container_width=True)

# ----------------- TAB 2: AI CONFIDENCE CALIBRATION -----------------
with tab2:
    st.subheader("Model Calibration Analysis")
    st.markdown("Correlation between the AI model's internal confidence estimation and ground-truth coding accuracy.")
    
    col_cal_left, col_cal_right = st.columns(2)
    
    with col_cal_left:
        fig_conf = px.histogram(
            filtered_df, 
            x="confidence_score", 
            nbins=20,
            title="Distribution of AI Confidence Scores",
            labels={"confidence_score": "Confidence Score", "count": "Frequency"},
            color_discrete_sequence=["#ff9900"],
            template="plotly_dark"
        )
        fig_conf.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000")
        st.plotly_chart(fig_conf, use_container_width=True)
        
    with col_cal_right:
        filtered_df["conf_bin"] = pd.cut(filtered_df["confidence_score"], bins=np.arange(0, 1.05, 0.1))
        calib = filtered_df.groupby("conf_bin").agg(
            total=("encounter_id", "count"),
            accurate=("is_accurate", "sum")
        ).reset_index()
        
        calib["midpoint"] = calib["conf_bin"].apply(lambda x: x.mid)
        calib["accuracy"] = calib["accurate"] / calib["total"]
        calib = calib.dropna()
        
        fig_calib = px.scatter(
            calib, 
            x="midpoint", 
            y="accuracy", 
            size="total",
            trendline="ols",
            title="Calibration Curve (Estimated Confidence vs Ground-Truth Accuracy)",
            labels={"midpoint": "Confidence Level", "accuracy": "Measured Accuracy"},
            color_discrete_sequence=["#00ff66"],
            template="plotly_dark"
        )
        fig_calib.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000")
        st.plotly_chart(fig_calib, use_container_width=True)

# ----------------- TAB 3: DENIAL ANALYSIS -----------------
with tab3:
    st.subheader("Denial Intelligence Summary")
    
    denied_df = filtered_df[filtered_df["status"] == "denied"]
    if len(denied_df) == 0:
        st.warning("No payer denials match the selected filter configuration.")
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
                title="Denial Reasons Frequency",
                labels={"count": "Frequency", "denial_reason": "Payer Denial Code"},
                color_discrete_sequence=["#ff3333"],
                template="plotly_dark"
            )
            fig_reasons.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000")
            st.plotly_chart(fig_reasons, use_container_width=True)
            
        with col_den_2:
            payer_denials = denied_df.groupby("payer_id_claim").size().reset_index(name="denials")
            fig_payer = px.pie(
                payer_denials,
                values="denials",
                names="payer_id_claim",
                title="Denial Distribution by Payer Cohort",
                color_discrete_sequence=px.colors.sequential.Gray_r,
                template="plotly_dark"
            )
            fig_payer.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000")
            st.plotly_chart(fig_payer, use_container_width=True)

# ----------------- TAB 4: REVENUE LEAKAGE EXPLORER -----------------
with tab4:
    st.subheader("Revenue Leakage Attribution")
    st.markdown("Isolation of billing anomalies resulting in lost or deferred payouts.")
    
    col_leak_1, col_leak_2 = st.columns(2)
    
    with col_leak_1:
        specialty_leak = filtered_df.groupby("specialty").agg(
            charges=("charge_amount", "sum"),
            payments=("paid_amount", "sum")
        ).reset_index()
        specialty_leak["leakage"] = specialty_leak["charges"] - specialty_leak["payments"]
        
        fig_spec_leak = px.bar(
            specialty_leak.sort_values(by="leakage", ascending=False),
            x="specialty",
            y="leakage",
            title="Revenue Leakage ($) by Specialty Area",
            labels={"leakage": "Unrecovered Amount ($)", "specialty": "Clinical Division"},
            color_discrete_sequence=["#ff9900"],
            template="plotly_dark"
        )
        fig_spec_leak.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000")
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
            title="Revenue Leakage ($) by Underwriter/Payer",
            labels={"leakage": "Unrecovered Amount ($)", "payer_id_enc": "Insurance Payer"},
            color_discrete_sequence=["#888888"],
            template="plotly_dark"
        )
        fig_payer_leak.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000")
        st.plotly_chart(fig_payer_leak, use_container_width=True)

# ----------------- TAB 5: AUDITOR PERFORMANCE -----------------
with tab5:
    st.subheader("Human-in-the-Loop Productivity Analytics")
    st.markdown("Verification metrics for claims routed to human audit due to sub-threshold AI confidence (<0.75).")
    
    audited_df = filtered_df[filtered_df["action_taken"] == "routed_to_audit"]
    
    if len(audited_df) == 0:
        st.warning("No audited claims located under the current configuration.")
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
                title="Mean Processing Duration (Seconds)",
                labels={"avg_duration": "Duration (s)", "auditor_id": "Auditor ID"},
                color_discrete_sequence=["#00ff66"],
                template="plotly_dark"
            )
            fig_dur.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000")
            st.plotly_chart(fig_dur, use_container_width=True)
            
        with col_aud_2:
            st.markdown("### Auditor Performance Ledger")
            st.dataframe(
                auditor_metrics.style.format({
                    "avg_duration": "{:.1f}s",
                    "correction_rate": "{:.1f}%"
                }),
                use_container_width=True
            )

# ----------------- TAB 6: A/B WORKFLOW EVALUATION -----------------
with tab6:
    st.subheader("Statistical Cohort Comparison")
    st.markdown("Significance testing of Control Group (v1.8 Coder) vs Treatment Group (v2.1 Coder).")
    
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
    
    st.markdown("### Two-Proportion Z-Test Significance Checks")
    
    from statsmodels.stats.proportion import proportions_ztest
    
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
                delta="Significant Change" if p_den < 0.05 else "Insignificant Variance",
                delta_color="normal" if p_den < 0.05 else "off"
            )
            st.info(f"Comparing denial rates: **{ab_stats['denial_rate'].iloc[0]:.2f}%** vs **{ab_stats['denial_rate'].iloc[1]:.2f}%**.")
            
        with c_sig_2:
            st.metric(
                label="AI Automation Rate p-value",
                value=f"{p_auto:.4f}",
                delta="Significant Change" if p_auto < 0.05 else "Insignificant Variance",
                delta_color="normal" if p_auto < 0.05 else "off"
            )
            st.info(f"Comparing automation rates: **{ab_stats['automation_rate'].iloc[0]:.2f}%** vs **{ab_stats['automation_rate'].iloc[1]:.2f}%**.")
    else:
        st.warning("Insufficient data available to compute proportional significance. Please populate or check filters.")

# ----------------- TAB 7: METRICS REFERENCE -----------------
with tab7:
    st.subheader("Standard RCM Terminology Reference Guide")
    
    st.markdown(
        """
        * **Automation Rate**: The proportion of medical visits processed and submitted to insurance underwriters without requiring human coder or auditor adjustment.
        * **Clean Claim Rate**: The proportion of submitted insurance billing files successfully cleared and resolved on initial transmission, requiring no secondary correction or denial mitigation.
        * **Denial Rate**: Total rejected or unpaid medical claims divided by the total number of claims submitted within a specified timeframe.
        * **Revenue Leakage**: Total financial shortfall resulting from insurer underpayments, coding errors, or resolved payment rejections.
        * **AI Diagnostic Accuracy**: Percentage of AI-assigned diagnosis (ICD-10) and procedure (CPT) codes that exactly match correct clinician clinical codes.
        * **Auditor Correction Rate**: Ratio of claims where human auditing modifications were required to correct AI coding predictions.
        """
    )
