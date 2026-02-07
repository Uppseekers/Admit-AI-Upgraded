import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
    max_weighted_sum = sum(max_scores[i] * weights[i] for i in range(len(max_scores)))
    return (earned_weighted_sum / max_weighted_sum) * 100 if max_weighted_sum > 0 else 0

# ─────────────────────────────────────────────
# 3. PDF REPORT GENERATOR
# ─────────────────────────────────────────────
def generate_strategic_pdf(state, tuned_regional_scores, counsellor_name, all_tuned_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Uppseekers Admit AI Strategic Roadmap: {state['name']}", styles['Title']))
    elements.append(Paragraph(f"<b>Planned Major:</b> {state['course']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Counsellor:</b> {counsellor_name}", styles['Normal']))
    elements.append(Spacer(1, 20))

    for region in state['regions']:
        score = tuned_regional_scores[region]
        elements.append(Paragraph(f"Target Region: {region} (Projected Readiness: {round(score, 1)}%)", styles['Heading2']))
        
        bench = all_tuned_bench.get(region, pd.DataFrame())
        if not bench.empty:
            # Sort Benchmarks strategically
            safe = bench[bench["Gap %"] >= -3].sort_values("Total Benchmark Score", ascending=False).head(5)
            elements.append(Paragraph("Recommended Safe/Target Institutions:", styles['Heading3']))
            if not safe.empty:
                data = [["University", "Bench Score", "Gap %"]] + [[r["University"], round(r["Total Benchmark Score"], 1), f"{round(r['Gap %'], 1)}%"] for _, r in safe.iterrows()]
                t = Table(data, colWidths=[300, 80, 70])
                t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.dodgerblue), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
                elements.append(t)
        elements.append(PageBreak())

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. STREAMLIT UI & LOGIC
# ─────────────────────────────────────────────
st.set_page_config(page_title="Admit AI: Global Strategy", layout="wide")

# Persistent State Management
if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'report_ready' not in st.session_state: st.session_state.report_ready = False

st.markdown("""<style>
    .stButton>button { width: 100%; border-radius: 10px; background-color: #004aad; color: white; font-weight: bold; height: 3em; }
    .score-box { background-color: #f8f9fa; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #004aad; margin-bottom: 15px; }
    .m-title { font-size: 1.1em; font-weight: bold; color: #004aad; }
    .m-val { font-size: 2.2em; font-weight: bold; color: #333; }
</style>""", unsafe_allow_html=True)

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

# --- PAGE 2: ASSESSMENT ---
elif st.session_state.page == 'assessment':
    col_q, col_meter = st.columns([0.6, 0.4])
    q_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats.", "Business and Administration": "set_business", "Finance and Economics": "set_finance&eco."}
    
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])
    q_df.columns = [c.strip() for c in q_df.columns]

    with col_q:
        st.header(f"Profile Audit: {st.session_state.course}")
        current_responses = []
        max_scores_list = []
        for idx, row in q_df.iterrows():
            q_display = row.get('Specific Question', f"Category: {row.get('Category', 'N/A')}")
            st.write(f"**Q{idx+1}. {q_display}**")
            opts = ["None"]; v_map = {"None": 0}
            for c in ['A', 'B', 'C', 'D']:
                opt_col = next((col for col in q_df.columns if f"Option {c}" in col), None)
                if opt_col and pd.notna(row[opt_col]):
                    label = f"{c}) {str(row[opt_col]).strip()}"; opts.append(label); v_map[label] = row[f'Score {c}']
            sel = st.selectbox("Select Status", opts, key=f"q{idx}")
            current_responses.append((q_display, sel, v_map[sel], idx))
            max_scores_list.append(row['Score A'])
            st.divider()

    with col_meter:
        st.header("🌍 Regional Strategy Dashboard")
        for region in st.session_state.regions:
            r_score = calculate_regional_score(current_responses, region, max_scores_list)
            st.markdown(f'<div class="score-box"><div class="m-title">{region} Readiness</div><div class="m-val">{round(r_score, 1)}%</div></div>', unsafe_allow_html=True)
            st.progress(r_score / 100)

        if st.button("Finalize & Compare Strategic Path"):
            b_map = {"CS/AI": "benchmarking_cs", "Data Science and Statistics": "benchmarking_ds", "Business and Administration": "benchmarking_business", "Finance and Economics": "benchmarking_finance&economic"}
            bench_raw = pd.read_excel("Benchmarking_USA (3) (2).xlsx", sheet_name=b_map[st.session_state.course])
            st.session_state.update({"current_responses": current_responses, "max_scores": max_scores_list, "bench_raw": bench_raw, "page": 'tuner'})
            st.rerun()

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
                if opt_col and pd.notna(row[opt_col]):
                    label = f"{c}) {str(row[opt_col]).strip()}"; opts.append(label); v_map[label] = row[f'Score {c}']
            t_sel = st.selectbox(f"Improvement: {CATEGORIES[i]}", opts, index=opts.index(orig_sel), key=f"t{i}")
            tuned_responses.append((q_text, t_sel, v_map[t_sel], q_id))

    with col_stats:
        st.subheader("📈 Global Numerical Impact")
        all_tuned_bench = {}
        tuned_regional_scores = {}
        for region in st.session_state.regions:
            c_score = calculate_regional_score(st.session_state.current_responses, region, st.session_state.max_scores)
            p_score = calculate_regional_score(tuned_responses, region, st.session_state.max_scores)
            tuned_regional_scores[region] = p_score
            st.markdown(f"#### 📍 {region}")
            m1, m2 = st.columns(2)
            m1.metric("Current", f"{round(c_score,1)}%"); m2.metric("Strategic", f"{round(p_score,1)}%", delta=f"{round(p_score-c_score,1)}%")
            
            bench = st.session_state.bench_raw.copy()
            bench["Gap %"] = ((p_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
            all_tuned_bench[region] = bench
            st.divider()

    c_name = st.text_input("Counsellor Name")
    if st.button("Generate Strategic Report") and st.text_input("PIN", type="password") == "304":
        pdf_data = generate_strategic_pdf(st.session_state, tuned_regional_scores, c_name, all_tuned_bench)
        st.session_state.pdf_buffer = pdf_data
        st.session_state.report_ready = True

    if st.session_state.report_ready:
        st.download_button("📥 Download Final PDF Roadmap", data=st.session_state.pdf_buffer, file_name=f"{st.session_state.name}_Roadmap.pdf", mime="application/pdf")
