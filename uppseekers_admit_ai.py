import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. REGIONAL DNA (WEIGHTS)
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
# 2. DYNAMIC FILE DISCOVERY
# ─────────────────────────────────────────────
def find_file(keywords):
    """Finds a CSV file that contains all the keywords in its name."""
    files = [f for f in os.listdir(".") if f.endswith(".csv")]
    for f in files:
        if all(k.lower() in f.lower() for k in keywords):
            return f
    return None

def calculate_score(responses, region, max_scores):
    weights = REGIONAL_WEIGHTS.get(region, [0.1]*10)
    earned = sum(responses[i][2] * weights[i] for i in range(len(responses)))
    possible = sum(max_scores[i] * weights[i] for i in range(len(max_scores)))
    return (earned / possible) * 100 if possible > 0 else 0

# ─────────────────────────────────────────────
# 3. PDF ENGINE
# ─────────────────────────────────────────────
def generate_pdf(state, tuned_scores, counsellor, all_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph(f"GLOBAL STRATEGIC ROADMAP: {state['name'].upper()}", styles['Title']))
    elements.append(Paragraph(f"Major: {state['course']} | Authorized by: {counsellor}", styles['Normal']))
    elements.append(Spacer(1, 20))

    for reg in state['regions']:
        score = tuned_scores[reg]
        elements.append(Paragraph(f"Region: {reg} (Projected Score: {round(score, 1)}%)", styles['Heading2']))
        bench = all_bench.get(reg, pd.DataFrame()).copy()
        if not bench.empty:
            bench["Gap %"] = ((score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
            for title, df_s, color in [
                ("SAFE TO TARGET (Gap > -3%)", bench[bench["Gap %"] >= -3], colors.darkgreen),
                ("NEEDS STRENGTHENING (-3% to -15%)", bench[(bench["Gap %"] < -3) & (bench["Gap %"] >= -15)], colors.orange),
                ("SIGNIFICANT GAP (Gap < -15%)", bench[bench["Gap %"] < -15], colors.red)
            ]:
                elements.append(Paragraph(title, ParagraphStyle('S', parent=styles['Heading3'], textColor=color)))
                if not df_s.empty:
                    data = [["University", "Score", "Gap %"]]
                    for _, r in df_s.sort_values("Total Benchmark Score", ascending=False).head(10).iterrows():
                        data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Gap %'], 1)}%"])
                    t = Table(data, colWidths=[280, 60, 70])
                    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
                    elements.append(t)
                else: elements.append(Paragraph("No matches.", styles['Italic']))
                elements.append(Spacer(1, 10))
        elements.append(PageBreak())
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. APP FLOW
# ─────────────────────────────────────────────
st.set_page_config(page_title="Admit AI", layout="wide")
if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'pdf' not in st.session_state: st.session_state.pdf = None

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    # Discover Readiness Index
    idx_f = find_file(["Readiness", "Sheet1"])
    if not idx_f:
        st.error("Index file for Readiness (Sheet1) not found.")
        st.stop()
    
    idx_df = pd.read_csv(idx_f)
    name = st.text_input("Student Name")
    course = st.selectbox("Select Major", idx_df['course'].tolist())
    regions = st.multiselect("Select Target Regions", list(REGIONAL_WEIGHTS.keys()))
    
    if st.button("Start Assessment"):
        if name and regions:
            q_kw = idx_df[idx_df['course'] == course]['next_questions_set'].values[0]
            st.session_state.update({"name": name, "course": course, "regions": regions, "q_kw": q_kw, "page": 'assessment'})
            st.rerun()

elif st.session_state.page == 'assessment':
    q_f = find_file(["Readiness", st.session_state.q_kw])
    if not q_f:
        st.error(f"Question file '{st.session_state.q_kw}' not found.")
        st.stop()

    df_q = pd.read_csv(q_f)
    res = []; max_s = []
    st.header(f"Assessment: {st.session_state.name}")
    for i, row in df_q.iterrows():
        st.write(f"**Q{i+1}. {row['Specific Question']}**")
        opts = ["None"]; v_map = {"None": 0}
        for char in ['A', 'B', 'C', 'D']:
            col = next((c for c in df_q.columns if c.strip().lower().startswith(f"option {char.lower()}")), None)
            if col and pd.notna(row[col]):
                lbl = f"{char}) {row[col]}"; opts.append(lbl); v_map[lbl] = row[f"Score {char}"]
        sel = st.selectbox("Current Status", opts, key=f"q_{i}")
        res.append((row['Specific Question'], sel, v_map[sel], i))
        max_s.append(row['Score A'])
        st.divider()

    if st.button("Move to Tuner"):
        b_idx_f = find_file(["Benchmarking", "Sheet1"])
        b_idx_df = pd.read_csv(b_idx_f)
        b_kw = b_idx_df[b_idx_df['course'] == st.session_state.course]['benchmarking_set'].values[0]
        b_f = find_file(["Benchmarking", b_kw])
        st.session_state.update({"res": res, "max": max_s, "b_df": pd.read_csv(b_f), "q_df": df_q, "page": 'tuner'})
        st.rerun()

elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Tuner")
    
    
    
    col_t, col_stats = st.columns([0.5, 0.5])
    with col_t:
        t_res = []
        for i, (q, s_l, s_v, q_idx) in enumerate(st.session_state.res):
            row = st.session_state.q_df.iloc[q_idx]
            opts = ["None"]; v_map = {"None": 0}
            for char in ['A', 'B', 'C', 'D']:
                col = next((c for c in st.session_state.q_df.columns if c.strip().lower().startswith(f"option {char.lower()}")), None)
                if col and pd.notna(row[col]):
                    lbl = f"{char}) {row[col]}"; opts.append(lbl); v_map[lbl] = row[f"Score {char}"]
            st.write(f"**Target: {CATEGORIES[i]}**")
            t_sel = st.selectbox("Simulate Goal", opts, index=opts.index(s_l), key=f"t_{i}")
            t_res.append((q, t_sel, v_map[t_sel], q_idx))

    with col_stats:
        tuned_scores = {reg: calculate_score(t_res, reg, st.session_state.max) for reg in st.session_state.regions}
        for reg, s in tuned_scores.items():
            st.metric(f"Projected {reg} Score", f"{round(s,1)}%")
            st.divider()

    c_name = st.text_input("Counsellor Name")
    if st.button("Generate Roadmap") and st.text_input("PIN", type="password") == "304":
        st.session_state.pdf = generate_pdf(st.session_state, tuned_scores, c_name, {reg: st.session_state.b_df for reg in st.session_state.regions})
        st.success("PDF Ready!")

    if st.session_state.pdf:
        st.download_button("📥 Download PDF", data=st.session_state.pdf, file_name=f"{st.session_state.name}_Roadmap.pdf")
