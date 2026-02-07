import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# 1. REGIONAL WEIGHTS (The Admissions DNA)
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

# 2. FILE SCANNER (Prevents "File Not Found" errors)
def find_local_csv(keyword):
    """Scans the local directory for the CSV file based on keywords provided in the prompt."""
    files = [f for f in os.listdir(".") if f.endswith(".csv")]
    for f in files:
        if keyword.lower() in f.lower():
            return f
    return None

# 3. SCORING ENGINE (True Weighted Normalization)
def calculate_score(responses, country_key, max_scores):
    weights = REGIONAL_WEIGHTS.get(country_key, [0.1]*10)
    earned = sum(responses[i][2] * weights[i] for i in range(len(responses)))
    possible = sum(max_scores[i] * weights[i] for i in range(len(max_scores)))
    return (earned / possible) * 100 if possible > 0 else 0

# 4. PDF GENERATOR (Segmented Logic)
def generate_roadmap_pdf(state, tuned_scores, counsellor, all_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph(f"GLOBAL STRATEGIC ROADMAP: {state['name'].upper()}", styles['Title']))
    elements.append(Paragraph(f"Authorized by: {counsellor} | Major: {state['course']}", styles['Normal']))
    elements.append(Spacer(1, 20))

    for reg in state['regions']:
        p_score = tuned_scores[reg]
        elements.append(Paragraph(f"Region: {reg} (Projected readiness: {round(p_score, 1)}%)", styles['Heading2']))
        
        bench = all_bench.get(reg, pd.DataFrame()).copy()
        if not bench.empty:
            bench["Gap %"] = ((p_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
            
            segs = [
                ("SAFE TO TARGET (Gap > -3%)", bench[bench["Gap %"] >= -3], colors.darkgreen),
                ("NEEDS STRENGTHENING (-3% to -15%)", bench[(bench["Gap %"] < -3) & (bench["Gap %"] >= -15)], colors.orange),
                ("SIGNIFICANT GAP (Gap < -15%)", bench[bench["Gap %"] < -15], colors.red)
            ]

            for title, df_s, color in segs:
                elements.append(Paragraph(title, ParagraphStyle('S', parent=styles['Heading3'], textColor=color)))
                if not df_s.empty:
                    data = [["University", "Bench", "Gap %"]]
                    # Show Top 10 most competitive in each segment
                    for _, r in df_s.sort_values("Total Benchmark Score", ascending=False).head(10).iterrows():
                        data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Gap %'], 1)}%"])
                    t = Table(data, colWidths=[300, 60, 70])
                    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
                    elements.append(t)
                else:
                    elements.append(Paragraph("No universities found in this segment for current profile.", styles['Italic']))
                elements.append(Spacer(1, 10))
        elements.append(PageBreak())
    doc.build(elements)
    buffer.seek(0)
    return buffer

# 5. STREAMLIT UI
st.set_page_config(page_title="Admit AI", layout="wide")

if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'pdf' not in st.session_state: st.session_state.pdf = None

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    n = st.text_input("Student Name")
    c = st.selectbox("Major", ["CS/AI", "Data Science and Statistics", "Business and Administration", "Finance and Economics"])
    r = st.multiselect("Regions", list(REGIONAL_WEIGHTS.keys()))
    if st.button("Begin Assessment"):
        if n and r:
            st.session_state.update({"name": n, "course": c, "regions": r, "page": 'assessment'})
            st.rerun()

elif st.session_state.page == 'assessment':
    # Dynamic Map
    k_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats", "Business and Administration": "set_business", "Finance and Economics": "set_finance"}
    f_path = find_local_csv(k_map[st.session_state.course])
    
    if not f_path:
        st.error("Question file missing from directory.")
        st.stop()

    df = pd.read_csv(f_path)
    res = []
    max_s = []
    
    st.header(f"Profile: {st.session_state.name}")
    for i, row in df.iterrows():
        st.write(f"**Q{i+1}. {row['Specific Question']}**")
        opts = ["None"]; v_map = {"None": 0}
        for char in ['A', 'B', 'C', 'D']:
            col_name = next((c for c in df.columns if f"Option {char}" in c), None)
            if col_name and pd.notna(row[col_name]):
                lbl = f"{char}) {row[col_name]}"; opts.append(lbl); v_map[lbl] = row[f"Score {char}"]
        
        sel = st.selectbox("Status", opts, key=f"eval_{i}")
        res.append((row['Specific Question'], sel, v_map[sel], i))
        max_s.append(row['Score A'])
        st.divider()

    if st.button("Finalize Profile"):
        b_k = {"CS/AI": "benchmarking_cs", "Data Science and Statistics": "benchmarking_ds", "Business and Administration": "benchmarking_business", "Finance and Economics": "benchmarking_finance"}
        b_f = find_local_csv(b_k[st.session_state.course])
        st.session_state.update({"res": res, "max": max_s, "b_df": pd.read_csv(b_f), "page": 'tuner'})
        st.rerun()

elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Tuner")
    col_t, col_stats = st.columns([0.5, 0.5])
    
    with col_t:
        t_res = []
        for i, (q, s_l, s_v, q_idx) in enumerate(st.session_state.res):
            st.write(f"**Target: {CATEGORIES[i]}**")
            # Pulling original options for the tuner selectbox
            t_sel = st.selectbox("Upgrade Goal", [s_l], key=f"t_{i}")
            t_res.append((q, t_sel, s_v, q_idx))

    with col_stats:
        tuned_scores = {}
        all_b = {}
        for reg in st.session_state.regions:
            s = calculate_score(t_res, reg, st.session_state.max)
            tuned_scores[reg] = s
            st.metric(f"{reg} Target", f"{round(s,1)}%")
            all_b[reg] = st.session_state.b_df
            st.divider()

    c_name = st.text_input("Counsellor Name")
    if st.button("Generate Strategic Roadmap") and st.text_input("PIN", type="password") == "304":
        st.session_state.pdf = generate_roadmap_pdf(st.session_state, tuned_scores, c_name, all_b)
        st.success("Report Ready for Download!")

    if st.session_state.pdf:
        st.download_button("📥 Download Report", data=st.session_state.pdf, file_name=f"{st.session_state.name}_Roadmap.pdf")
