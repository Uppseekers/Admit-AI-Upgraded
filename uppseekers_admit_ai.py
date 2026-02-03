import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. APP CONFIG & UI STYLING
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", page_icon="Uppseekers Logo.png", layout="wide")

def apply_styles():
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #004aad; color: white; font-weight: bold; border: none; }
        .card { background-color: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #f0f0f0; margin-bottom: 25px; }
        .score-box { background-color: #e8f0fe; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #004aad; margin-bottom: 20px; }
        .uni-card { padding: 10px; border-radius: 8px; margin-bottom: 5px; color: white; font-weight: bold; font-size: 0.85em; }
        h1, h2, h3 { color: #004aad; }
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA LOADING
# ─────────────────────────────────────────────
@st.cache_resource
def load_resources():
    try:
        q_xls = pd.ExcelFile("University Readiness_new.xlsx")
        q_idx = q_xls.parse(q_xls.sheet_names[0])
        q_map = dict(zip(q_idx.iloc[:,0], q_idx.iloc[:,1]))
        
        b_xls = pd.ExcelFile("Benchmarking_USA.xlsx")
        b_idx = b_xls.parse(b_xls.sheet_names[0])
        b_map = dict(zip(b_idx.iloc[:,0], b_idx.iloc[:,1]))
        
        return q_xls, q_map, b_xls, b_map
    except Exception as e:
        st.error(f"System Error: Required data files missing. ({e})")
        st.stop()

# ─────────────────────────────────────────────
# 3. PDF GENERATOR (CURRENT VS PLANNED)
# ─────────────────────────────────────────────
def generate_comparison_pdf(state, tuned_score, counsellor_name):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    logo_path = "Uppseekers Logo.png"
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=140, height=42); logo.hAlign = 'LEFT'
            elements.append(logo); elements.append(Spacer(1, 15))
        except: pass

    elements.append(Paragraph(f"Admit AI Strategy Report: {state.name}", styles['Title']))
    elements.append(Paragraph(f"<b>Current Score:</b> {round(state.current_total, 1)} | <b>Planned Score:</b> {round(tuned_score, 1)}", styles['Normal']))
    elements.append(Paragraph(f"<b>Counsellor:</b> {counsellor_name}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Improvement Summary
    elements.append(Paragraph("Strategic Growth Path", styles['Heading2']))
    elements.append(Paragraph(f"By implementing the tuned changes, the profile strength increases by {round(tuned_score - state.current_total, 1)} points, significantly expanding university eligibility.", styles['Normal']))
    elements.append(Spacer(1, 15))

    # 9-List Strategy (3 Countries x 3 Categories)
    # Using Tuned Score for the Final Roadmap
    tuned_bench = state.bench_raw.copy()
    tuned_bench["Score Gap %"] = ((tuned_score - tuned_bench["Total Benchmark Score"]) / tuned_bench["Total Benchmark Score"]) * 100

    for country in state.countries:
        elements.append(Paragraph(f"Strategy for {country}", styles['Heading2']))
        c_df = tuned_bench[tuned_bench["Country"] == country] if "Country" in tuned_bench.columns else tuned_bench
        
        buckets = [
            ("Safe (Match)", c_df[c_df["Score Gap %"] >= -3], colors.darkgreen),
            ("Target (Growth)", c_df[(c_df["Score Gap %"] < -3) & (c_df["Score Gap %"] >= -15)], colors.orange),
            ("Dream (Reach)", c_df[c_df["Score Gap %"] < -15], colors.red)
        ]

        for title, df_cat, color in buckets:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            if not df_cat.empty:
                data = [["University", "Bench Score", "Match Gap"]]
                for _, r in df_cat.sort_values("Score Gap %", ascending=False).head(5).iterrows():
                    data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Score Gap %'], 1)}%"])
                t = Table(data, colWidths=[300, 80, 70])
                t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
                elements.append(t)
            else:
                elements.append(Paragraph("No current matches found.", styles['Italic']))
            elements.append(Spacer(1, 10))
        elements.append(Spacer(1, 10))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. APP INTERFACE
# ─────────────────────────────────────────────
apply_styles()
q_xls, q_map, b_xls, b_map = load_resources()

if 'page' not in st.session_state: st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        country_list = ["USA", "UK", "Canada", "Singapore", "Australia", "Europe"]
        pref_countries = st.multiselect("Preferred Target Countries (Select 3)", country_list, max_selections=3)
        course = st.selectbox("Interested Major", list(q_map.keys()))
        if st.button("Start Analysis"):
            if name and pref_countries:
                st.session_state.update({"name": name, "course": course, "countries": pref_countries, "page": 'assessment'})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'assessment':
    col_left, col_right = st.columns([0.6, 0.4])
    q_df = q_xls.parse(q_map[st.session_state.course])
    
    with col_left:
        st.header(f"Phase 1: Current Profile Assessment")
        current_score = 0
        current_responses = []
        for idx, row in q_df.iterrows():
            st.markdown(f"**{row['question_text']}**")
            opts = ["None"]
            v_map = {"None": 0}
            for c in 'ABCDE':
                if pd.notna(row.get(f'option_{c}')):
                    label = f"{c}) {str(row[f'option_{c}']).strip()}"
                    opts.append(label); v_map[label] = row[f'score_{c}']
            sel = st.selectbox("Current Status", opts, key=f"q{idx}")
            current_score += v_map[sel]
            current_responses.append((row['question_text'], sel, v_map[sel], row['question_id']))
        
        if st.button("Finalize & Proceed to Tuning"):
            bench_raw = b_xls.parse(b_map[st.session_state.course])
            st.session_state.update({"current_total": current_score, "current_responses": current_responses, "bench_raw": bench_raw, "page": 'tuner'})
            st.rerun()

    with col_right:
        st.markdown(f"<div class='score-box'><h3>Current Score</h3><h1>{round(current_score, 1)}</h1></div>", unsafe_allow_html=True)
        
        st.info("The Live Score above represents your current readiness based on US, UK, and Singapore admission benchmarks.")

elif st.session_state.page == 'tuner':
    st.title("🔧 Phase 2: Strategic Growth & 9-List Strategy")
    st.markdown("##### Compare your **Current Profile** against your **Planned Improvements** and view the impact on your university lists.")
    
    col_tune, col_res = st.columns([0.5, 0.5])
    q_df = q_xls.parse(q_map[st.session_state.course])
    
    with col_tune:
        st.subheader("Counsellor Tuning")
        tuned_score = 0
        for i, (q_text, orig_sel, orig_val, q_id) in enumerate(st.session_state.current_responses):
            row = q_df[q_df['question_id'] == q_id].iloc[0]
            opts = ["None"]
            v_map = {"None": 0}
            for c in 'ABCDE':
                if pd.notna(row.get(f'option_{c}')):
                    label = f"{c}) {str(row[f'option_{c}']).strip()}"
                    opts.append(label); v_map[label] = row[f'score_{c}']
            
            tuned_sel = st.selectbox(f"Plan: {q_text}", opts, index=opts.index(orig_sel), key=f"t{q_id}")
            tuned_score += v_map[tuned_sel]

    with col_res:
        st.markdown(f"<div class='score-box' style='background-color:#fff;'><h4>Planned Improvement Score</h4><h1 style='color:#28a745;'>{round(tuned_score, 1)}</h1><p>Original: {round(st.session_state.current_total, 1)}</p></div>", unsafe_allow_html=True)
        
        st.subheader("Live 9-List Strategy")
        t_bench = st.session_state.bench_raw.copy()
        t_bench["Score Gap %"] = ((tuned_score - t_bench["Total Benchmark Score"]) / t_bench["Total Benchmark Score"]) * 100

        for country in st.session_state.countries:
            with st.expander(f"📍 {country} Curation", expanded=True):
                c_df = t_bench[t_bench["Country"] == country] if "Country" in t_bench.columns else t_bench
                
                s_list = c_df[c_df["Score Gap %"] >= -3].head(3)
                t_list = c_df[(c_df["Score Gap %"] < -3) & (c_df["Score Gap %"] >= -15)].head(3)
                d_list = c_df[c_df["Score Gap %"] < -15].head(3)

                if not s_list.empty:
                    st.markdown("**🟢 Safe**")
                    for _, r in s_list.iterrows(): st.markdown(f"<div class='uni-card' style='background-color:#28a745;'>{r['University']}</div>", unsafe_allow_html=True)
                if not t_list.empty:
                    st.markdown("**🟡 Target**")
                    for _, r in t_list.iterrows(): st.markdown(f"<div class='uni-card' style='background-color:#ff922b;'>{r['University']}</div>", unsafe_allow_html=True)
                if not d_list.empty:
                    st.markdown("**🔴 Dream**")
                    for _, r in d_list.iterrows(): st.markdown(f"<div class='uni-card' style='background-color:#dc3545;'>{r['University']}</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("📥 Authorization & Download")
    c_name = st.text_input("Counsellor Name")
    c_code = st.text_input("Access Code", type="password")
    if st.button("Generate Strategy Report"):
        if c_code == "304" and c_name:
            pdf = generate_comparison_pdf(st.session_state, tuned_score, c_name)
            st.success("Analysis Authorized.")
            st.download_button("Download Strategy PDF", data=pdf, file_name=f"{st.session_state.name}_Report.pdf")
        else: st.error("Invalid Code.")
