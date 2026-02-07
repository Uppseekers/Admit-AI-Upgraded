import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. GLOBAL REGIONAL WEIGHTING MATRIX (DNA)
# ─────────────────────────────────────────────
# Defines the percentage impact of Q1 through Q10 for each region.
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
# 2. CORE SCORING ENGINE
# ─────────────────────────────────────────────
def calculate_regional_score(responses, country_key, max_scores):
    weights = REGIONAL_WEIGHTS.get(country_key, [0.1]*10)
    earned_weighted_sum = sum(responses[i][2] * weights[i] for i in range(len(responses)))
    max_weighted_sum = sum(max_scores[i] * weights[i] for i in range(len(responses)))
    return (earned_weighted_sum / max_weighted_sum) * 100 if max_weighted_sum > 0 else 0

# ─────────────────────────────────────────────
# 3. UI SETUP & SESSION STATE
# ─────────────────────────────────────────────
st.set_page_config(page_title="Admit AI: Global Strategy", layout="wide")

if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'report_ready' not in st.session_state: st.session_state.report_ready = False

st.markdown("""
    <style>
    .score-box { background-color: #f8f9fa; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #004aad; margin-bottom: 15px; }
    .m-title { font-size: 1.1em; font-weight: bold; color: #004aad; }
    .m-val { font-size: 2.2em; font-weight: bold; color: #333; }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 4. PAGE 1: SETUP
# ─────────────────────────────────────────────
if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI: Global Assessment")
    name = st.text_input("Student Name")
    course = st.selectbox("Select Major", ["CS/AI", "Data Science and Statistics", "Business and Administration", "Finance and Economics"])
    selected_regions = st.multiselect("Select Target Regions", list(REGIONAL_WEIGHTS.keys()))
    
    if st.button("Start Strategic Analysis"):
        if name and selected_regions:
            st.session_state.update({"name": name, "course": course, "regions": selected_regions, "page": 'assessment'})
            st.rerun()

# ─────────────────────────────────────────────
# 5. PAGE 2: ASSESSMENT
# ─────────────────────────────────────────────
elif st.session_state.page == 'assessment':
    col_q, col_meter = st.columns([0.6, 0.4])
    q_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats.", "Business and Administration": "set_business", "Finance and Economics": "set_finance&eco."}
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])

    with col_q:
        st.header(f"Profile Audit: {st.session_state.course}")
        current_responses = []
        max_scores_list = []
        for idx, row in q_df.iterrows():
            q_display = row.get('Specific Question', f"Q{idx+1}")
            st.write(f"**{q_display}**")
            opts = ["None"]; v_map = {"None": 0}
            for c in ['A', 'B', 'C', 'D']:
                if pd.notna(row[f'Option {c}']):
                    label = f"{c}) {str(row[f'Option {c}'])}"
                    opts.append(label); v_map[label] = row[f'Score {c}']
            sel = st.selectbox("Current Status", opts, key=f"q{idx}")
            current_responses.append((q_display, sel, v_map[sel], idx))
            max_scores_list.append(row['Score A'])
            st.divider()

    with col_meter:
        st.header("🌍 Regional Strategy Dashboard")
        # Display weightage for the first selected region
        with st.expander(f"📊 {st.session_state.regions[0]} Category Weightage"):
            weights = REGIONAL_WEIGHTS[st.session_state.regions[0]]
            st.table(pd.DataFrame({"Category": CATEGORIES, "Weight": [f"{int(w*100)}%" for w in weights]}))
        
        for region in st.session_state.regions:
            r_score = calculate_regional_score(current_responses, region, max_scores_list)
            st.markdown(f'<div class="score-box"><div class="m-title">{region}</div><div class="m-val">{round(r_score, 1)}%</div></div>', unsafe_allow_html=True)
            st.progress(r_score / 100)

        if st.button("Proceed to Strategic Tuner"):
            st.session_state.update({"current_responses": current_responses, "max_scores": max_scores_list, "page": 'tuner'})
            st.rerun()

# ─────────────────────────────────────────────
# 6. PAGE 3: STRATEGIC TUNER & PERSISTENT DOWNLOAD
# ─────────────────────────────────────────────
elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Comparison Tuner")
    col_t, col_stats = st.columns([0.5, 0.5])
    
    with col_t:
        st.subheader("🛠️ Strategic Improvement Plan")
        tuned_responses = []
        for i, (q_text, orig_sel, orig_val, q_id) in enumerate(st.session_state.current_responses):
            st.markdown(f"**{q_text}**")
            # Logic to rebuild options for tuning...
            tuned_responses.append((q_text, orig_sel, orig_val, q_id)) # Simplified for brevity

    with col_stats:
        st.subheader("📈 Global Impact")
        for region in st.session_state.regions:
            c_score = calculate_regional_score(st.session_state.current_responses, region, st.session_state.max_scores)
            # In real use, p_score would use tuned_responses
            st.metric(f"{region} Current Profile", f"{round(c_score,1)}%")

    # --- Persisent Download Logic ---
    st.divider()
    if not st.session_state.report_ready:
        if st.button("Authorize & Generate Final Report"):
            # Dummy PDF generation logic
            st.session_state.pdf_data = b"PDF Content" 
            st.session_state.report_ready = True
            st.rerun()
    else:
        st.success("Report Generated Successfully!")
        st.download_button(
            label="⬇️ Download Strategic Report",
            data=st.session_state.pdf_data,
            file_name=f"{st.session_state.name}_Roadmap.pdf",
            mime="application/pdf"
        )
