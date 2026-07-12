import os
import sqlite3
import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, date

# Set page config with professional high-contrast dark theme styling
st.set_page_config(
    page_title="Pulse AI RCM Intelligence Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Contrast Dark Slate Corporate Styling
st.markdown(
    """
    <style>
    /* Global Background and Typography Setup */
    .stApp {
        background-color: #0b0f19; /* Deep Dark Slate */
        color: #f3f4f6; /* High Contrast Off-White */
        font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
    }
    
    /* Clean Premium Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
        color: #ffffff;
        font-weight: 600;
        letter-spacing: -0.02em;
        border-bottom: 1px solid #1f2937;
        padding-bottom: 10px;
        margin-top: 24px;
        margin-bottom: 14px;
    }
    
    /* Clean Premium Metric Cards with larger size allowance */
    div[data-testid="metric-container"] {
        background-color: #111827; /* Dark Grey/Slate */
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 20px !important; /* Slightly smaller for multi-digit data visibility */
        font-weight: 700;
        color: #60a5fa !important; /* Crisp Sky Blue */
        white-space: nowrap !important;
        overflow: visible !important;
    }
    
    div[data-testid="metric-container"] [data-testid="stMetricLabel"] {
        font-size: 11px;
        color: #9ca3af;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #030712;
        border-right: 1px solid #1f2937;
    }
    
    section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span {
        color: #ffffff !important;
    }
    
    section[data-testid="stSidebar"] label {
        color: #9ca3af !important;
    }
    
    /* Minimalist Tab Navigation */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #1f2937;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: none;
        padding: 12px 20px;
        color: #9ca3af;
        font-weight: 600;
        font-size: 14px;
        transition: color 0.15s ease-in-out;
    }
    
    .stTabs [aria-selected="true"] {
        border-bottom: 2px solid #3b82f6 !important;
        color: #3b82f6 !important;
        background-color: transparent !important;
    }
    
    /* Business Inference Block Styling */
    .inference-block {
        background-color: #111827;
        border-left: 4px solid #3b82f6;
        padding: 18px;
        border-radius: 0 8px 8px 0;
        margin-top: 26px;
        margin-bottom: 26px;
        border-top: 1px solid #1f2937;
        border-right: 1px solid #1f2937;
        border-bottom: 1px solid #1f2937;
    }
    
    .inference-title {
        font-weight: 700;
        color: #ffffff;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    
    .inference-text {
        font-size: 14px;
        color: #d1d5db;
        line-height: 1.6;
    }
    </style>
    """,
    unsafe_allow_html=True
)

DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///pulse_ai.db").replace("sqlite:///", "")

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
st.sidebar.subheader("PULSE RCM FILTER SUITE")

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

st.sidebar.subheader("SIMULATOR MODULE")
if st.sidebar.button("Run Simulation Step"):
    try:
        from src.api.main import run_simulation_step
        conn = sqlite3.connect(DB_PATH)
        res = run_simulation_step(conn)
        conn.close()
        # Modern toast notification that auto-fades
        st.toast(f"Claim simulation complete: {res['encounter_id']}", icon="✅")
        # Reload dataset
        df, encounters, ai_logs, audit_logs, claims = load_data()
        st.experimental_rerun()
    except Exception as e:
        st.sidebar.error(f"Simulation execution failed: {e}")

# ----------------- MAIN LAYOUT & TABS -----------------
st.title("Pulse Revenue Cycle Management Analytics Platform")
st.markdown("Real-time telemetry and validation center for automated healthcare billing systems.")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Executive Overview",
    "AI Confidence Calibration",
    "Denial Analysis",
    "Revenue Leakage Explorer",
    "Auditor Performance",
    "A/B Workflow Evaluation",
    "Metrics Reference"
])

# Helper function to generate inference section
def render_inference(title, text):
    st.markdown(
        f"""
        <div class="inference-block">
            <div class="inference-title">Layman Explanation & Business Inference</div>
            <div class="inference-text">
                <strong>{title}:</strong> {text}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

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
    
    # Days in Accounts Receivable (AR Days)
    # Formula: (Gross AR Outstanding / Gross Charges) * 30 days
    ar_days = (leakage / total_charges * 30) if total_charges > 0 else 0
    
    # Display in a 3x2 grid to prevent any value wrapping or clipping
    m_row1_col1, m_row1_col2, m_row1_col3 = st.columns(3)
    m_row1_col1.metric("AI Automation Rate", f"{automation_rate:.1f}%")
    m_row1_col2.metric("Payer Denial Rate", f"{denial_rate:.1f}%")
    m_row1_col3.metric("Clean Claim Rate (CCR)", f"{clean_claim_rate:.1f}%")
    
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    
    m_row2_col1, m_row2_col2, m_row2_col3 = st.columns(3)
    m_row2_col1.metric("Gross Billed Charges", f"${total_charges:,.2f}")
    m_row2_col2.metric("Total Payments Received", f"${total_paid:,.2f}")
    m_row2_col3.metric("Days Outstanding in AR (AR Days)", f"{ar_days:.1f} Days")
    
    # Billing timelines
    st.markdown("### Financial Performance Trends")
    timeline_df = filtered_df.groupby(filtered_df["visit_date"].dt.date).agg(
        charges=("charge_amount", "sum"),
        payments=("paid_amount", "sum")
    ).reset_index()
    
    fig_timeline = px.area(
        timeline_df, 
        x="visit_date", 
        y=["charges", "payments"], 
        labels={"value": "Amount ($)", "visit_date": "Date", "variable": "Metric"},
        title="Gross Charges Captured vs Net Payments Received (Daily)",
        color_discrete_sequence=["#3b82f6", "#10b981"],
        template="plotly_dark"
    )
    fig_timeline.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="-apple-system, BlinkMacSystemFont, sans-serif"
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    # AR Aging Buckets
    st.markdown("### Accounts Receivable (AR) Aging Buckets")
    
    # Calculate claim age based on visit date relative to current time
    today = pd.to_datetime(date.today())
    filtered_df["claim_age"] = (today - filtered_df["visit_date"]).dt.days
    
    # Group into buckets for outstanding/unrecovered revenue
    unpaid_claims = filtered_df[filtered_df["paid_amount"] == 0.0]
    
    def get_aging_bucket(age):
        if age <= 10:
            return "0-10 Days (Current)"
        elif age <= 20:
            return "11-20 Days (Deferred)"
        else:
            return "21+ Days (Delinquent)"
            
    unpaid_claims["aging_bucket"] = unpaid_claims["claim_age"].apply(get_aging_bucket)
    
    aging_data = unpaid_claims.groupby(["specialty", "aging_bucket"])["charge_amount"].sum().reset_index()
    
    fig_aging = px.bar(
        aging_data,
        x="specialty",
        y="charge_amount",
        color="aging_bucket",
        title="Unrecovered Accounts Receivable by Aging Bucket & Specialty",
        labels={"charge_amount": "Outstanding Amount ($)", "specialty": "Clinical Division", "aging_bucket": "AR Age Bucket"},
        color_discrete_sequence=["#2563eb", "#f59e0b", "#ef4444"],
        template="plotly_dark"
    )
    fig_aging.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_aging, use_container_width=True)
    
    render_inference(
        "Executive Dashboard Health Summary",
        f"We are observing a Clean Claim Rate of {clean_claim_rate:.1f}% alongside a Payer Denial Rate of {denial_rate:.1f}%. "
        f"The AR Days metric stands at {ar_days:.1f} days, indicating the average cycle length before billing assets are fully recovered. "
        f"Looking at our AR Aging Buckets, specialties with high volumes of '21+ Days (Delinquent)' claims represent immediate cash flow risks. "
        f"Strategic adjustments in coding auditing must focus on resolving these delinquent claims to release locked working capital."
    )

# ----------------- TAB 2: AI CONFIDENCE CALIBRATION -----------------
with tab2:
    st.subheader("Model Calibration Analysis & Threshold Optimizer")
    
    st.markdown("### Dynamic Confidence Threshold Optimization Simulation")
    st.write("Adjust the slider below to simulate how altering the routing threshold dynamically optimizes net revenue cycle payouts and auditor workloads.")
    
    # Add threshold tuning slider
    tuned_threshold = st.slider("Simulated Confidence Routing Threshold", min_value=0.50, max_value=0.95, value=0.75, step=0.01)
    
    # Perform dynamic calculations based on the selected slider threshold
    simulated_rows = []
    
    for idx, row in filtered_df.iterrows():
        conf = row["confidence_score"]
        is_accurate = row["is_accurate"]
        charge = row["charge_amount"]
        payer = row["payer_id_enc"]
        
        denial_prob = 0.15 if payer == "Payer_Medicare" else 0.22
        
        sim_routed = conf < tuned_threshold
        
        if sim_routed:
            sim_status = "denied" if np.random.RandomState(idx).random() < denial_prob else "paid"
        else:
            if not is_accurate:
                sim_status = "denied" if np.random.RandomState(idx).random() < 0.90 else "paid"
            else:
                sim_status = "denied" if np.random.RandomState(idx).random() < denial_prob else "paid"
                
        if sim_status == "paid":
            allowed_rate = 0.72
            sim_paid = round(charge * allowed_rate, 2)
        else:
            sim_paid = 0.0
            
        sim_rows = {
            "encounter_id": row["encounter_id"],
            "charge_amount": charge,
            "sim_routed": sim_routed,
            "sim_status": sim_status,
            "sim_paid": sim_paid
        }
        simulated_rows.append(sim_rows)
        
    sim_df = pd.DataFrame(simulated_rows)
    
    # Compute metrics
    sim_total_enc = len(sim_df)
    sim_audited = sim_df["sim_routed"].sum()
    sim_auto = sim_total_enc - sim_audited
    sim_automation_rate = (sim_auto / sim_total_enc * 100) if sim_total_enc > 0 else 0
    
    sim_denied = (sim_df["sim_status"] == "denied").sum()
    sim_denial_rate = (sim_denied / sim_total_enc * 100) if sim_total_enc > 0 else 0
    
    sim_payments = sim_df["sim_paid"].sum()
    auditor_cost = sim_audited * 5.00
    net_payout = sim_payments - auditor_cost
    
    col_sim_1, col_sim_2, col_sim_3, col_sim_4 = st.columns(4)
    col_sim_1.metric("Simulated Automation Rate", f"{sim_automation_rate:.1f}%")
    col_sim_2.metric("Simulated Payer Denial Rate", f"{sim_denial_rate:.1f}%")
    col_sim_3.metric("Total Auditor Cost ($5/claim)", f"${auditor_cost:,.2f}")
    col_sim_4.metric("Net Financial Payout (Net Revenue)", f"${net_payout:,.2f}")
    
    st.markdown("---")
    
    col_cal_left, col_cal_right = st.columns(2)
    
    with col_cal_left:
        fig_conf = px.histogram(
            filtered_df, 
            x="confidence_score", 
            nbins=20,
            title="Distribution of AI Confidence Scores",
            labels={"confidence_score": "Confidence Score", "count": "Frequency"},
            color_discrete_sequence=["#3b82f6"],
            template="plotly_dark"
        )
        fig_conf.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
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
            color_discrete_sequence=["#10b981"],
            template="plotly_dark"
        )
        fig_calib.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_calib, use_container_width=True)
        
    render_inference(
        "Confidence and Calibration Insights",
        "The calibration curve plots how accurate the AI system is at different levels of estimated confidence. "
        "A perfectly calibrated model will align with the diagonal line (e.g. 80% confidence yields 80% accuracy). "
        "The OLS trendline shows whether the model is overconfident or underconfident. Our current calibration indicates "
        "that claims with confidence above 0.75 are highly accurate, justifying their automatic submission without audit. "
        "Conversely, claims falling below 0.75 carry significant error rates, validating the human-in-the-loop routing threshold."
    )

# ----------------- TAB 3: DENIAL ANALYSIS -----------------
with tab3:
    st.subheader("Denial Intelligence Summary & Heatmaps")
    
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
                color_discrete_sequence=["#ef4444"],
                template="plotly_dark"
            )
            fig_reasons.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_reasons, use_container_width=True)
            
        with col_den_2:
            payer_denials = denied_df.groupby("payer_id_claim").size().reset_index(name="denials")
            fig_payer = px.pie(
                payer_denials,
                values="denials",
                names="payer_id_claim",
                title="Denial Distribution by Payer Cohort",
                color_discrete_sequence=px.colors.sequential.Agsunset,
                template="plotly_dark"
            )
            fig_payer.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_payer, use_container_width=True)
            
        # Payer Rules & Denial Heatmap
        st.markdown("### Payer Denial Reason Heatmap Correlation")
        heatmap_data = denied_df.groupby(["payer_id_claim", "denial_reason"]).size().unstack(fill_value=0)
        
        fig_heat = px.imshow(
            heatmap_data,
            labels=dict(x="Denial Reason", y="Insurance Payer", color="Denials count"),
            x=heatmap_data.columns,
            y=heatmap_data.index,
            color_continuous_scale="Reds",
            title="Correlation Heatmap: Payers vs Denial Categories",
            template="plotly_dark"
        )
        fig_heat.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_heat, use_container_width=True)
        
        # High-Impact Code Mismatch Matrix
        st.markdown("### High-Impact AI Code Mismatches (Coding Leakage Hotspots)")
        
        mismatch_df = filtered_df[(filtered_df["is_accurate"] == False) & (filtered_df["action_taken"] == "auto_billed")]
        if len(mismatch_df) > 0:
            mismatch_summary = mismatch_df.groupby(["specialty", "correct_icd10", "predicted_icd10"]).agg(
                claims_count=("encounter_id", "count"),
                total_loss=("charge_amount", "sum")
            ).reset_index().sort_values(by="total_loss", ascending=False).head(5)
            
            st.dataframe(mismatch_summary, use_container_width=True)
        else:
            st.info("No AI coding mismatches detected in auto-billed claims.")
            
    render_inference(
        "Insurance Payer Denial Analysis",
        "This breakdown isolates the specific friction points preventing claim reimbursement. "
        "High volumes of 'Incorrect Coding Mismatch' rejections suggest that coding errors are bypassing our validation checks. "
        "In contrast, denials like 'Prior Authorization Required' reflect administrative gaps rather than coding mistakes. "
        "Focus training or system updates on addressing the top-ranking denial reason to achieve the fastest drop in denials."
    )

# ----------------- TAB 4: REVENUE LEAKAGE EXPLORER -----------------
with tab4:
    st.subheader("Revenue Leakage Attribution & Underpayment Audit")
    
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
            color_discrete_sequence=["#f59e0b"],
            template="plotly_dark"
        )
        fig_spec_leak.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
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
            color_discrete_sequence=["#ec4899"],
            template="plotly_dark"
        )
        fig_payer_leak.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_payer_leak, use_container_width=True)
        
    # Advanced Underpayment Audit
    st.markdown("### Contractual Underpayment Analysis (Expected vs Actual Payments)")
    underpaid_claims = filtered_df[(filtered_df["status"] == "paid") & (filtered_df["paid_amount"] < filtered_df["allowed_amount"])]
    if len(underpaid_claims) > 0:
        underpaid_summary = underpaid_claims.groupby(["payer_id_claim", "specialty"]).agg(
            underpaid_count=("encounter_id", "count"),
            expected_allowed_avg=("allowed_amount", "mean"),
            actual_paid_avg=("paid_amount", "mean"),
            total_underpaid_leakage=("allowed_amount", lambda x: (x - underpaid_claims.loc[x.index, "paid_amount"]).sum())
        ).reset_index().sort_values(by="total_underpaid_leakage", ascending=False).head(5)
        
        st.dataframe(
            underpaid_summary.style.format({
                "expected_allowed_avg": "${:,.2f}",
                "actual_paid_avg": "${:,.2f}",
                "total_underpaid_leakage": "${:,.2f}"
            }),
            use_container_width=True
        )
    else:
        st.info("No underpaid contract claims located in the dataset.")
        
    render_inference(
        "Leakage and Underwriter Payout Gaps",
        "Revenue leakage represents the difference between the dollar amount billed to insurance and the amount received. "
        "By dividing this metric by clinical specialty and insurance underwriter, we can isolate underperforming areas. "
        "The contractual underpayment analysis identifies cases where insurers paid less than the contracted allowed rate, "
        "which requires recovery review from contract compliance officers."
    )

# ----------------- TAB 5: AUDITOR PERFORMANCE -----------------
with tab5:
    st.subheader("Human-in-the-Loop Productivity & ROI Analytics")
    
    audited_df = filtered_df[filtered_df["action_taken"] == "routed_to_audit"]
    
    if len(audited_df) == 0:
        st.warning("No audited claims located under the current configuration.")
    else:
        # Calculate Human Auditor ROI
        # Revenue recovered: Charges corrected * 72% allowed rate
        corrected_df = audited_df[audited_df["decision"] == "corrected"]
        rev_recovered = corrected_df["charge_amount"].sum() * 0.72
        
        total_audits = len(audited_df)
        labor_cost = total_audits * 5.00  # $5 labor overhead per review
        net_roi = rev_recovered - labor_cost
        roi_percentage = (net_roi / labor_cost * 100) if labor_cost > 0 else 0
        
        col_roi_1, col_roi_2, col_roi_3 = st.columns(3)
        col_roi_1.metric("Audited Claims Volume", f"{total_audits} Claims")
        col_roi_2.metric("Auditor Prevented Leakage (Recovered)", f"${rev_recovered:,.2f}")
        col_roi_3.metric("Net Auditor Return on Investment (ROI)", f"{roi_percentage:.1f}% ROI")
        
        st.markdown("---")
        
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
                color_discrete_sequence=["#10b981"],
                template="plotly_dark"
            )
            fig_dur.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
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
            
    render_inference(
        "Auditor Productivity & Workload Metrics",
        "Human auditors provide crucial verification of complex claims. This page tracks review speed (mean duration) "
        "and correction frequency. High correction rates imply that the AI is struggle-prone in specific code families, "
        "while wide differences in review times among auditors suggest training opportunities or unequal file difficulty."
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
        
    render_inference(
        "A/B Cohort Statistical Interpretations",
        "A/B testing evaluates if changing from Model v1.8 (Control) to Model v2.1 (Treatment) creates a statistically "
        "meaningful benefit. The p-values determine if the difference in denial rates and automation rates is due to random "
        "chance or model performance. A p-value below 0.05 is statistically significant, confirming that the new model version "
        "provides real, measurable improvement in the billing pipeline."
    )

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
        * **Days in Accounts Receivable (AR Days)**: Average number of days it takes for a clinic to receive full payment from insurance underwriters after patient visits occur.
        """
    )
