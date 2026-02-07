import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. GLOBAL REGIONAL WEIGHTING MATRIX (DNA)
# ─────────────────────────────────────────────
# Each list represents the weight of Q1 through Q10 for that region.
# Q5 (Research) and Q7 (Internships) are high-sensitivity movers.
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

# ─────────────────────────────────────────────
# 2. APP UI & STYLING
# ─────────────────────────────────────────────
st.set_page_config(page_title="Admit AI: Global Strategy", layout="wide")

def apply_styles():
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 10px; background-color: #004aad; color: white; font-weight: bold; height: 3.2em; border: none; }
        .score-box { background-color: #f0f2f6; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #004aad; margin-bottom: 15px; }
        .m-title { font-size: 1em; font-weight: bold; color: #004aad; margin-bottom: 5px; }
        .m-val { font-size: 2.2em; font-weight: bold; color: #333; }
        .comparison-label { font-size: 0.9em; font-weight: bold; color: #555; }
        .comparison-val { font-size: 1.3em; font-weight: bold; color: #004aad; }
        </style>
    """, unsafe_allow_html=True)

def calculate_regional_score(responses, country_key, max_scores):
    weights = REGIONAL_WEIGHTS.get(country_key, [0.1]*10)
    total_weighted = 0
    max_weighted = 0
    for i, (_, _, raw_val, _) in enumerate(responses):
        total_weighted += (raw_val * weights[i])
        max_weighted += (max_scores[i] * weights[i])
    
    if max_weighted == 0: return 0
    return (total_weighted / max_weighted) * 100

# ─────────────────────────────────────────────
# 3. REPORT GENERATOR (STRATEGIC SORTING)
# ─────────────────────────────────────────────
def generate_strategic_pdf(state, tuned_scores, counsellor_name, all_tuned_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Global Admit AI Strategic Roadmap: {state['name']}", styles['Title']))
    elements.append(Paragraph(f"<b>Planned Major:</b> {state['course']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Authorized By:</b> {counsellor_name}", styles['Normal']))
    elements.append(Spacer(1, 20))

    for region in state['regions']:
        elements.append(Paragraph(f"Region: {region} (Target Score: {round(tuned_scores[region], 1)}%)", styles['Heading2']))
        
        # Filtering and Gap Calculation
        bench = all_tuned_bench[region]
        if bench.empty:
            elements.append(Paragraph("No specific university data available for this region.", styles['Italic']))
            continue

        # STRATEGIC SORTING LOGIC
        # Safe to Target: Benchmark Score High -> Low
        safe_df = bench[bench["Gap %"] >= -3].sort_values("Total Benchmark Score", ascending=False)
        # Needs Strengthening: Benchmark Score Low -> High
        needs_df = bench[(bench["Gap %"] < -3) & (bench["Gap %"] >= -15)].sort_values("Total Benchmark Score", ascending=True)
        # Significant Gaps: Benchmark Score Low -> High
        gaps_df = bench[bench["Gap %"] < -15].sort_values("Total Benchmark Score", ascending=True)

        for title, df_cat, color in [("Safe to Target", safe_df, colors.darkgreen), 
                                     ("Needs Strengthening", needs_df, colors.orange), 
                                     ("Significant Gaps", gaps_df, colors.red)]:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading3'], textColor=color)))
            if not df_cat.empty:
                data = [["University", "Bench Score", "Gap %"]]
                for _, r in df_cat.head(10).iterrows():
                    data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Gap %'], 1)}%"])
                t = Table(data, colWidths=[300, 80, 70])
                t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
                elements.append(t)
            else:
                elements.append(Paragraph("No matches in this category.", styles['Italic']))
            elements.append(Spacer(1, 10))
        
        elements.append(PageBreak())

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. MAIN APP LOGIC
# ─────────────────────────────────────────────
apply_styles()

if 'page' not in st.session_state: st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI: Global Assessment")
    with st.container():
        name = st.text_input("Student Name")
        course = st.selectbox("Select Major", ["CS/AI", "Data Science and Statistics", "Business and Administration", "Finance and Economics"])
        selected_regions = st.multiselect("Select Target Regions", list(REGIONAL_WEIGHTS.keys()))
        
        if st.button("Start Global Analysis"):
            if name and selected_regions:
                st.session_state.update({"name": name, "course": course, "regions": selected_regions, "page": 'assessment'})
                st.rerun()

elif st.session_state.page == 'assessment':
    col_q, col_meter = st.columns([0.6, 0.4])
    
    q_map = {
        "CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats.", 
        "Business and Administration": "set_business", "Finance and Economics": "set_finance&eco."
    }
    
    # LOAD DATA: Look for column "Specific Question"
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])
    q_df.columns = [c.strip() for c in q_df.columns]
    
    with col_q:
        st.header(f"Profile: {st.session_state.course}")
        current_responses = []
        max_scores_list = []
        
        for idx, row in q_df.iterrows():
            q_text = row.get('Specific Question', f"Question {idx+1}")
            st.write(f"**{q_text}**")
            
            opts = ["None"]; v_map = {"None": 0}
            for c in ['A', 'B', 'C', 'D']:
                opt_col = next((col for col in q_df.columns if f"Option {c}" in col), None)
                score_col = f'Score {c}'
                if opt_col and pd.notna(row[opt_col]):
                    label = f"{c}) {str(row[opt_col]).strip()}"
                    opts.append(label); v_map[label] = row[score_col]
            
            sel = st.selectbox("Current Status", opts, key=f"q{idx}")
            current_responses.append((q_text, sel, v_map[sel], idx))
            max_scores_list.append(row['Score A'])
            st.divider()

    with col_meter:
        st.header("🌍 Regional Readiness")
        st.info("Scores are calculated using region-specific weights.")
        for region in st.session_state.regions:
            r_score = calculate_regional_score(current_responses, region, max_scores_list)
            st.markdown(f"""<div class="score-box"><div class="m-title">{region}</div><div class="m-val">{round(r_score, 1)}%</div></div>""", unsafe_allow_html=True)
            st.progress(r_score / 100)

        if st.button("Proceed to Strategic Tuner"):
            b_map = {"CS/AI": "benchmarking_cs", "Data Science and Statistics": "benchmarking_ds", "Business and Administration": "benchmarking_business", "Finance and Economics": "benchmarking_finance&economic"}
            bench_raw = pd.read_excel("Benchmarking_USA (3) (2).xlsx", sheet_name=b_map[st.session_state.course])
            st.session_state.update({"current_responses": current_responses, "max_scores": max_scores_list, "bench_raw": bench_raw, "page": 'tuner'})
            st.rerun()

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
                score_col = f'Score {c}'
                if opt_col and pd.notna(row[opt_col]):
                    label = f"{c}) {str(row[opt_col]).strip()}"
                    opts.append(label); v_map[label] = row[score_col]
            
            st.markdown(f"**{row.get('Specific Question', q_text)}**")
            t_sel = st.selectbox("Improvement Goal", opts, index=opts.index(orig_sel), key=f"t{i}")
            tuned_responses.append((q_text, t_sel, v_map[t_sel], q_id))

    with col_stats:
        st.subheader("📊 Cross-Regional Impact")
        all_tuned_bench = {}
        tuned_regional_scores = {}
        
        for region in st.session_state.regions:
            c_score = calculate_regional_score(st.session_state.current_responses, region, st.session_state.max_scores)
            p_score = calculate_regional_score(tuned_responses, region, st.session_state.max_scores)
            tuned_regional_scores[region] = p_score
            
            st.markdown(f"#### 📍 {region}")
            m1, m2 = st.columns(2)
            m1.metric("Current", f"{round(c_score,1)}%")
            m2.metric("Planned", f"{round(p_score,1)}%", delta=f"{round(p_score-c_score,1)}%")
            
            # Regional Gap Analysis
            bench = st.session_state.bench_raw[st.session_state.bench_raw["Country"] == region].copy() if "Country" in st.session_state.bench_raw.columns else st.session_state.bench_raw.copy()
            if not bench.empty:
                bench["Gap %"] = ((p_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
                all_tuned_bench[region] = bench
                st.write(f"**Safe Schools:** {len(bench[bench['Gap %'] >= -3])} | **Reach Schools:** {len(bench[bench['Gap %'] < -3])}")
            st.divider()

    c_name = st.text_input("Counsellor Name")
    if st.button("Generate Detailed PDF Report") and st.text_input("PIN", type="password") == "304":
        pdf = generate_strategic_pdf(st.session_state, tuned_regional_scores, c_name, all_tuned_bench)
        st.download_button("Download Report", data=pdf, file_name=f"{st.session_state.name}_Global_Strategy.pdf")
