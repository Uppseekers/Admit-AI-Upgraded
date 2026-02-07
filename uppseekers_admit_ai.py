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
# 2. HELPER FUNCTIONS
# ─────────────────────────────────────────────
def find_csv_by_keyword(keyword):
    """Finds any CSV file in the current directory containing the keyword."""
    files = [f for f in os.listdir(".") if f.endswith(".csv")]
    for f in files:
        if keyword.lower() in f.lower():
            return f
    return None

def calculate_regional_score(responses, country_key, max_scores):
    weights = REGIONAL_WEIGHTS.get(country_key, [0.1]*10)
    earned_sum = sum(responses[i][2] * weights[i] for i in range(len(responses)))
    max_sum = sum(max_scores[i] * weights[i] for i in range(len(max_scores)))
    return (earned_sum / max_sum) * 100 if max_sum > 0 else 0

def generate_strategic_pdf(state, tuned_scores, counsellor, all_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph(f"GLOBAL STRATEGIC ROADMAP: {state['name'].upper()}", styles['Title']))
    elements.append(Paragraph(f"Major: {state['course']} | Consultant: {counsellor}", styles['Normal']))
    elements.append(Spacer(1, 20))

    for region in state['regions']:
        p_score = tuned_scores[region]
        elements.append(Paragraph(f"Region: {region} (Projected Score: {round(p_score, 1)}%)", styles['Heading2']))
        
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
                    # Sort by competitiveness
                    df_disp = df_s.sort_values("Total Benchmark Score", ascending=False).head(10)
                    for _, r in df_disp.iterrows():
                        data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Gap %'], 1)}%"])
                    t = Table(data, colWidths=[300, 80, 70])
                    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
                    elements.append(t)
                else:
                    elements.append(Paragraph("No matches found in this segment.", styles['Italic']))
                elements.append(Spacer(1, 10))
        elements.append(PageBreak())
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 3. MAIN STREAMLIT APP
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", layout="wide")

# Persistent State Management
if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'pdf_buffer' not in st.session_state: st.session_state.pdf_buffer = None
if 'report_ready' not in st.session_state: st.session_state.report_ready = False

# PAGE 1: SETUP
if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    name = st.text_input("Student Full Name")
    course = st.selectbox("Intended Major", ["CS/AI", "Data Science and Statistics", "Business and Administration", "Finance and Economics"])
    regions = st.multiselect("Select Target Regions", list(REGIONAL_WEIGHTS.keys()))
    
    if st.button("Start Assessment"):
        if name and regions:
            st.session_state.update({"name": name, "course": course, "regions": regions, "page": 'assessment'})
            st.rerun()

# PAGE 2: ASSESSMENT
elif st.session_state.page == 'assessment':
    # Dynamic keyword mapping to find files regardless of prefix
    file_keywords = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats", "Business and Administration": "set_business", "Finance and Economics": "set_finance"}
    file_path = find_csv_by_keyword(file_keywords[st.session_state.course])
    
    if not file_path:
        st.error(f"Error: Question file for {st.session_state.course} not found in directory.")
        st.stop()

    df = pd.read_csv(file_path)
    col_q, col_m = st.columns([0.6, 0.4])
    
    with col_q:
        st.header(f"Profile Audit: {st.session_state.name}")
        assessment_results = []
        max_scores = []
        
        for i, row in df.iterrows():
            st.write(f"**Q{i+1}. {row['Specific Question']}**")
            opts = ["None"]; v_map = {"None": 0}
            for char in ['A', 'B', 'C', 'D']:
                opt_col = next((col for col in df.columns if f"Option {char}" in col), None)
                if opt_col and pd.notna(row[opt_col]):
                    lbl = f"{char}) {row[opt_col]}"
                    opts.append(lbl)
                    v_map[lbl] = row[f"Score {char}"]
            
            sel = st.selectbox(f"Select Status (Q{i+1})", opts, key=f"eval_{i}")
            assessment_results.append((row['Specific Question'], sel, v_map[sel], i))
            max_scores.append(row['Score A'])
            st.divider()

    with col_m:
        st.header("Readiness Meters")
        for reg in st.session_state.regions:
            score = calculate_regional_score(assessment_results, reg, max_scores)
            st.metric(f"{reg} Readiness", f"{round(score, 1)}%")
            st.progress(score/100)
        
        if st.button("Proceed to Strategic Tuner"):
            bench_keywords = {"CS/AI": "benchmarking_cs", "Data Science and Statistics": "benchmarking_ds", "Business and Administration": "benchmarking_business", "Finance and Economics": "benchmarking_finance"}
            bench_file = find_csv_by_keyword(bench_keywords[st.session_state.course])
            if bench_file:
                st.session_state.update({"res": assessment_results, "max": max_scores, "b_df": pd.read_csv(bench_file), "page": 'tuner'})
                st.rerun()
            else:
                st.error("Benchmarking data file not found.")

# PAGE 3: STRATEGIC TUNER & DOWNLOAD
elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Comparison Tuner")
    col_t, col_stats = st.columns([0.5, 0.5])
    
    with col_t:
        st.subheader("Simulate Profile Improvements")
        tuned_results = []
        for i, (q_text, orig_sel, orig_val, q_idx) in enumerate(st.session_state.res):
            st.write(f"**{CATEGORIES[i]}**")
            # In the tuner, we maintain the original value for baseline
            t_sel = st.selectbox(f"Simulate Goal for {CATEGORIES[i]}", [orig_sel], key=f"t_{i}")
            tuned_results.append((q_text, t_sel, orig_val, q_idx))

    with col_stats:
        st.subheader("Global Impact Analysis")
        tuned_scores = {}
        all_bench_data = {}
        for reg in st.session_state.regions:
            p_score = calculate_regional_score(tuned_results, reg, st.session_state.max)
            tuned_scores[reg] = p_score
            st.metric(f"Projected {reg} Score", f"{round(p_score,1)}%")
            all_bench_data[reg] = st.session_state.b_df
            st.divider()

    st.subheader("📥 Generate Final Strategic Report")
    c_name = st.text_input("Enter Counsellor Name")
    pin = st.text_input("Enter Admin PIN", type="password")

    if st.button("Authorize & Generate PDF"):
        if pin == "304" and c_name:
            st.session_state.pdf_buffer = generate_strategic_pdf(st.session_state, tuned_scores, c_name, all_bench_data)
            st.session_state.report_ready = True
            st.success("Report Generated! Click the button below.")
        else:
            st.error("Invalid PIN or Missing Name.")

    if st.session_state.report_ready:
        st.download_button(
            label="📥 Download Strategic Roadmap PDF",
            data=st.session_state.pdf_buffer,
            file_name=f"{st.session_state.name}_Global_Strategy.pdf",
            mime="application/pdf"
        )
