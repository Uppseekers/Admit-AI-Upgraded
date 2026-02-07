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

CATEGORIES = ["Academics", "Rigor", "Testing", "Merit", "Research", "Engagement", "Experience", "Impact", "Public Voice", "Recognition"]

# ─────────────────────────────────────────────
# 2. CORE LOGIC FUNCTIONS
# ─────────────────────────────────────────────
def calculate_regional_score(responses, country_key, max_scores):
    weights = REGIONAL_WEIGHTS.get(country_key, [0.1]*10)
    earned_sum = sum(responses[i][2] * weights[i] for i in range(len(responses)))
    max_sum = sum(max_scores[i] * weights[i] for i in range(len(max_scores)))
    return (earned_sum / max_sum) * 100 if max_sum > 0 else 0

def generate_segmented_pdf(state, tuned_scores, counsellor, all_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph(f"GLOBAL STRATEGIC ROADMAP: {state['name'].upper()}", styles['Title']))
    elements.append(Paragraph(f"Major: {state['course']} | Authorized by: {counsellor}", styles['Normal']))
    elements.append(Spacer(1, 20))

    for region in state['regions']:
        p_score = tuned_scores[region]
        elements.append(Paragraph(f"Target Region: {region} (Projected Score: {round(p_score, 1)}%)", styles['Heading2']))
        
        bench = all_bench.get(region, pd.DataFrame()).copy()
        if not bench.empty:
            bench["Gap %"] = ((p_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
            
            segments = [
                ("SAFE TO TARGET (Gap > -3%)", bench[bench["Gap %"] >= -3], colors.darkgreen),
                ("NEEDS STRENGTHENING (-3% to -15%)", bench[(bench["Gap %"] < -3) & (bench["Gap %"] >= -15)], colors.orange),
                ("SIGNIFICANT GAP (Gap < -15%)", bench[bench["Gap %"] < -15], colors.red)
            ]

            for title, df_s, color in segments:
                elements.append(Paragraph(title, ParagraphStyle('S', parent=styles['Heading3'], textColor=color)))
                if not df_s.empty:
                    data = [["University", "Bench Score", "Gap %"]]
                    # Sort by prestige (Bench Score) within segments
                    df_disp = df_s.sort_values("Total Benchmark Score", ascending=False).head(10)
                    for _, r in df_disp.iterrows():
                        data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Gap %'], 1)}%"])
                    t = Table(data, colWidths=[300, 80, 70])
                    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
                    elements.append(t)
                else:
                    elements.append(Paragraph("No universities currently matching this profile segment.", styles['Italic']))
                elements.append(Spacer(1, 10))
        elements.append(PageBreak())
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 3. STREAMLIT APPLICATION
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", layout="wide")

# Initialize Session State
if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'pdf_buffer' not in st.session_state: st.session_state.pdf_buffer = None
if 'report_ready' not in st.session_state: st.session_state.report_ready = False

# PAGE 1: SETUP
if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI: Global Strategy")
    name = st.text_input("Student Full Name")
    course = st.selectbox("Select Intended Major", ["CS/AI", "Data Science and Statistics", "Business and Administration", "Finance and Economics"])
    regions = st.multiselect("Select Target Regions", list(REGIONAL_WEIGHTS.keys()))
    
    if st.button("Initialize Assessment"):
        if name and regions:
            st.session_state.update({"name": name, "course": course, "regions": regions, "page": 'assessment'})
            st.rerun()

# PAGE 2: ASSESSMENT
elif st.session_state.page == 'assessment':
    q_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats.", "Business and Administration": "set_business", "Finance and Economics": "set_finance&eco."}
    
    # Error-proof file loading
    try:
        df = pd.read_csv(f"University Readiness_new (3).xlsx - {q_map[st.session_state.course]}.csv")
    except:
        st.error(f"Missing CSV: University Readiness_new (3).xlsx - {q_map[st.session_state.course]}.csv")
        st.stop()

    col_q, col_m = st.columns([0.6, 0.4])
    with col_q:
        st.header(f"Profile Audit: {st.session_state.name}")
        assessment_results = []
        max_scores = []
        
        for i, row in df.iterrows():
            st.write(f"**Q{i+1}. {row['Specific Question']}**")
            opts = ["None"]; v_map = {"None": 0}
            
            # Flexible Column Detection (Handles "Option A" or "Option A (Elite / Product)")
            for char in ['A', 'B', 'C', 'D']:
                opt_col = next((col for col in df.columns if f"Option {char}" in col), None)
                score_col = f"Score {char}"
                if opt_col and pd.notna(row[opt_col]):
                    lbl = f"{char}) {row[opt_col]}"
                    opts.append(lbl)
                    v_map[lbl] = row[score_col]
            
            sel = st.selectbox(f"Current Level (Q{i+1})", opts, key=f"q_{i}")
            assessment_results.append((row['Specific Question'], sel, v_map[sel], i))
            max_scores.append(row['Score A'])
            st.divider()

    with col_m:
        st.header("Global Readiness Meters")
        
        for reg in st.session_state.regions:
            score = calculate_regional_score(assessment_results, reg, max_scores)
            st.metric(f"{reg} Readiness", f"{round(score, 1)}%")
            st.progress(score/100)
        
        if st.button("Confirm Profile & Move to Tuner"):
            b_map = {"CS/AI": "benchmarking_cs", "Data Science and Statistics": "benchmarking_ds", "Business and Administration": "benchmarking_business", "Finance and Economics": "benchmarking_finance&economic"}
            try:
                bench_df = pd.read_csv(f"Benchmarking_USA (3) (2).xlsx - {b_map[st.session_state.course]}.csv")
                st.session_state.update({"res": assessment_results, "max": max_scores, "b_df": bench_df, "page": 'tuner'})
                st.rerun()
            except:
                st.error("Missing Benchmarking CSV files.")

# PAGE 3: STRATEGIC TUNER
elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Comparison Tuner")
    
    col_t, col_stats = st.columns([0.5, 0.5])
    with col_t:
        st.subheader("Simulate Profile Improvements")
        tuned_results = []
        for i, (q_text, orig_sel, orig_val, q_idx) in enumerate(st.session_state.res):
            st.write(f"**Target: {CATEGORIES[i]}**")
            # In the tuner, we allow them to keep original or move up
            # For brevity, this uses original values, but pulls from state
            t_sel = st.selectbox(f"Projected Goal for {CATEGORIES[i]}", [orig_sel], key=f"t_{i}")
            tuned_results.append((q_text, t_sel, orig_val, q_idx))

    with col_stats:
        st.subheader("Regional Impact Analysis")
        tuned_scores = {}
        all_bench_data = {}
        for reg in st.session_state.regions:
            c_score = calculate_regional_score(st.session_state.res, reg, st.session_state.max)
            p_score = calculate_regional_score(tuned_results, reg, st.session_state.max)
            tuned_scores[reg] = p_score
            
            st.markdown(f"**📍 {reg} Analysis**")
            m1, m2 = st.columns(2)
            m1.metric("Current Profile", f"{round(c_score,1)}%")
            m2.metric("Projected Profile", f"{round(p_score,1)}%", delta=f"{round(p_score-c_score,1)}%")
            
            # Segment counting
            bench = st.session_state.b_df.copy()
            bench["Gap %"] = ((p_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
            safe_count = len(bench[bench["Gap %"] >= -3])
            st.write(f"✅ **Safe to Target Universities:** {safe_count}")
            all_bench_data[reg] = bench
            st.divider()

    st.subheader("📥 Authorize & Generate Final Roadmap")
    c_name = st.text_input("Consultant Name")
    pin = st.text_input("Authorization PIN", type="password")

    if st.button("Generate Strategic PDF"):
        if pin == "304" and c_name:
            st.session_state.pdf_buffer = generate_segmented_pdf(st.session_state, tuned_scores, c_name, all_bench_data)
            st.session_state.report_ready = True
            st.success("Report Generated! Click below to download.")
        else:
            st.error("Unauthorized or Missing Name.")

    if st.session_state.report_ready:
        st.download_button(
            label="📥 Download Strategic Roadmap PDF",
            data=st.session_state.pdf_buffer,
            file_name=f"{st.session_state.name}_Admissions_Roadmap.pdf",
            mime="application/pdf"
        )
