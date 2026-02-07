import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# 1. REGIONAL ADMISSIONS DNA (WEIGHTS)
REGIONAL_WEIGHTS = {
    "USA": [0.20, 0.10, 0.05, 0.05, 0.15, 0.05, 0.20, 0.10, 0.05, 0.05],
    "UK": [0.25, 0.10, 0.05, 0.05, 0.30, 0.02, 0.10, 0.03, 0.00, 0.10],
    "Germany": [0.35, 0.10, 0.05, 0.05, 0.05, 0.00, 0.35, 0.00, 0.00, 0.05],
    "Singapore": [0.30, 0.10, 0.10, 0.15, 0.10, 0.02, 0.15, 0.03, 0.00, 0.05],
    "Australia": [0.30, 0.10, 0.10, 0.05, 0.10, 0.05, 0.20, 0.05, 0.00, 0.05],
    "Canada": [0.25, 0.10, 0.05, 0.05, 0.15, 0.05, 0.20, 0.10, 0.00, 0.05],
    "Netherlands": [0.35, 0.15, 0.05, 0.05, 0.10, 0.00, 0.25, 0.00, 0.00, 0.05],
    "European Countries": [0.30, 0.15, 0.05, 0.05, 0.10, 0.05, 0.20, 0.05, 0.00, 0.05],
    "Japan": [0.40, 0.10, 0.10, 0.10, 0.10, 0.00, 0.10, 0.05, 0.00, 0.05],
    "Other Asian": [0.40, 0.10, 0.15, 0.10, 0.05, 0.02, 0.10, 0.03, 0.00, 0.05]
}

CATEGORIES = ["Academics", "Rigor", "Testing", "Merit", "Research", "Engagement", "Experience", "Impact", "Public Voice", "Recognition"]

# 2. FILE SEARCH UTILITY
def find_csv(keyword):
    """Finds a CSV file containing the keyword in its name."""
    keyword = keyword.lower()
    for f in os.listdir("."):
        if f.endswith(".csv") and keyword in f.lower():
            return f
    return None

# 3. SCORING UTILITY
def get_weighted_score(responses, region, max_scores):
    weights = REGIONAL_WEIGHTS.get(region, [0.1]*10)
    earned = sum(responses[i][2] * weights[i] for i in range(len(responses)))
    possible = sum(max_scores[i] * weights[i] for i in range(len(max_scores)))
    return (earned / possible) * 100 if possible > 0 else 0

# 4. SEGMENTED PDF GENERATOR
def generate_pdf(state, tuned_scores, counsellor, all_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph(f"GLOBAL ADMISSIONS STRATEGY: {state['name'].upper()}", styles['Title']))
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
                    data = [["University", "Bench", "Gap %"]]
                    # Sort by prestige (Bench Score) within segments
                    df_disp = df_s.sort_values("Total Benchmark Score", ascending=False).head(10)
                    for _, r in df_disp.iterrows():
                        data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Gap %'], 1)}%"])
                    t = Table(data, colWidths=[300, 60, 70])
                    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
                    elements.append(t)
                else:
                    elements.append(Paragraph("No matches found in this segment.", styles['Italic']))
                elements.append(Spacer(1, 10))
        elements.append(PageBreak())
    doc.build(elements)
    buffer.seek(0)
    return buffer

# 5. STREAMLIT UI
st.set_page_config(page_title="Uppseekers Admit AI", layout="wide")

if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'pdf' not in st.session_state: st.session_state.pdf = None

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    n = st.text_input("Student Full Name")
    c = st.selectbox("Intended Major", ["CS/AI", "Data Science and Statistics", "Business and Administration", "Finance and Economics"])
    r = st.multiselect("Select Target Regions", list(REGIONAL_WEIGHTS.keys()))
    if st.button("Initialize Assessment"):
        if n and r:
            st.session_state.update({"name": n, "course": c, "regions": r, "page": 'assessment'})
            st.rerun()

elif st.session_state.page == 'assessment':
    # Map selection to file keywords
    key_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats", "Business and Administration": "set_business", "Finance and Economics": "set_finance"}
    f_path = find_csv(key_map[st.session_state.course])
    
    if not f_path:
        st.error(f"Error: Question file for {st.session_state.course} not found in directory.")
        st.stop()

    df = pd.read_csv(f_path)
    res = []; max_s = []
    
    st.header(f"Profile Audit: {st.session_state.name}")
    for i, row in df.iterrows():
        # Column C is 'Specific Question'
        st.write(f"**Q{i+1}. {row['Specific Question']}**")
        opts = ["None"]; v_map = {"None": 0}
        
        # Handle flexible column naming
        for char in ['A', 'B', 'C', 'D']:
            col_name = next((c for c in df.columns if f"Option {char}" in c), None)
            if col_name and pd.notna(row[col_name]):
                lbl = f"{char}) {row[col_name]}"
                opts.append(lbl)
                v_map[lbl] = row[f"Score {char}"]
        
        sel = st.selectbox("Current Level", opts, key=f"eval_{i}")
        res.append((row['Specific Question'], sel, v_map[sel], i))
        max_s.append(row['Score A'])
        st.divider()

    if st.button("Confirm Profile"):
        b_map = {"CS/AI": "benchmarking_cs", "Data Science and Statistics": "benchmarking_ds", "Business and Administration": "benchmarking_business", "Finance and Economics": "benchmarking_finance"}
        b_f = find_csv(b_map[st.session_state.course])
        st.session_state.update({"res": res, "max": max_s, "b_df": pd.read_csv(b_f), "page": 'tuner'})
        st.rerun()

elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Comparison Tuner")
    col_t, col_stats = st.columns([0.5, 0.5])
    
    with col_t:
        st.subheader("Simulate Profile Improvements")
        t_res = []
        for i, (q, s_l, s_v, q_idx) in enumerate(st.session_state.res):
            st.write(f"**Target Area: {CATEGORIES[i]}**")
            # We allow user to "stay" at their level or move up.
            t_sel = st.selectbox("Projected Goal", [s_l], key=f"t_{i}")
            t_res.append((q, t_sel, s_v, q_idx))

    with col_stats:
        tuned_scores = {}
        all_b = {}
        for reg in st.session_state.regions:
            s = get_weighted_score(t_res, reg, st.session_state.max)
            tuned_scores[reg] = s
            st.metric(f"{reg} Forecast", f"{round(s,1)}%")
            all_b[reg] = st.session_state.b_df
            st.divider()

    c_name = st.text_input("Enter Counsellor Name")
    if st.button("Generate Roadmap") and st.text_input("PIN", type="password") == "304":
        st.session_state.pdf = generate_pdf(st.session_state, tuned_scores, c_name, all_b)
        st.success("Strategic Roadmap is ready for download!")

    if st.session_state.pdf:
        st.download_button("📥 Download PDF Roadmap", data=st.session_state.pdf, file_name=f"{st.session_state.name}_Global_Strategy.pdf")
