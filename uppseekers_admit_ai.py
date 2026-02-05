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
        .score-box { background-color: #f8f9fa; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6; margin-bottom: 20px; }
        .comparison-label { font-size: 0.9em; font-weight: bold; color: #555; margin-bottom: 5px; }
        .comparison-val { font-size: 1.4em; font-weight: bold; color: #004aad; }
        h1, h2, h3 { color: #004aad; }
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA LOADING (LATEST V3-2 FILES)
# ─────────────────────────────────────────────
@st.cache_data
def load_resources():
    q_file = "University Readiness_new (3).xlsx"
    b_file = "Benchmarking_USA (3) (2).xlsx"
    
    if not os.path.exists(q_file) or not os.path.exists(b_file):
        st.error("System Error: Required data files missing. Please check the repository.")
        st.stop()
        
    try:
        q_xls = pd.ExcelFile(q_file)
        q_idx = q_xls.parse(q_xls.sheet_names[0])
        q_map = {str(k).strip(): str(v).strip() for k, v in zip(q_idx.iloc[:,0], q_idx.iloc[:,1])}
        
        b_xls = pd.ExcelFile(b_file)
        b_idx = b_xls.parse(b_xls.sheet_names[0])
        b_map = {str(k).strip(): str(v).strip() for k, v in zip(b_idx.iloc[:,0], b_idx.iloc[:,1])}
        
        return q_map, b_map
    except Exception as e:
        st.error(f"System Error: Failed to parse mappings. {e}")
        return {}, {}

# ─────────────────────────────────────────────
# 3. PDF GENERATOR (RANKED LISTS)
# ─────────────────────────────────────────────
def generate_comparison_pdf(state, tuned_score, counsellor_name, tuned_bench):
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

    elements.append(Paragraph(f"Admit AI Strategic Comparison: {state.name}", styles['Title']))
    elements.append(Paragraph(f"<b>Current Score:</b> {round(state.current_total, 1)} | <b>Planned Strategic Score:</b> {round(tuned_score, 1)}", styles['Normal']))
    elements.append(Paragraph(f"<b>Counsellor:</b> {counsellor_name}", styles['Normal']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Strategic University Roadmap (Ordered by Proximity)", styles['Heading2']))
    
    for country in state.countries:
        elements.append(Paragraph(f"Regional Focus: {country}", styles['Heading3']))
        c_df = tuned_bench[tuned_bench["Country"].str.strip().str.lower() == country.strip().lower()] if "Country" in tuned_bench.columns else tuned_bench
        
        # CATEGORY RANKING LOGIC
        # Safe to Target: Ranked highest match probability first (Gap % nearest to 0 or positive)
        # Needs Strengthening & Gaps: Ranked nearest to farthest (Gap % nearest to -3 or -15)
        buckets = [
            ("Safe to Target", c_df[c_df["Gap %"] >= -3].sort_values("Gap %", ascending=False), colors.darkgreen),
            ("Needs Strengthening", c_df[(c_df["Gap %"] < -3) & (c_df["Gap %"] >= -15)].sort_values("Gap %", ascending=False), colors.orange),
            ("Significant Gaps", c_df[c_df["Gap %"] < -15].sort_values("Gap %", ascending=False), colors.red)
        ]

        for title, df_cat, color in buckets:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            if not df_cat.empty:
                data = [["University", "Target Score", "Gap %"]]
                for _, r in df_cat.head(8).iterrows():
                    data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Gap %'], 1)}%"])
                t = Table(data, colWidths=[300, 80, 70])
                t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
                elements.append(t)
            else:
                elements.append(Paragraph("No matches currently identified.", styles['Italic']))
            elements.append(Spacer(1, 10))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. APP INTERFACE
# ─────────────────────────────────────────────
apply_styles()
q_map, b_map = load_resources()

if 'page' not in st.session_state: st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        country_list = ["USA", "UK", "Canada", "Singapore", "Australia", "Europe"]
        pref_countries = st.multiselect("Select 3 Target Countries", country_list, max_selections=3)
        course = st.selectbox("Interested Major", list(q_map.keys()))
        if st.button("Start Analysis"):
            if name and pref_countries:
                st.session_state.update({"name": name, "course": course.strip(), "countries": pref_countries, "page": 'assessment'})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'assessment':
    col_left, col_right = st.columns([0.6, 0.4])
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])
    
    with col_left:
        st.header(f"Phase 1: Profile Assessment")
        current_score = 0
        current_responses = []
        for idx, row in q_df.iterrows():
            st.markdown(f"**Q{int(row['question_id'])}. {row['question_text']}**")
            opts = ["None"]
            v_map = {"None": 0}
            for c in 'ABCDE':
                label_text = row.get(f'option_{c}')
                if pd.notna(label_text):
                    label = f"{c}) {str(label_text).strip()}"
                    opts.append(label); v_map[label] = row.get(f'score_{c}', 0)
            sel = st.selectbox("Select Current Level", opts, key=f"q{idx}")
            current_score += v_map[sel]
            current_responses.append((row['question_text'], sel, v_map[sel], row['question_id']))
        
        if st.button("Finalize & View Comparisons"):
            b_sheet = b_map[st.session_state.course]
            if "finance" in b_sheet.lower() and "eco" in b_sheet.lower(): b_sheet = "benchmarking_finance&economic"
            
            bench_raw = pd.read_excel("Benchmarking_USA (3) (2).xlsx", sheet_name=b_sheet)
            st.session_state.update({"current_total": current_score, "current_responses": current_responses, "bench_raw": bench_raw, "page": 'tuner'})
            st.rerun()

    with col_right:
        st.markdown(f"<div class='score-box'><h3>Current Score</h3><h1>{round(current_score, 1)}</h1></div>", unsafe_allow_html=True)
        st.markdown("")
        st.info("Profiles are benchmarked against 10 critical domains of international admission.")

elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Comparison Dashboard")
    col_tune, col_stats = st.columns([0.5, 0.5])
    q_df = pd.read_excel("University Readiness_new (3).xlsx", sheet_name=q_map[st.session_state.course])
    
    with col_tune:
        st.subheader("🛠️ Strategic Tuning")
        tuned_score = 0
        for i, (q_text, orig_sel, orig_val, q_id) in enumerate(st.session_state.current_responses):
            row = q_df[q_df['question_id'] == q_id].iloc[0]
            opts = ["None"]
            v_map = {"None": 0}
            for c in 'ABCDE':
                label_text = row.get(f'option_{c}')
                if pd.notna(label_text):
                    label = f"{c}) {str(label_text).strip()}"
                    opts.append(label); v_map[label] = row.get(f'score_{c}', 0)
            st.markdown(f"**{q_text}**")
            tuned_sel = st.selectbox(f"Improvement Plan", opts, index=opts.index(orig_sel), key=f"t{q_id}")
            tuned_score += v_map[tuned_sel]

    with col_stats:
        st.subheader("📊 Strategic Impact Analysis")
        
        curr_b = st.session_state.bench_raw.copy()
        curr_b["Gap %"] = ((st.session_state.current_total - curr_b["Total Benchmark Score"]) / curr_b["Total Benchmark Score"]) * 100
        plan_b = st.session_state.bench_raw.copy()
        plan_b["Gap %"] = ((tuned_score - plan_b["Total Benchmark Score"]) / plan_b["Total Benchmark Score"]) * 100

        m1, m2 = st.columns(2)
        m1.metric("Current Score", round(st.session_state.current_total, 1))
        m2.metric("Strategic Score", round(tuned_score, 1), delta=f"+{round(tuned_score - st.session_state.current_total, 1)}")

        st.divider()
        
        for country in st.session_state.countries:
            st.markdown(f"#### 🚩 {country} University Counts")
            cb = curr_b[curr_b["Country"].str.strip().str.lower() == country.strip().lower()] if "Country" in curr_b.columns else curr_b
            pb = plan_b[plan_b["Country"].str.strip().str.lower() == country.strip().lower()] if "Country" in plan_b.columns else plan_b
            
            # SIDE-BY-SIDE NUMERICAL COMPARISON
            c1, c2, c3 = st.columns(3)
            with c1: 
                st.markdown(f"<p class='comparison-label'>Safe to Target</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='comparison-val'>{len(cb[cb['Gap %'] >= -3])} → {len(pb[pb['Gap %'] >= -3])}</p>", unsafe_allow_html=True)
            with c2: 
                st.markdown(f"<p class='comparison-label'>Needs Strengthening</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='comparison-val'>{len(cb[(cb['Gap %'] < -3) & (cb['Gap %'] >= -15)])} → {len(pb[(pb['Gap %'] < -3) & (pb['Gap %'] >= -15)])}</p>", unsafe_allow_html=True)
            with c3: 
                st.markdown(f"<p class='comparison-label'>Significant Gaps</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='comparison-val'>{len(cb[cb['Gap %'] < -15])} → {len(pb[pb['Gap %'] < -15])}</p>", unsafe_allow_html=True)
            st.divider()

    st.subheader("📥 Secure Report Authorization")
    c_name = st.text_input("Counsellor Name")
    c_code = st.text_input("Access Pin", type="password")
    if st.button("Download Comparison PDF"):
        if c_code == "304":
            pdf = generate_comparison_pdf(st.session_state, tuned_score, c_name, plan_b)
            st.download_button("Download Comparative Report", data=pdf, file_name=f"{st.session_state.name}_Report.pdf")
