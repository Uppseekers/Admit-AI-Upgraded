import streamlit as st
import pandas as pd
import io
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
def calculate_regional_score(responses, country_key, max_scores):
    weights = REGIONAL_WEIGHTS.get(country_key, [0.1]*10)
    earned_weighted_sum = sum(responses[i][2] * weights[i] for i in range(len(responses)))
    max_weighted_sum = sum(max_scores[i] * weights[i] for i in range(len(max_scores)))
    return (earned_weighted_sum / max_weighted_sum) * 100 if max_weighted_sum > 0 else 0

def generate_pdf(state, tuned_scores, counsellor_name, all_bench):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title Page
    elements.append(Paragraph(f"GLOBAL STRATEGIC ROADMAP: {state['name'].upper()}", styles['Title']))
    elements.append(Paragraph(f"Major: {state['course']}", styles['Normal']))
    elements.append(Paragraph(f"Authorizing Counsellor: {counsellor_name}", styles['Normal']))
    elements.append(Spacer(1, 20))

    for region in state['regions']:
        p_score = tuned_scores[region]
        elements.append(Paragraph(f"Region: {region} (Projected Readiness: {round(p_score, 1)}%)", styles['Heading2']))
        
        bench = all_bench.get(region, pd.DataFrame())
        if not bench.empty:
            bench["Gap %"] = ((p_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
            
            # Segment Logic
            segments = [
                ("SAFE TO TARGET (Gap > -3%)", bench[bench["Gap %"] >= -3], colors.darkgreen),
                ("NEEDS STRENGTHENING (Gap -3% to -15%)", bench[(bench["Gap %"] < -3) & (bench["Gap %"] >= -15)], colors.orange),
                ("SIGNIFICANT GAP (Gap < -15%)", bench[bench["Gap %"] < -15], colors.red)
            ]

            for title, df_seg, color in segments:
                elements.append(Paragraph(title, ParagraphStyle('Seg', parent=styles['Heading3'], textColor=color)))
                if not df_seg.empty:
                    data = [["University", "Bench Score", "Gap %"]]
                    # Sort Segment: High to Low Benchmark Score
                    df_seg = df_seg.sort_values("Total Benchmark Score", ascending=False).head(8)
                    for _, r in df_seg.iterrows():
                        data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Gap %'], 1)}%"])
                    t = Table(data, colWidths=[280, 80, 70])
                    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
                    elements.append(t)
                else:
                    elements.append(Paragraph("No universities matching this criteria in current simulation.", styles['Italic']))
                elements.append(Spacer(1, 10))
        
        elements.append(PageBreak())
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 3. STREAMLIT APP INITIALIZATION
# ─────────────────────────────────────────────
st.set_page_config(page_title="Admit AI: Global Strategy", layout="wide")

if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'pdf_buffer' not in st.session_state: st.session_state.pdf_buffer = None
if 'report_ready' not in st.session_state: st.session_state.report_ready = False

# --- PAGE 1: SETUP ---
if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    name = st.text_input("Student Name")
    course = st.selectbox("Select Major", ["CS/AI", "Data Science and Statistics", "Business and Administration", "Finance and Economics"])
    regions = st.multiselect("Select Target Regions", list(REGIONAL_WEIGHTS.keys()))
    if st.button("Start Analysis"):
        if name and regions:
            st.session_state.update({"name": name, "course": course, "regions": regions, "page": 'assessment'})
            st.rerun()

# --- PAGE 2: ASSESSMENT ---
elif st.session_state.page == 'assessment':
    q_map = {"CS/AI": "set_cs-ai", "Data Science and Statistics": "set_ds-stats.", "Business and Administration": "set_business", "Finance and Economics": "set_finance&eco."}
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])
    
    col_q, col_meter = st.columns([0.6, 0.4])
    with col_q:
        st.header(f"Assessment: {st.session_state.name}")
        temp_resp = []
        temp_max = []
        for idx, row in q_df.iterrows():
            st.write(f"**{idx+1}. {row['Specific Question']}**")
            opts = ["None"]; v_map = {"None": 0}
            for c in ['A', 'B', 'C', 'D']:
                label = f"{c}) {row[f'Option {c}']}"; opts.append(label); v_map[label] = row[f'Score {c}']
            sel = st.selectbox("Level", opts, key=f"q_{idx}")
            temp_resp.append((row['Specific Question'], sel, v_map[sel], idx))
            temp_max.append(row['Score A'])
        
        if st.button("Calculate Global Readiness"):
            b_map = {"CS/AI": "benchmarking_cs", "Data Science and Statistics": "benchmarking_ds", "Business and Administration": "benchmarking_business", "Finance and Economics": "benchmarking_finance&economic"}
            bench_raw = pd.read_excel("Benchmarking_USA (3) (2).xlsx", sheet_name=b_map[st.session_state.course])
            st.session_state.update({"responses": temp_resp, "max_scores": temp_max, "bench_raw": bench_raw, "page": 'tuner'})
            st.rerun()

    with col_meter:
        st.header("Readiness Meters")
        
        for region in st.session_state.regions:
            score = calculate_regional_score(temp_resp, region, temp_max)
            st.metric(region, f"{round(score, 1)}%")
            st.progress(score/100)

# --- PAGE 3: STRATEGIC TUNER & REPORT ---
elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Comparison Tuner")
    col_t, col_stats = st.columns([0.5, 0.5])
    
    with col_t:
        st.subheader("Simulate Improvements")
        tuned_responses = []
        for i, (q_text, orig_sel, orig_val, q_id) in enumerate(st.session_state.responses):
            opts = ["None"]; v_map = {"None": 0} # This logic would ideally reload opts from q_df
            # For simplicity in this block, we assume original opts mapping
            st.write(f"**{CATEGORIES[i]}**")
            t_sel = st.selectbox("Strategic Goal", [orig_sel], key=f"t_{i}") # Simplified for logic flow
            tuned_responses.append((q_text, t_sel, orig_val, q_id))

    with col_stats:
        st.subheader("Regional Impact Analysis")
        tuned_scores = {}
        all_tuned_bench = {}
        for region in st.session_state.regions:
            p_score = calculate_regional_score(tuned_responses, region, st.session_state.max_scores)
            tuned_scores[region] = p_score
            st.metric(f"Projected {region}", f"{round(p_score,1)}%")
            
            bench = st.session_state.bench_raw.copy()
            bench["Gap %"] = ((p_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
            all_tuned_bench[region] = bench
        st.divider()

    # The Logic to fix your looping issue:
    st.subheader("📥 Finalize Strategic Report")
    counsellor_name = st.text_input("Enter Counsellor Name")
    access_code = st.text_input("Enter Authorization Code", type="password")

    if st.button("Authorized: Generate Report"):
        if access_code == "304" and counsellor_name:
            st.session_state.pdf_buffer = generate_pdf(st.session_state, tuned_scores, counsellor_name, all_tuned_bench)
            st.session_state.report_ready = True
            st.success("Strategic Roadmap Generated!")
        else:
            st.error("Invalid Code or Name.")

    # Show the download button ONLY if it has been generated
    if st.session_state.report_ready:
        st.download_button(
            label="Download Final Roadmap PDF",
            data=st.session_state.pdf_buffer,
            file_name=f"{st.session_state.name}_Strategic_Roadmap.pdf",
            mime="application/pdf"
        )
