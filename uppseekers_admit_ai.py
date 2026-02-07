import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. GLOBAL REGIONAL WEIGHTING MATRIX
# ─────────────────────────────────────────────
# Each list represents the weight of Q1 through Q10 for that region.
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

# ─────────────────────────────────────────────
# 2. APP UI & STYLING
# ─────────────────────────────────────────────
st.set_page_config(page_title="Admit AI: Global Strategy", layout="wide")

def apply_styles():
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 10px; background-color: #004aad; color: white; font-weight: bold; height: 3.2em; border: none; }
        .score-box { background-color: #f0f2f6; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #004aad; margin-bottom: 15px; }
        .m-title { font-size: 1em; font-weight: bold; color: #004aad; margin-bottom: 5px; }
        .m-val { font-size: 2.2em; font-weight: bold; color: #333; }
        .comparison-label { font-size: 0.9em; font-weight: bold; color: #555; }
        .comparison-val { font-size: 1.3em; font-weight: bold; color: #004aad; }
        </style>
    """, unsafe_allow_html=True)

def calculate_regional_score(responses, country_key):
    weights = REGIONAL_WEIGHTS.get(country_key, [0.1]*10)
    total = 0
    # Normalize score based on a 100-point scale
    for i, (_, _, raw_val, _) in enumerate(responses):
        # We multiply raw_val by weights[i] and a factor of 10 to reach the 100 range
        total += (raw_val * weights[i] * 10)
    return min(100, total / 4.2) # Normalizing constant

# ─────────────────────────────────────────────
# 3. APP FLOW
# ─────────────────────────────────────────────
apply_styles()

if 'page' not in st.session_state: st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI: Global Edition")
    with st.container():
        name = st.text_input("Student Name")
        course = st.selectbox("Select Major", ["CS/AI", "Data Science and Statistics", "Business and Administration", "Finance and Economics"])
        selected_regions = st.multiselect("Select Target Regions (Up to 10)", list(REGIONAL_WEIGHTS.keys()))
        
        if st.button("Start Global Analysis"):
            if name and selected_regions:
                st.session_state.update({"name": name, "course": course, "regions": selected_regions, "page": 'assessment'})
                st.rerun()
            else:
                st.warning("Please provide a name and select at least one region.")

elif st.session_state.page == 'assessment':
    col_q, col_meter = st.columns([0.6, 0.4])
    
    q_map = {
        "CS/AI": "set_cs-ai", 
        "Data Science and Statistics": "set_ds-stats.", 
        "Business and Administration": "set_business", 
        "Finance and Economics": "set_finance&eco."
    }
    
    # Load questions and normalize columns
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])
    q_df.columns = [c.strip().lower() for c in q_df.columns]
    q_text_col = 'question_text' if 'question_text' in q_df.columns else q_df.columns[1]

    with col_q:
        st.header(f"Profile Assessment: {st.session_state.course}")
        current_responses = []
        for idx, row in q_df.iterrows():
            st.write(f"**Q{idx+1}. {row[q_text_col]}**")
            opts = ["None"]
            v_map = {"None": 0}
            for c in 'ABCDE':
                col_name = f'option_{c.lower()}' if f'option_{c.lower()}' in q_df.columns else f'option_{c}'
                score_name = f'score_{c.lower()}' if f'score_{c.lower()}' in q_df.columns else f'score_{c}'
                
                if col_name in q_df.columns and pd.notna(row[col_name]):
                    label = f"{c}) {str(row[col_name]).strip()}"
                    opts.append(label); v_map[label] = row[score_name]
            
            sel = st.selectbox("Select Status", opts, key=f"q{idx}")
            current_responses.append((row[q_text_col], sel, v_map[sel], idx))
            st.divider()

    with col_meter:
        st.header("🌍 Live Regional Readiness")
        st.caption("Each region weights your profile based on its unique admissions DNA.")
        
        
        
        for region in st.session_state.regions:
            r_score = calculate_regional_score(current_responses, region)
            st.markdown(f"""
            <div class="score-box">
                <div class="m-title">{region} Readiness Score</div>
                <div class="m-val">{round(r_score, 1)}%</div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(r_score / 100)

        if st.button("Proceed to Strategic Tuner"):
            # Load benchmarking (v3-2)
            b_map = {
                "CS/AI": "benchmarking_cs", 
                "Data Science and Statistics": "benchmarking_ds", 
                "Business and Administration": "benchmarking_business", 
                "Finance and Economics": "benchmarking_finance&economic"
            }
            bench_raw = pd.read_excel("Benchmarking_USA (3) (2).xlsx", sheet_name=b_map[st.session_state.course])
            st.session_state.update({"current_responses": current_responses, "bench_raw": bench_raw, "page": 'tuner'})
            st.rerun()

elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Tuner: Impact Comparison")
    col_t, col_stats = st.columns([0.5, 0.5])
    
    q_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats.", "Business and Administration": "set_business", "Finance and Economics": "set_finance&eco."}
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])
    q_df.columns = [c.strip().lower() for c in q_df.columns]

    with col_t:
        st.subheader("🛠️ Counsellor Strategic Plan")
        tuned_responses = []
        for i, (q_text, orig_sel, orig_val, q_id) in enumerate(st.session_state.current_responses):
            row = q_df.iloc[i]
            opts = ["None"]; v_map = {"None": 0}
            for c in 'ABCDE':
                col_name = f'option_{c.lower()}' if f'option_{c.lower()}' in q_df.columns else f'option_{c}'
                score_name = f'score_{c.lower()}' if f'score_{c.lower()}' in q_df.columns else f'score_{c}'
                if col_name in q_df.columns and pd.notna(row[col_name]):
                    label = f"{c}) {str(row[col_name]).strip()}"
                    opts.append(label); v_map[label] = row[score_name]
            
            st.markdown(f"**{row.get('question_text', q_text)}**")
            t_sel = st.selectbox("Strategic Improvement", opts, index=opts.index(orig_sel), key=f"t{i}")
            tuned_responses.append((q_text, t_sel, v_map[t_sel], q_id))

    with col_stats:
        st.subheader("📈 Cross-Regional Impact Analysis")
        for region in st.session_state.regions:
            c_score = calculate_regional_score(st.session_state.current_responses, region)
            p_score = calculate_regional_score(tuned_responses, region)
            
            st.markdown(f"#### 🚩 {region}")
            m1, m2 = st.columns(2)
            m1.metric("Current", f"{round(c_score,1)}%")
            m2.metric("Planned", f"{round(p_score,1)}%", delta=f"{round(p_score-c_score,1)}%")
            
            # University Counts Comparison
            bench = st.session_state.bench_raw[st.session_state.bench_raw["Country"].str.strip().str.lower() == region.strip().lower()] if "Country" in st.session_state.bench_raw.columns else st.session_state.bench_raw
            
            if not bench.empty:
                # Gap thresholds: Safe-Target (>= -3%), Needs (-3 to -15%), Gap (< -15%)
                c_gaps = ((c_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
                p_gaps = ((p_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
                
                c_s, p_s = len(c_gaps[c_gaps >= -3]), len(p_gaps[p_gaps >= -3])
                c_n, p_n = len(c_gaps[(c_gaps < -3) & (c_gaps >= -15)]), len(p_gaps[(p_gaps < -3) & (p_gaps >= -15)])
                
                c1, c2 = st.columns(2)
                with c1: st.markdown(f"<p class='comparison-label'>Safe to Target</p><p class='comparison-val'>{c_s} → {p_s}</p>", unsafe_allow_html=True)
                with c2: st.markdown(f"<p class='comparison-label'>Needs Strengthening</p><p class='comparison-val'>{c_n} → {p_n}</p>", unsafe_allow_html=True)
            st.divider()

    st.subheader("📥 Authorization")
    if st.text_input("Consultant Access PIN", type="password") == "304":
        st.success("Authorized.")
