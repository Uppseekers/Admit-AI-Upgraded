import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. GLOBAL REGIONAL WEIGHTING MATRIX (DNA)
# ─────────────────────────────────────────────
# This matrix defines the percentage impact of Q1 through Q10 for each region.
# Note high sensitivity on Q5 (Research) and Q7 (Internships).
REGIONAL_WEIGHTS = {
    "USA":               [0.20, 0.10, 0.05, 0.05, 0.15, 0.05, 0.20, 0.10, 0.05, 0.05],
    "UK":                [0.25, 0.10, 0.05, 0.05, 0.30, 0.02, 0.10, 0.03, 0.00, 0.10],
    "Germany":           [0.35, 0.10, 0.05, 0.05, 0.05, 0.00, 0.35, 0.00, 0.00, 0.05],
    "Singapore":         [0.30, 0.10, 0.10, 0.15, 0.10, 0.02, 0.15, 0.03, 0.00, 0.05],
    "Australia":         [0.30, 0.10, 0.10, 0.05, 0.10, 0.05, 0.20, 0.05, 0.00, 0.05],
    "Canada":            [0.25, 0.10, 0.05, 0.05, 0.15, 0.05, 0.20, 0.10, 0.00, 0.05],
    "Netherlands":       [0.35, 0.15, 0.05, 0.05, 0.10, 0.00, 0.25, 0.00, 0.00, 0.05],
    "European Countries":[0.30, 0.15, 0.05, 0.05, 0.10, 0.05, 0.20, 0.05, 0.00, 0.05],
    "Japan":             [0.40, 0.10, 0.10, 0.10, 0.10, 0.00, 0.10, 0.05, 0.00, 0.05],
    "Other Asian":       [0.40, 0.10, 0.15, 0.10, 0.05, 0.02, 0.10, 0.03, 0.00, 0.05]
}

CATEGORIES = [
    "Academics", "Rigor", "Testing", "Merit", "Research", 
    "Engagement", "Experience", "Impact", "Public Voice", "Recognition"
]

# ─────────────────────────────────────────────
# 2. CORE SCORING ENGINE (PROPORTIONAL LOGIC)
# ─────────────────────────────────────────────
def calculate_regional_score(responses, country_key, max_scores):
    """
    Calculates score based on True Weighted Average.
    Formula: Σ (Earned_i * Weight_i) / Σ (Max_i * Weight_i) * 100
    """
    weights = REGIONAL_WEIGHTS.get(country_key, [0.1]*10)
    earned_weighted_sum = 0
    max_weighted_sum = 0
    
    for i in range(len(responses)):
        earned_weighted_sum += (responses[i][2] * weights[i])
        max_weighted_sum += (max_scores[i] * weights[i])
        
    if max_weighted_sum == 0: return 0
    return (earned_weighted_sum / max_weighted_sum) * 100

# ─────────────────────────────────────────────
# 3. UI STYLING & APP FLOW
# ─────────────────────────────────────────────
st.set_page_config(page_title="Admit AI: Global Strategy", layout="wide")

def apply_styles():
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 10px; background-color: #004aad; color: white; font-weight: bold; }
        .score-box { background-color: #f8f9fa; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #004aad; margin-bottom: 15px; }
        .m-title { font-size: 1.1em; font-weight: bold; color: #004aad; }
        .m-val { font-size: 2.2em; font-weight: bold; color: #333; }
        .weight-tag { background-color: #e9ecef; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold; color: #495057; }
        </style>
    """, unsafe_allow_html=True)

apply_styles()

if 'page' not in st.session_state: st.session_state.page = 'intro'

# --- PAGE 1: SETUP ---
if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI: Global Assessment")
    name = st.text_input("Student Name")
    course = st.selectbox("Select Major", ["CS/AI", "Data Science and Statistics", "Business and Administration", "Finance and Economics"])
    selected_regions = st.multiselect("Select Target Regions", list(REGIONAL_WEIGHTS.keys()))
    
    if st.button("Start Strategic Analysis"):
        if name and selected_regions:
            st.session_state.update({"name": name, "course": course, "regions": selected_regions, "page": 'assessment'})
            st.rerun()
        else:
            st.warning("Please enter your name and select at least one region.")

# --- PAGE 2: ASSESSMENT ---
elif st.session_state.page == 'assessment':
    col_q, col_meter = st.columns([0.6, 0.4])
    
    q_map = {
        "CS/AI": "set_cs-ai", 
        "Data Science and Statistics": "set_ds-stats.", 
        "Business and Administration": "set_business", 
        "Finance and Economics": "set_finance&eco."
    }
    
    # Logic to load data and identify questions from Column C
    try:
        q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])
        q_df.columns = [c.strip() for c in q_df.columns]
    except:
        st.error("Data file not found. Please ensure 'University Readiness_new (3).xlsx' is available.")
        st.stop()

    with col_q:
        st.header(f"Profile Audit: {st.session_state.course}")
        current_responses = []
        max_scores_list = []
        
        for idx, row in q_df.iterrows():
            # Use Column C ("Specific Question") as requested
            q_display = row.get('Specific Question', f"Category: {row.get('Category', 'N/A')}")
            st.write(f"**Q{idx+1}. {q_display}**")
            
            opts = ["None"]
            v_map = {"None": 0}
            for c in ['A', 'B', 'C', 'D']:
                opt_col = next((col for col in q_df.columns if f"Option {c}" in col), None)
                score_col = f'Score {c}'
                if opt_col and pd.notna(row[opt_col]):
                    label = f"{c}) {str(row[opt_col]).strip()}"
                    opts.append(label)
                    v_map[label] = row[score_col]
            
            sel = st.selectbox("Select Current Status", opts, key=f"q{idx}")
            current_responses.append((q_display, sel, v_map[sel], idx))
            max_scores_list.append(row['Score A'])
            st.divider()

    with col_meter:
        st.header("🌍 Regional Strategy Dashboard")
        
        # Display weights for the primary selected region
        primary_region = st.session_state.regions[0]
        with st.expander(f"📊 Regional DNA: {primary_region} Priorities"):
            weights = REGIONAL_WEIGHTS[primary_region]
            w_data = pd.DataFrame({"Category": CATEGORIES, "Weight (%)": [f"{int(w*100)}%" for w in weights]})
            st.table(w_data)

        # Calculate and show score meters
        for region in st.session_state.regions:
            r_score = calculate_regional_score(current_responses, region, max_scores_list)
            st.markdown(f"""
            <div class="score-box">
                <div class="m-title">{region} Readiness Score</div>
                <div class="m-val">{round(r_score, 1)}%</div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(r_score / 100)
            
            # Tip logic based on "Number Movers"
            if current_responses[4][2] < max_scores_list[4]: # Research tip
                st.caption(f"💡 Research is a high-impact category for {region}. Upgrading this moves the meter by {int(REGIONAL_WEIGHTS[region][4]*100)}%.")
            st.write("")

        if st.button("Finalize & Compare Strategic Path"):
            b_map = {
                "CS/AI": "benchmarking_cs", "Data Science and Statistics": "benchmarking_ds", 
                "Business and Administration": "benchmarking_business", "Finance and Economics": "benchmarking_finance&economic"
            }
            try:
                bench_raw = pd.read_excel("Benchmarking_USA (3) (2).xlsx", sheet_name=b_map[st.session_state.course])
                st.session_state.update({
                    "current_responses": current_responses, 
                    "max_scores": max_scores_list, 
                    "bench_raw": bench_raw, 
                    "page": 'tuner'
                })
                st.rerun()
            except:
                st.error("Benchmarking sheet not found.")

# --- PAGE 3: STRATEGIC TUNER ---
elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Comparison Tuner")
    col_t, col_stats = st.columns([0.5, 0.5])
    
    q_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats.", "Business and Administration": "set_business", "Finance and Economics": "set_finance&eco."}
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])
    q_df.columns = [c.strip() for c in q_df.columns]

    with col_t:
        st.subheader("🛠️ Strategic Improvement Plan")
        tuned_responses = []
        for i, (q_text, orig_sel, orig_val, q_id) in enumerate(st.session_state.current_responses):
            row = q_df.iloc[i]
            opts = ["None"]; v_map = {"None": 0}
            for c in ['A', 'B', 'C', 'D']:
                opt_col = next((col for col in q_df.columns if f"Option {c}" in col), None)
                score_col = f'Score {c}'
                if opt_col and pd.notna(row[opt_col]):
                    label = f"{c}) {str(row[opt_col]).strip()}"
                    opts.append(label); v_map[label] = row[score_col]
            
            st.markdown(f"**{row.get('Specific Question', q_text)}**")
            t_sel = st.selectbox("Strategic Improvement", opts, index=opts.index(orig_sel), key=f"t{i}")
            tuned_responses.append((q_text, t_sel, v_map[t_sel], q_id))

    with col_stats:
        st.subheader("📈 Global Numerical Impact")
        for region in st.session_state.regions:
            c_score = calculate_regional_score(st.session_state.current_responses, region, st.session_state.max_scores)
            p_score = calculate_regional_score(tuned_responses, region, st.session_state.max_scores)
            
            st.markdown(f"#### 📍 {region}")
            m1, m2 = st.columns(2)
            m1.metric("Current Profile", f"{round(c_score,1)}%")
            m2.metric("Strategic Profile", f"{round(p_score,1)}%", delta=f"{round(p_score-c_score,1)}%")
            
            # Logic for university counts using regional benchmarking
            bench = st.session_state.bench_raw[st.session_state.bench_raw["Country"] == region] if "Country" in st.session_state.bench_raw.columns else st.session_state.bench_raw
            if not bench.empty:
                def get_cat_counts(s):
                    gaps = ((s - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
                    return len(gaps[gaps >= -3]), len(gaps[(gaps < -3) & (gaps >= -15)])
                
                cs, cn = get_cat_counts(c_score)
                ps, pn = get_cat_counts(p_score)
                st.write(f"**Safe to Target:** {cs} → {ps} | **Needs Strengthening:** {cn} → {pn}")
            st.divider()

    st.subheader("📥 Finalize Analysis")
    if st.text_input("Consultant Security Code", type="password") == "304":
        st.success("Analysis Authorized. You can now generate the final strategic report.")
