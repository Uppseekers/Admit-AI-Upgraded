import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. REGIONAL ADMISSIONS DNA (WEIGHTS)
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
# 2. FILE SEARCH UTILITIES
# ─────────────────────────────────────────────
def find_file_by_keyword(keyword):
    """Finds a CSV file in the current directory that contains the keyword."""
    keyword = str(keyword).lower().strip()
    for f in os.listdir("."):
        if f.endswith(".csv") and keyword in f.lower():
            return f
    return None

def get_mapping_data():
    """Reads the mapping sheets to find question and benchmark file keywords."""
    q_map_file = find_file_by_keyword("University Readiness_new (3).xlsx - Sheet1.csv")
    b_map_file = find_file_by_keyword("Benchmarking_USA (3) (2).xlsx - Sheet1.csv")
    
    if not q_map_file or not b_map_file:
        return None, None
    
    q_map = pd.read_csv(q_map_file)
    b_map = pd.read_csv(b_map_file)
    return q_map, b_map

# ─────────────────────────────────────────────
# 3. SCORING & PDF ENGINE
# ─────────────────────────────────────────────
def calculate_regional_score(responses, region, max_scores):
    weights = REGIONAL_WEIGHTS.get(region, [0.1]*10)
    earned = sum(responses[i][2] * weights[i] for i in range(len(responses)))
    possible = sum(max_scores[i] * weights[i] for i in range(len(max_scores)))
    return (earned / possible) * 100 if possible > 0 else 0

def generate_segmented_pdf(state, tuned_scores, counsellor, all_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph(f"GLOBAL ADMISSIONS STRATEGIC ROADMAP: {state['name'].upper()}", styles['Title']))
    elements.append(Paragraph(f"Major: {state['course']} | Counselor: {counsellor}", styles['Normal']))
    elements.append(Spacer(1, 20))

    for region in state['regions']:
        p_score = tuned_scores[region]
        elements.append(Paragraph(f"Target Region: {region} (Projected Score: {round(p_score, 1)}%)", styles['Heading2']))
        
        bench = all_bench.get(region, pd.DataFrame()).copy()
        if not bench.empty:
            # Clean benchmarking score column
            bench['Total Benchmark Score'] = pd.to_numeric(bench['Total Benchmark Score'], errors='coerce').fillna(0)
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
                    # Sort by competitiveness (Prestige) within segment
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
# 4. STREAMLIT UI & SESSION STATE
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", layout="wide")

if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'pdf_buffer' not in st.session_state: st.session_state.pdf_buffer = None
if 'report_ready' not in st.session_state: st.session_state.report_ready = False

# PAGE 1: SETUP
if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    q_map, b_map = get_mapping_data()
    
    if q_map is None:
        st.error("Mapping files (Sheet 1) missing. Please check your folder.")
        st.stop()
        
    name = st.text_input("Student Full Name")
    course_list = q_map['course'].unique().tolist()
    course = st.selectbox("Intended Major", course_list)
    regions = st.multiselect("Select Target Regions", list(REGIONAL_WEIGHTS.keys()))
    
    if st.button("Initialize Assessment"):
        if name and regions:
            # Get keywords from mapping
            q_keyword = q_map[q_map['course'] == course]['next_questions_set'].values[0]
            b_keyword = b_map[b_map['course'] == course]['benchmarking_set'].values[0]
            
            # Find actual files
            q_file = find_file_by_keyword(q_keyword)
            b_file = find_file_by_keyword(b_keyword)
            
            if q_file and b_file:
                st.session_state.update({
                    "name": name, "course": course, "regions": regions, 
                    "q_df": pd.read_csv(q_file), "b_df": pd.read_csv(b_file), 
                    "page": 'assessment'
                })
                st.rerun()
            else:
                st.error("Required data files not found based on Sheet 1 mapping.")

# PAGE 2: ASSESSMENT
elif st.session_state.page == 'assessment':
    df = st.session_state.q_df
    col_q, col_meter = st.columns([0.6, 0.4])
    
    with col_q:
        st.header(f"Profile Audit: {st.session_state.name}")
        assessment_responses = []
        max_scores = []
        
        for i, row in df.iterrows():
            st.write(f"**Q{i+1}. {row['Specific Question']}**")
            opts = ["None"]; v_map = {"None": 0}
            for char in ['A', 'B', 'C', 'D']:
                opt_col = next((c for c in df.columns if f"Option {char}" in c), None)
                if opt_col and pd.notna(row[opt_col]):
                    lbl = f"{char}) {row[opt_col]}"
                    opts.append(lbl)
                    v_map[lbl] = row[f"Score {char}"]
            
            sel = st.selectbox(f"Current Level (Q{i+1})", opts, key=f"q_{i}")
            assessment_responses.append((row['Specific Question'], sel, v_map[sel], i))
            max_scores.append(row['Score A'])
            st.divider()

    with col_meter:
        st.header("Readiness Meters")
        for reg in st.session_state.regions:
            score = calculate_regional_score(assessment_responses, reg, max_scores)
            st.metric(f"{reg} Baseline", f"{round(score, 1)}%")
            st.progress(score/100)
        
        if st.button("Lock Profile & Simulate Improvements"):
            st.session_state.update({"res": assessment_responses, "max": max_scores, "page": 'tuner'})
            st.rerun()

# PAGE 3: STRATEGIC TUNER
elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Comparison Tuner")
    col_t, col_stats = st.columns([0.5, 0.5])
    
    with col_t:
        st.subheader("Simulate Goals")
        tuned_responses = []
        df = st.session_state.q_df
        for i, (q_text, orig_sel, orig_val, q_idx) in enumerate(st.session_state.res):
            st.write(f"**{df.iloc[i]['Category']}**")
            # Rebuild options for current question
            opts = ["None"]; v_map = {"None": 0}
            for char in ['A', 'B', 'C', 'D']:
                opt_col = next((c for c in df.columns if f"Option {char}" in c), None)
                if opt_col and pd.notna(df.iloc[i][opt_col]):
                    lbl = f"{char}) {df.iloc[i][opt_col]}"
                    opts.append(lbl)
                    v_map[lbl] = df.iloc[i][f"Score {char}"]
            
            t_sel = st.selectbox(f"Strategic Plan for Q{i+1}", opts, index=opts.index(orig_sel), key=f"t_{i}")
            tuned_responses.append((q_text, t_sel, v_map[t_sel], q_idx))

    with col_stats:
        st.subheader("Global Impact Analysis")
        tuned_scores = {}
        all_bench_data = {}
        for reg in st.session_state.regions:
            c_score = calculate_regional_score(st.session_state.res, reg, st.session_state.max)
            p_score = calculate_regional_score(tuned_responses, reg, st.session_state.max)
            tuned_scores[reg] = p_score
            st.metric(f"Projected {reg} Score", f"{round(p_score,1)}%", delta=f"{round(p_score-c_score,1)}%")
            all_bench_data[reg] = st.session_state.b_df
            st.divider()

    st.subheader("📥 Authorize & Generate Roadmap")
    c_name = st.text_input("Enter Counselor Name")
    pin = st.text_input("Access PIN", type="password")

    if st.button("Generate Strategic PDF"):
        if pin == "304" and c_name:
            st.session_state.pdf_buffer = generate_segmented_pdf(st.session_state, tuned_scores, c_name, all_bench_data)
            st.session_state.report_ready = True
            st.success("Strategic Roadmap is ready!")
        else:
            st.error("Authorization Failed.")

    if st.session_state.report_ready:
        st.download_button(
            label="📥 Download Strategic Roadmap PDF",
            data=st.session_state.pdf_buffer,
            file_name=f"{st.session_state.name}_Strategic_Roadmap.pdf",
            mime="application/pdf"
        )
