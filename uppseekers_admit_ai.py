import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. GLOBAL REGIONAL WEIGHTING MATRIX
# ─────────────────────────────────────────────
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
# 2. CORE SCORING ENGINE (PROPORTIONAL LOGIC)
# ─────────────────────────────────────────────
def calculate_regional_score(responses, country_key, max_scores):
    """
    Calculates score based on True Weighted Average.
    If only one question is answered, the score will be low.
    """
    weights = REGIONAL_WEIGHTS.get(country_key, [0.1]*10)
    earned_points = 0
    total_possible_weight_points = 0
    
    for i in range(len(responses)):
        # raw_val is the score of the selected option
        # max_scores[i] is the Score A for that question
        earned_points += (responses[i][2] * weights[i])
        total_possible_weight_points += (max_scores[i] * weights[i])
        
    if total_possible_weight_points == 0: return 0
    return (earned_points / total_possible_weight_points) * 100

# ─────────────────────────────────────────────
# 3. UI & APP FLOW
# ─────────────────────────────────────────────
st.set_page_config(page_title="Admit AI: Global Strategy", layout="wide")

def apply_styles():
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 10px; background-color: #004aad; color: white; font-weight: bold; }
        .score-box { background-color: #f0f2f6; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #004aad; margin-bottom: 15px; }
        .m-val { font-size: 2.2em; font-weight: bold; color: #333; }
        </style>
    """, unsafe_allow_html=True)

apply_styles()

if 'page' not in st.session_state: st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI: Global Assessment")
    name = st.text_input("Student Name")
    course = st.selectbox("Select Major", ["CS/AI", "Data Science and Statistics", "Business and Administration", "Finance and Economics"])
    selected_regions = st.multiselect("Select Target Regions", list(REGIONAL_WEIGHTS.keys()))
    if st.button("Start Analysis"):
        if name and selected_regions:
            st.session_state.update({"name": name, "course": course, "regions": selected_regions, "page": 'assessment'})
            st.rerun()

elif st.session_state.page == 'assessment':
    col_q, col_meter = st.columns([0.6, 0.4])
    
    # File mapping
    q_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats.", "Business and Administration": "set_business", "Finance and Economics": "set_finance&eco."}
    
    # Logic to load Column C as Question
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])
    q_df.columns = [c.strip() for c in q_df.columns]

    with col_q:
        st.header(f"Profile: {st.session_state.course}")
        current_responses = []
        max_scores_list = []
        
        for idx, row in q_df.iterrows():
            # Use Column C ("Specific Question")
            q_display = row.get('Specific Question', f"Question {idx+1}")
            st.write(f"**{q_display}**")
            
            opts = ["None"]; v_map = {"None": 0}
            for c in ['A', 'B', 'C', 'D']:
                opt_col = next((col for col in q_df.columns if f"Option {c}" in col), None)
                score_col = f'Score {c}'
                if opt_col and pd.notna(row[opt_col]):
                    label = f"{c}) {str(row[opt_col]).strip()}"
                    opts.append(label); v_map[label] = row[score_col]
            
            sel = st.selectbox("Select Status", opts, key=f"q{idx}")
            current_responses.append((q_display, sel, v_map[sel], idx))
            max_scores_list.append(row['Score A'])
            st.divider()

    with col_meter:
        st.header("🌍 Regional Readiness")
        
        for region in st.session_state.regions:
            r_score = calculate_regional_score(current_responses, region, max_scores_list)
            st.markdown(f"""<div class="score-box"><div class="m-title">{region}</div><div class="m-val">{round(r_score, 1)}%</div></div>""", unsafe_allow_html=True)
            st.progress(r_score / 100)

        if st.button("Proceed to Strategic Tuner"):
            b_map = {"CS/AI": "benchmarking_cs", "Data Science and Statistics": "benchmarking_ds", "Business and Administration": "benchmarking_business", "Finance and Economics": "benchmarking_finance&economic"}
            bench_raw = pd.read_excel("Benchmarking_USA (3) (2).xlsx", sheet_name=b_map[st.session_state.course])
            st.session_state.update({"current_responses": current_responses, "max_scores": max_scores_list, "bench_raw": bench_raw, "page": 'tuner'})
            st.rerun()

elif st.session_state.page == 'tuner':
    # Strategic Tuner Logic (includes PDF generation with the Big-to-Small and Small-to-Big sorting logic)
    st.title("⚖️ Strategic Comparison Tuner")
    # ... [Rest of Tuner and sorting logic as previously discussed]
