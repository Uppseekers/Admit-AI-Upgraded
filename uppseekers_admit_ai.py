import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. GLOBAL REGIONAL WEIGHTING MATRIX (Normalized to 100)
# ─────────────────────────────────────────────
# Order: [Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10]
# Q5 (Research) and Q7 (Internships) are the primary movers
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
        .stButton>button { width: 100%; border-radius: 10px; background-color: #004aad; color: white; font-weight: bold; height: 3em; }
        .score-box { background-color: #f0f2f6; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #004aad; margin-bottom: 15px; }
        .m-title { font-size: 1.1em; font-weight: bold; color: #004aad; }
        .m-val { font-size: 2em; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

def calculate_regional_score(responses, country_key):
    weights = REGIONAL_WEIGHTS.get(country_key, [0.1]*10)
    total = 0
    for i, (_, _, raw_val, _) in enumerate(responses):
        # Normalize: (Raw score * Weight) / Max Possible contribution
        # Max score for Q1 is 40, others are 7.5 to 11.2
        total += (raw_val * weights[i] * 10)
    return min(100, total / 4.2) # Scaling factor to normalize to 100 scale

# ─────────────────────────────────────────────
# 3. APP FLOW
# ─────────────────────────────────────────────
apply_styles()

if 'page' not in st.session_state: st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI: Global Assessment")
    with st.container():
        name = st.text_input("Student Name")
        course = st.selectbox("Select Major", ["CS/AI", "Data Science and Statistics", "Business and Administration", "Finance and Economics"])
        selected_regions = st.multiselect("Select Target Regions", list(REGIONAL_WEIGHTS.keys()))
        
        if st.button("Start Global Analysis"):
            if name and selected_regions:
                st.session_state.update({"name": name, "course": course, "regions": selected_regions, "page": 'assessment'})
                st.rerun()

elif st.session_state.page == 'assessment':
    col_q, col_meter = st.columns([0.6, 0.4])
    
    # Mapping to correct sheet
    q_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats.", "Business and Administration": "set_business", "Finance and Economics": "set_finance&eco."}
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])

    with col_q:
        st.header(f"Profile: {st.session_state.course}")
        current_responses = []
        for idx, row in q_df.iterrows():
            st.write(f"**Q{idx+1}. {row['question_text']}**")
            opts = ["None"]
            v_map = {"None": 0}
            for c in 'ABCDE':
                if pd.notna(row.get(f'option_{c}')):
                    label = f"{c}) {str(row[f'option_{c}']).strip()}"
                    opts.append(label); v_map[label] = row[f'score_{c}']
            sel = st.selectbox("Current Status", opts, key=f"q{idx}")
            current_responses.append((row['question_text'], sel, v_map[sel], row['question_id']))
            st.divider()

    with col_meter:
        st.header("🌍 Real-Time Regional Readiness")
        st.caption("Each region weights your profile differently based on local admission DNA.")
        
        
        
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
            b_map = {"CS/AI": "benchmarking_cs", "Data Science and Statistics": "benchmarking_ds", "Business and Administration": "benchmarking_business", "Finance and Economics": "benchmarking_finance&economic"}
            bench_raw = pd.read_excel("Benchmarking_USA (3) (2).xlsx", sheet_name=b_map[st.session_state.course])
            st.session_state.update({"current_responses": current_responses, "bench_raw": bench_raw, "page": 'tuner'})
            st.rerun()

elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Tuner: Current vs. Planned Impact")
    col_t, col_stats = st.columns([0.5, 0.5])
    
    q_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats.", "Business and Administration": "set_business", "Finance and Economics": "set_finance&eco."}
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])

    with col_t:
        st.subheader("🛠️ Strategic Tuning")
        tuned_responses = []
        for i, (q_text, orig_sel, orig_val, q_id) in enumerate(st.session_state.current_responses):
            row = q_df.iloc[i]
            opts = ["None"]; v_map = {"None": 0}
            for c in 'ABCDE':
                if pd.notna(row.get(f'option_{c}')):
                    label = f"{c}) {str(row[f'option_{c}']).strip()}"
                    opts.append(label); v_map[label] = row[f'score_{c}']
            st.markdown(f"**{q_text}**")
            t_sel = st.selectbox("Strategic Improvement", opts, index=opts.index(orig_sel), key=f"t{i}")
            tuned_responses.append((q_text, t_sel, v_map[t_sel], q_id))

    with col_stats:
        st.subheader("📈 Global Numerical Comparison")
        for region in st.session_state.regions:
            c_score = calculate_regional_score(st.session_state.current_responses, region)
            p_score = calculate_regional_score(tuned_responses, region)
            
            st.markdown(f"#### 📍 {region}")
            m1, m2 = st.columns(2)
            m1.metric("Current", f"{round(c_score,1)}%")
            m2.metric("Planned", f"{round(p_score,1)}%", delta=f"{round(p_score-c_score,1)}%")
            
            # Regional Sorting & Counting
            bench = st.session_state.bench_raw[st.session_state.bench_raw["Country"] == region] if "Country" in st.session_state.bench_raw.columns else st.session_state.bench_raw
            
            # Dynamic Sorting logic: Safe-Target (High to Low) | Needs-Gap (Low to High)
            def get_cat_counts(score):
                if bench.empty: return 0, 0, 0
                gaps = ((score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
                safe = len(gaps[gaps >= -3])
                needs = len(gaps[(gaps < -3) & (gaps >= -15)])
                gaps_count = len(gaps[gaps < -15])
                return safe, needs, gaps_count

            cs, cn, cg = get_cat_counts(c_score)
            ps, pn, pg = get_cat_counts(p_score)
            
            st.write(f"**Safe to Target:** {cs} → {ps} | **Needs Strengthening:** {cn} → {pn}")
            st.divider()

    c_code = st.text_input("Consultant Security Code", type="password")
    if st.button("Generate Report") and c_code == "304":
        st.success("Analysis Authorized.")
