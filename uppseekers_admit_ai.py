import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# 1. REGIONAL ADMISSIONS DNA
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

# 2. DYNAMIC FILE LOCATOR (FUZZY SEARCH)
def find_file_fuzzy(keywords):
    """Finds a file that contains all the provided keywords."""
    for f in os.listdir("."):
        if all(k.lower() in f.lower() for k in keywords) and f.endswith(".csv"):
            return f
    return None

def get_sheet_from_index(index_keyword, course_name, target_col):
    """Reads the 'Sheet 1' index to find the specific data sheet name."""
    idx_file = find_file_fuzzy([index_keyword, "sheet1"])
    if idx_file:
        idx_df = pd.read_csv(idx_file)
        match = idx_df[idx_df['course'].str.strip() == course_name.strip()]
        if not match.empty:
            sheet_keyword = match.iloc[0][target_col]
            return find_file_fuzzy([sheet_keyword])
    return None

def calculate_score(responses, region, max_scores):
    weights = REGIONAL_WEIGHTS.get(region, [0.1]*10)
    earned = sum(responses[i][2] * weights[i] for i in range(len(responses)))
    possible = sum(max_scores[i] * weights[i] for i in range(len(max_scores)))
    return (earned / possible) * 100 if possible > 0 else 0

# 3. PDF REPORT GENERATOR
def generate_pdf(state, tuned_scores, counsellor, all_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph(f"STRATEGIC ADMISSIONS ROADMAP: {state['name'].upper()}", styles['Title']))
    elements.append(Paragraph(f"Major: {state['course']} | Consultant: {counsellor}", styles['Normal']))
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
                    for _, r in df_s.sort_values("Total Benchmark Score", ascending=False).head(10).iterrows():
                        data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Gap %'], 1)}%"])
                    t = Table(data, colWidths=[300, 60, 70])
                    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
                    elements.append(t)
                else:
                    elements.append(Paragraph("No matches currently found.", styles['Italic']))
                elements.append(Spacer(1, 10))
        elements.append(PageBreak())
    doc.build(elements)
    buffer.seek(0)
    return buffer

# 4. APP INITIALIZATION
st.set_page_config(page_title="Admit AI: Global Strategy", layout="wide")

if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'pdf' not in st.session_state: st.session_state.pdf = None

# --- PAGE 1: SETUP ---
if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    
    # Fuzzy find the Course Index file
    idx_file = find_file_fuzzy(["University Readiness", "sheet1"])
    if not idx_file:
        st.error("Critical Error: 'Sheet 1' index for University Readiness not found.")
        st.stop()
    
    idx_df = pd.read_csv(idx_file)
    courses = idx_df['course'].tolist()
    
    name = st.text_input("Student Name")
    course = st.selectbox("Select Major", courses)
    regions = st.multiselect("Target Regions", list(REGIONAL_WEIGHTS.keys()))
    
    if st.button("Proceed to Assessment"):
        if name and regions:
            st.session_state.update({"name": name, "course": course, "regions": regions, "page": 'assessment'})
            st.rerun()

# --- PAGE 2: ASSESSMENT ---
elif st.session_state.page == 'assessment':
    # Find data file using index logic
    q_file = get_sheet_from_index("University Readiness", st.session_state.course, 'next_questions_set')
    
    if not q_file:
        st.error(f"Error: Question data for {st.session_state.course} not found in index.")
        st.stop()

    df = pd.read_csv(q_file)
    res = []; max_s = []
    
    st.header(f"Assessment: {st.session_state.name}")
    for i, row in df.iterrows():
        st.write(f"**Q{i+1}. {row['Specific Question']}**")
        opts = ["None"]; v_map = {"None": 0}
        for char in ['A', 'B', 'C', 'D']:
            col = next((c for c in df.columns if f"Option {char}" in c), None)
            if col and pd.notna(row[col]):
                lbl = f"{char}) {row[col]}"; opts.append(lbl); v_map[lbl] = row[f"Score {char}"]
        
        sel = st.selectbox("Status", opts, key=f"q_{i}")
        res.append((row['Specific Question'], sel, v_map[sel], i))
        max_s.append(row['Score A'])
        st.divider()

    if st.button("Analyze Profile"):
        # Find benchmark file using index logic
        b_file = get_sheet_from_index("Benchmarking_USA", st.session_state.course, 'benchmarking_set')
        if b_file:
            st.session_state.update({"res": res, "max": max_s, "b_df": pd.read_csv(b_file), "page": 'tuner'})
            st.rerun()
        else:
            st.error("Benchmarking index error.")

# --- PAGE 3: TUNER & REPORT ---
elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Tuner")
    
    
    
    col_t, col_stats = st.columns([0.5, 0.5])
    with col_t:
        t_res = []
        for i, (q, s_l, s_v, q_idx) in enumerate(st.session_state.res):
            st.write(f"**{CATEGORIES[i]}**")
            t_sel = st.selectbox("Upgrade Path", [s_l], key=f"t_{i}")
            t_res.append((q, t_sel, s_v, q_idx))

    with col_stats:
        tuned_scores = {reg: calculate_score(t_res, reg, st.session_state.max) for reg in st.session_state.regions}
        for reg, score in tuned_scores.items():
            st.metric(f"{reg} Target", f"{round(score,1)}%")
            st.progress(score/100)
            st.divider()

    counsellor = st.text_input("Counsellor Name")
    if st.button("Generate Final Report") and st.text_input("PIN", type="password") == "304":
        st.session_state.pdf = generate_pdf(st.session_state, tuned_scores, counsellor, {reg: st.session_state.b_df for reg in st.session_state.regions})
        st.success("Report Ready!")

    if st.session_state.pdf:
        st.download_button("📥 Download PDF Roadmap", data=st.session_state.pdf, file_name=f"{st.session_state.name}_Strategic_Roadmap.pdf")
