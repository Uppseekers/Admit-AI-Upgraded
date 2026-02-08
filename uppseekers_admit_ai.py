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
# 2. CORE UTILITIES
# ─────────────────────────────────────────────
def calculate_regional_score(responses, region, max_scores):
    weights = REGIONAL_WEIGHTS.get(region, [0.1]*10)
    earned = sum(responses[i][2] * weights[i] for i in range(len(responses)))
    possible = sum(max_scores[i] * weights[i] for i in range(len(max_scores)))
    return (earned / possible) * 100 if possible > 0 else 0

def find_file_fuzzy(prefix, keyword):
    """Searches directory for a file matching prefix and keyword."""
    for f in os.listdir("."):
        if prefix.lower() in f.lower() and keyword.lower() in f.lower() and f.endswith(".csv"):
            return f
    return None

def generate_pdf_report(state, tuned_scores, counsellor, all_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph(f"GLOBAL STRATEGIC ROADMAP: {state['name'].upper()}", styles['Title']))
    elements.append(Paragraph(f"Authorized by: {counsellor} | Major: {state['course']}", styles['Normal']))
    elements.append(Spacer(1, 20))

    for reg in state['regions']:
        p_score = tuned_scores[reg]
        elements.append(Paragraph(f"Target Region: {reg} (Projected Score: {round(p_score, 1)}%)", styles['Heading2']))
        
        bench = all_bench.get(reg, pd.DataFrame()).copy()
        if not bench.empty:
            # Segmenting Universities
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
                    for _, r in df_s.sort_values("Total Benchmark Score", ascending=False).head(10).iterrows():
                        data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Gap %'], 1)}%"])
                    t = Table(data, colWidths=[300, 80, 70])
                    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
                    elements.append(t)
                else:
                    elements.append(Paragraph("No matches found in this profile segment.", styles['Italic']))
                elements.append(Spacer(1, 10))
        elements.append(PageBreak())
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 3. STREAMLIT UI
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", layout="wide")

if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'pdf_buffer' not in st.session_state: st.session_state.pdf_buffer = None

# PAGE 1: SETUP
if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    idx_file = find_file_fuzzy("University Readiness", "Sheet1")
    if not idx_file:
        st.error("Index file missing.")
        st.stop()
    
    idx_df = pd.read_csv(idx_file)
    name = st.text_input("Student Name")
    course = st.selectbox("Major", idx_df['course'].tolist())
    regions = st.multiselect("Regions", list(REGIONAL_WEIGHTS.keys()))
    
    if st.button("Start Analysis"):
        if name and regions:
            # Map index values
            q_keyword = idx_df[idx_df['course'] == course]['next_questions_set'].values[0]
            st.session_state.update({"name": name, "course": course, "regions": regions, "q_kw": q_keyword, "page": 'assessment'})
            st.rerun()

# PAGE 2: ASSESSMENT
elif st.session_state.page == 'assessment':
    q_file = find_file_fuzzy("University Readiness", st.session_state.q_kw)
    if not q_file:
        st.error("Question set not found.")
        st.stop()

    df = pd.read_csv(q_file)
    res = []; max_s = []
    
    st.header(f"Profile Audit: {st.session_state.name}")
    for i, row in df.iterrows():
        st.write(f"**Q{i+1}. {row['Specific Question']}**")
        opts = ["None"]; v_map = {"None": 0}
        
        # FLEXIBLE COLUMN FINDER: Handles 'Option A', 'Option A (Elite / Product)', etc.
        for char in ['A', 'B', 'C', 'D']:
            col_name = next((c for c in df.columns if c.strip().startswith(f"Option {char}")), None)
            if col_name and pd.notna(row[col_name]):
                lbl = f"{char}) {row[col_name]}"
                opts.append(lbl)
                v_map[lbl] = row[f"Score {char}"]
        
        sel = st.selectbox("Select Status", opts, key=f"q_{i}")
        res.append((row['Specific Question'], sel, v_map[sel], i))
        max_s.append(row['Score A'])
        st.divider()

    if st.button("Confirm Profile"):
        # Map Benchmarking File
        b_idx_file = find_file_fuzzy("Benchmarking_USA", "Sheet1")
        b_idx_df = pd.read_csv(b_idx_file)
        b_kw = b_idx_df[b_idx_df['course'] == st.session_state.course]['benchmarking_set'].values[0]
        b_file = find_file_fuzzy("Benchmarking_USA", b_kw)
        
        st.session_state.update({"res": res, "max": max_s, "b_df": pd.read_csv(b_file), "page": 'tuner'})
        st.rerun()

# PAGE 3: STRATEGIC TUNER
elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Comparison Tuner")
    col_t, col_stats = st.columns([0.5, 0.5])
    
    with col_t:
        tuned_res = []
        for i, (q, s_l, s_v, q_idx) in enumerate(st.session_state.res):
            st.write(f"**Target: {CATEGORIES[i]}**")
            # For brevity in tuning, user can keep original level or we assume upgrade path logic
            t_sel = st.selectbox("Simulated Goal", [s_l], key=f"t_{i}")
            tuned_res.append((q, t_sel, s_v, q_idx))

    with col_stats:
        tuned_scores = {}
        for reg in st.session_state.regions:
            score = calculate_regional_score(tuned_res, reg, st.session_state.max)
            tuned_scores[reg] = score
            st.metric(reg, f"{round(score,1)}%")
            st.divider()

    c_name = st.text_input("Enter Counsellor Name")
    if st.button("Generate Roadmap") and st.text_input("PIN", type="password") == "304":
        st.session_state.pdf_buffer = generate_pdf_report(st.session_state, tuned_scores, c_name, {reg: st.session_state.b_df for reg in st.session_state.regions})
        st.success("Report Ready!")

    if st.session_state.pdf_buffer:
        st.download_button("📥 Download PDF", data=st.session_state.pdf_buffer, file_name=f"{st.session_state.name}_Strategy.pdf")
