import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. GLOBAL REGIONAL WEIGHTING MATRIX (DNA)
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

CATEGORIES = ["Academics", "Rigor", "Testing", "Merit", "Research", "Engagement", "Experience", "Impact", "Public Voice", "Recognition"]

# ─────────────────────────────────────────────
# 2. CORE UTILITY FUNCTIONS
# ─────────────────────────────────────────────
def calculate_regional_score(responses, country_key, max_scores):
    weights = REGIONAL_WEIGHTS.get(country_key, [0.1]*10)
    # Earned = Σ (Score_i * Weight_i) / Σ (Max_i * Weight_i)
    earned_weighted_sum = sum(responses[i][2] * weights[i] for i in range(len(responses)))
    max_weighted_sum = sum(max_scores[i] * weights[i] for i in range(len(max_scores)))
    return (earned_weighted_sum / max_weighted_sum) * 100 if max_weighted_sum > 0 else 0

def generate_pdf(state, tuned_scores, counsellor_name, all_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph(f"Strategic Roadmap: {state['name']}", styles['Title']))
    elements.append(Paragraph(f"Major: {state['course']} | Counsellor: {counsellor_name}", styles['Normal']))
    elements.append(Spacer(1, 20))

    for region in state['regions']:
        elements.append(Paragraph(f"Region: {region} (Target Readiness: {round(tuned_scores[region], 1)}%)", styles['Heading2']))
        bench = all_bench.get(region, pd.DataFrame())
        if not bench.empty:
            data = [["University", "Bench Score", "Gap %"]]
            for _, r in bench.head(10).iterrows():
                data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Gap %'], 1)}%"])
            t = Table(data, colWidths=[280, 80, 70])
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.dodgerblue), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
            elements.append(t)
        elements.append(PageBreak())
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 3. STREAMLIT APP INITIALIZATION
# ─────────────────────────────────────────────
st.set_page_config(page_title="Admit AI: Global Strategy", layout="wide")

# CRITICAL: Initialize session state variables to prevent AttributeErrors
if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'max_scores' not in st.session_state: st.session_state.max_scores = []
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None
if 'report_ready' not in st.session_state: st.session_state.report_ready = False

st.markdown("""<style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #004aad; color: white; font-weight: bold; }
    .score-box { background-color: #f8f9fa; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #004aad; margin-bottom: 10px; }
    .m-title { font-weight: bold; color: #004aad; }
</style>""", unsafe_allow_html=True)

# --- PAGE 1: INTRO ---
if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    name = st.text_input("Student Name")
    course = st.selectbox("Select Major", ["CS/AI", "Data Science and Statistics", "Business and Administration", "Finance and Economics"])
    regions = st.multiselect("Select Regions", list(REGIONAL_WEIGHTS.keys()))
    if st.button("Proceed to Assessment"):
        if name and regions:
            st.session_state.update({"name": name, "course": course, "regions": regions, "page": 'assessment'})
            st.rerun()

# --- PAGE 2: ASSESSMENT ---
elif st.session_state.page == 'assessment':
    q_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats.", "Business and Administration": "set_business", "Finance and Economics": "set_finance&eco."}
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])
    q_df.columns = [c.strip() for c in q_df.columns]
    
    col_q, col_meter = st.columns([0.6, 0.4])
    with col_q:
        st.header(f"Assessment: {st.session_state.name}")
        temp_responses = []
        temp_max_scores = []
        for idx, row in q_df.iterrows():
            q_text = row.get('Specific Question', f"Category: {row.get('Category')}")
            st.write(f"**{idx+1}. {q_text}**")
            opts = ["None"]; v_map = {"None": 0}
            for c in ['A', 'B', 'C', 'D']:
                opt_col = next((col for col in q_df.columns if f"Option {c}" in col), None)
                if opt_col and pd.notna(row[opt_col]):
                    label = f"{c}) {row[opt_col]}"; opts.append(label); v_map[label] = row[f'Score {c}']
            sel = st.selectbox("Level", opts, key=f"q_{idx}")
            temp_responses.append((q_text, sel, v_map[sel], idx))
            temp_max_scores.append(row['Score A'])
            st.divider()

    with col_meter:
        st.header("Readiness Meters")
        for region in st.session_state.regions:
            score = calculate_regional_score(temp_responses, region, temp_max_scores)
            st.markdown(f'<div class="score-box"><div class="m-title">{region}</div><div style="font-size: 2em; font-weight: bold;">{round(score, 1)}%</div></div>', unsafe_allow_html=True)
            st.progress(score/100)
        
        if st.button("Go to Strategic Tuner"):
            # SAVE TO STATE BEFORE SWITCHING
            b_map = {"CS/AI": "benchmarking_cs", "Data Science and Statistics": "benchmarking_ds", "Business and Administration": "benchmarking_business", "Finance and Economics": "benchmarking_finance&economic"}
            bench_raw = pd.read_excel("Benchmarking_USA (3) (2).xlsx", sheet_name=b_map[st.session_state.course])
            st.session_state.responses = temp_responses
            st.session_state.max_scores = temp_max_scores
            st.session_state.bench_raw = bench_raw
            st.session_state.page = 'tuner'
            st.rerun()

# --- PAGE 3: STRATEGIC TUNER ---
elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Tuner")
    
    col_t, col_stats = st.columns([0.5, 0.5])
    with col_t:
        st.subheader("Simulate Improvements")
        tuned_responses = []
        # Accessing session_state.responses safely because it was initialized
        for i, (q_text, orig_sel, orig_val, q_id) in enumerate(st.session_state.responses):
            # We rebuild the option list to allow the student to select higher options
            # Since the logic depends on the original Excel structure, we re-load it briefly
            q_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats.", "Business and Administration": "set_business", "Finance and Economics": "set_finance&eco."}
            q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])
            row = q_df.iloc[i]
            
            opts = ["None"]; v_map = {"None": 0}
            for c in ['A', 'B', 'C', 'D']:
                opt_col = next((col for col in q_df.columns if f"Option {c}" in col), None)
                if opt_col and pd.notna(row[opt_col]):
                    label = f"{c}) {row[opt_col]}"; opts.append(label); v_map[label] = row[f'Score {c}']
            
            st.write(f"**{CATEGORIES[i]}**")
            t_sel = st.selectbox("Plan Goal", opts, index=opts.index(orig_sel), key=f"tune_{i}")
            tuned_responses.append((q_text, t_sel, v_map[t_sel], q_id))

    with col_stats:
        st.subheader("Regional Impact")
        tuned_scores = {}
        all_tuned_bench = {}
        for region in st.session_state.regions:
            c_score = calculate_regional_score(st.session_state.responses, region, st.session_state.max_scores)
            p_score = calculate_regional_score(tuned_responses, region, st.session_state.max_scores)
            tuned_scores[region] = p_score
            
            st.markdown(f"**📍 {region}**")
            m1, m2 = st.columns(2)
            m1.metric("Current", f"{round(c_score,1)}%")
            m2.metric("Target", f"{round(p_score,1)}%", delta=f"{round(p_score-c_score,1)}%")
            
            bench = st.session_state.bench_raw.copy()
            bench["Gap %"] = ((p_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
            all_tuned_bench[region] = bench.sort_values("Gap %", ascending=False)
            st.divider()

    c_name = st.text_input("Counsellor Name")
    if st.button("Generate Roadmap") and st.text_input("PIN", type="password") == "304":
        st.session_state.pdf_data = generate_pdf(st.session_state, tuned_scores, c_name, all_tuned_bench)
        st.session_state.report_ready = True
        st.success("Roadmap Generated!")

    if st.session_state.report_ready:
        st.download_button("📥 Download PDF", data=st.session_state.pdf_data, file_name=f"{st.session_state.name}_Roadmap.pdf")
