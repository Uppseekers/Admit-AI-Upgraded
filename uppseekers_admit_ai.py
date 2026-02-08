import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. REGIONAL WEIGHTING MATRIX (THE DNA)
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
# 2. FILE SEARCH ENGINE (INDEX-AWARE)
# ─────────────────────────────────────────────
def find_csv(keyword):
    """Finds a CSV file containing the keyword in its name."""
    for f in os.listdir("."):
        if keyword.lower() in f.lower() and f.endswith(".csv"):
            return f
    return None

def calculate_regional_score(responses, region, max_scores):
    weights = REGIONAL_WEIGHTS.get(region, [0.1]*10)
    earned = sum(responses[i][2] * weights[i] for i in range(len(responses)))
    possible = sum(max_scores[i] * weights[i] for i in range(len(max_scores)))
    return (earned / possible) * 100 if possible > 0 else 0

# ─────────────────────────────────────────────
# 3. PDF GENERATOR (SEGMENTED)
# ─────────────────────────────────────────────
def generate_roadmap_pdf(state, tuned_scores, counsellor, all_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph(f"GLOBAL ADMISSIONS STRATEGY: {state['name'].upper()}", styles['Title']))
    elements.append(Paragraph(f"Authorized by: {counsellor} | Major: {state['course']}", styles['Normal']))
    elements.append(Spacer(1, 20))

    for reg in state['regions']:
        p_score = tuned_scores[reg]
        elements.append(Paragraph(f"Target Region: {reg} (Projected Score: {round(p_score, 1)}%)", styles['Heading2']))
        
        bench = all_bench.get(reg, pd.DataFrame()).copy()
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

# ─────────────────────────────────────────────
# 4. STREAMLIT APPLICATION
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", layout="wide")

if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'pdf_buffer' not in st.session_state: st.session_state.pdf_buffer = None

# --- PAGE 1: SETUP ---
if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    # Load Course Index from Sheet1
    idx_file = find_csv("Readiness") # Looking for 'University Readiness_new (3).xlsx - Sheet1.csv'
    if not idx_file:
        st.error("Index file (Sheet1) not found.")
        st.stop()
    
    idx_df = pd.read_csv(idx_file)
    name = st.text_input("Student Name")
    course = st.selectbox("Intended Major", idx_df['course'].tolist())
    regions = st.multiselect("Select Target Regions", list(REGIONAL_WEIGHTS.keys()))
    
    if st.button("Start Assessment"):
        if name and regions:
            q_kw = idx_df[idx_df['course'] == course]['next_questions_set'].values[0]
            st.session_state.update({"name": name, "course": course, "regions": regions, "q_kw": q_kw, "page": 'assessment'})
            st.rerun()

# --- PAGE 2: ASSESSMENT ---
elif st.session_state.page == 'assessment':
    q_file = find_csv(st.session_state.q_kw)
    if not q_file:
        st.error(f"Set file for {st.session_state.q_kw} not found.")
        st.stop()

    df_q = pd.read_csv(q_file)
    res = []; max_s = []
    
    st.header(f"Assessment: {st.session_state.name}")
    for i, row in df_q.iterrows():
        st.write(f"**Q{i+1}. {row['Specific Question']}**")
        opts = ["None"]; v_map = {"None": 0}
        
        for char in ['A', 'B', 'C', 'D']:
            col_name = next((c for c in df_q.columns if c.strip().startswith(f"Option {char}")), None)
            if col_name and pd.notna(row[col_name]):
                lbl = f"{char}) {row[col_name]}"
                opts.append(lbl)
                v_map[lbl] = row[f"Score {char}"]
        
        sel = st.selectbox("Level", opts, key=f"q_{i}")
        res.append((row['Specific Question'], sel, v_map[sel], i))
        max_s.append(row['Score A'])
        st.divider()

    if st.button("Calculate Global Readiness"):
        # Find Benchmarking file using its index
        b_idx_file = find_csv("Benchmarking_USA (3) (2).xlsx - Sheet1.csv") or find_csv("Benchmarking_USA (3).xlsx - Sheet1.csv")
        b_idx_df = pd.read_csv(b_idx_file)
        b_kw = b_idx_df[b_idx_df['course'] == st.session_state.course]['benchmarking_set'].values[0]
        b_file = find_csv(b_kw)
        
        st.session_state.update({"res": res, "max": max_s, "b_df": pd.read_csv(b_file), "q_df": df_q, "page": 'tuner'})
        st.rerun()

# --- PAGE 3: STRATEGIC TUNER ---
elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Comparison Tuner")
    col_t, col_stats = st.columns([0.5, 0.5])
    
    with col_t:
        st.subheader("Simulate Improvements")
        tuned_res = []
        for i, (q_text, orig_sel, orig_val, q_idx) in enumerate(st.session_state.res):
            row = st.session_state.q_df.iloc[q_idx]
            opts = ["None"]; v_map = {"None": 0}
            for char in ['A', 'B', 'C', 'D']:
                col_name = next((c for c in st.session_state.q_df.columns if c.strip().startswith(f"Option {char}")), None)
                if col_name and pd.notna(row[col_name]):
                    lbl = f"{char}) {row[col_name]}"; opts.append(lbl); v_map[lbl] = row[f"Score {char}"]
            
            st.write(f"**Target: {CATEGORIES[i]}**")
            t_sel = st.selectbox("Plan Goal", opts, index=opts.index(orig_sel), key=f"t_{i}")
            tuned_res.append((q_text, t_sel, v_map[t_sel], q_idx))

    with col_stats:
        tuned_scores = {reg: calculate_regional_score(tuned_res, reg, st.session_state.max) for reg in st.session_state.regions}
        for reg, s in tuned_scores.items():
            st.metric(f"Projected {reg} Score", f"{round(s,1)}%")
            st.divider()

    c_name = st.text_input("Counsellor Name")
    if st.button("Generate Final Report") and st.text_input("PIN", type="password") == "304":
        st.session_state.pdf_buffer = generate_roadmap_pdf(st.session_state, tuned_scores, c_name, {reg: st.session_state.b_df for reg in st.session_state.regions})
        st.success("Report Ready!")

    if st.session_state.pdf_buffer:
        st.download_button("📥 Download PDF Roadmap", data=st.session_state.pdf_buffer, file_name=f"{st.session_state.name}_Strategic_Roadmap.pdf")
