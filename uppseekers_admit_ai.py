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
        .comparison-label { font-size: 0.9em; color: #666; margin-bottom: 2px; }
        .comparison-val { font-size: 1.8em; font-weight: bold; color: #004aad; }
        .uni-card { padding: 10px; border-radius: 8px; margin-bottom: 5px; color: white; font-weight: bold; font-size: 0.85em; }
        h1, h2, h3 { color: #004aad; }
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA LOADING (REFINED FOR FLEXIBILITY)
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
        st.error(f"System Error: Required data files missing or incorrect format. {e}")
        st.stop()

# ─────────────────────────────────────────────
# 3. PDF GENERATOR (COMPARATIVE REPORT)
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

    elements.append(Paragraph(f"Strategic Comparison Report: {state.name}", styles['Title']))
    elements.append(Paragraph(f"<b>Current Score:</b> {round(state.current_total, 1)} | <b>Planned Strategic Score:</b> {round(tuned_score, 1)}", styles['Normal']))
    elements.append(Paragraph(f"<b>Counsellor:</b> {counsellor_name}", styles['Normal']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Strategic University Roadmap", styles['Heading2']))
    
    tuned_bench = state.bench_raw.copy()
    tuned_bench["Gap %"] = ((tuned_score - tuned_bench["Total Benchmark Score"]) / tuned_bench["Total Benchmark Score"]) * 100

    for country in state.countries:
        elements.append(Paragraph(f"Country Focus: {country}", styles['Heading3']))
        c_df = tuned_bench[tuned_bench["Country"].str.contains(country, case=False, na=False)] if "Country" in tuned_bench.columns else tuned_bench
        
        buckets = [
            ("Safe (Match)", c_df[c_df["Gap %"] >= -3], colors.darkgreen),
            ("Target (Growth)", c_df[(c_df["Gap %"] < -3) & (c_df["Gap %"] >= -15)], colors.orange),
            ("Dream (Aspirational)", c_df[c_df["Gap %"] < -15], colors.red)
        ]

        for title, df_cat, color in buckets:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            if not df_cat.empty:
                data = [["University", "Target Score", "Gap %"]]
                for _, r in df_cat.sort_values("Gap %", ascending=False).head(5).iterrows():
                    data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Gap %'], 1)}%"])
                t = Table(data, colWidths=[300, 80, 70])
                t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
                elements.append(t)
            else:
                elements.append(Paragraph("No current matches in this category.", styles['Italic']))
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
        country_list = ["USA", "UK", "Canada", "Singapore", "Australia", "Germany"]
        pref_countries = st.multiselect("Select 3 Target Countries", country_list, max_selections=3)
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
        responses = []
        for idx, row in q_df.iterrows():
            st.markdown(f"**Q{int(row['question_id'])}. {row['question_text']}**")
            opts = ["None"]
            v_map = {"None": 0}
            for c in 'ABCDE':
                text = row.get(f'option_{c}')
                if pd.notna(text):
                    label = f"{c}) {str(text).strip()}"
                    opts.append(label); v_map[label] = row[f'score_{c}']
            sel = st.selectbox("Current Status", opts, key=f"q{idx}")
            current_score += v_map[sel]
            responses.append((row['question_text'], sel, v_map[sel], row['question_id']))
        
        st.divider()
        if st.button("Finalize & Compare with Strategic Plan"):
            bench_raw = b_xls.parse(b_map[st.session_state.course])
            st.session_state.update({"current_total": current_score, "current_responses": responses, "bench_raw": bench_raw, "page": 'tuner'})
            st.rerun()

    with col_right:
        st.markdown(f"<div class='score-box'><h3>Live Profile Score</h3><h1>{round(current_score, 1)}</h1></div>", unsafe_allow_html=True)
        
        st.info("Your score updates in real-time. Universities evaluate you across 10 critical pillars of admission.")

elif st.session_state.page == 'tuner':
    st.title("⚖️ Strategic Comparison Dashboard")
    col_tune, col_stats = st.columns([0.5, 0.5])
    q_df = q_xls.parse(q_map[st.session_state.course])
    
    with col_tune:
        st.subheader("🛠️ Counsellor Tuning")
        tuned_score = 0
        for i, (q_text, orig_sel, orig_val, q_id) in enumerate(st.session_state.current_responses):
            row = q_df[q_df['question_id'] == q_id].iloc[0]
            opts = ["None"]
            v_map = {"None": 0}
            for c in 'ABCDE':
                text = row.get(f'option_{c}')
                if pd.notna(text):
                    label = f"{c}) {str(text).strip()}"
                    opts.append(label); v_map[label] = row[f'score_{c}']
            
            st.markdown(f"**{q_text}**")
            st.caption(f"Original: {orig_sel}")
            tuned_sel = st.selectbox(f"Strategic Plan", opts, index=opts.index(orig_sel), key=f"t{q_id}")
            tuned_score += v_map[tuned_sel]

    with col_stats:
        st.subheader("📈 Numerical Impact Analysis")
        m1, m2 = st.columns(2)
        m1.metric("Current Score", round(st.session_state.current_total, 1))
        m2.metric("Strategic Score", round(tuned_score, 1), delta=f"+{round(tuned_score - st.session_state.current_total, 1)}")

        curr_b = st.session_state.bench_raw.copy()
        curr_b["Gap %"] = ((st.session_state.current_total - curr_b["Total Benchmark Score"]) / curr_b["Total Benchmark Score"]) * 100
        plan_b = st.session_state.bench_raw.copy()
        plan_b["Gap %"] = ((tuned_score - plan_b["Total Benchmark Score"]) / plan_b["Total Benchmark Score"]) * 100

        for country in st.session_state.countries:
            st.markdown(f"#### 🚩 {country} University Counts")
            cb = curr_b[curr_b["Country"].str.contains(country, case=False, na=False)] if "Country" in curr_b.columns else curr_b
            pb = plan_b[plan_b["Country"].str.contains(country, case=False, na=False)] if "Country" in plan_b.columns else plan_b
            
            s_c, s_p = len(cb[cb["Gap %"] >= -3]), len(pb[pb["Gap %"] >= -3])
            t_c, t_p = len(cb[(cb["Gap %"] < -3) & (cb["Gap %"] >= -15)]), len(pb[(pb["Gap %"] < -3) & (pb["Gap %"] >= -15)])
            d_c, d_p = len(cb[cb["Gap %"] < -15]), len(pb[pb["Gap %"] < -15])

            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f"<p class='comparison-label'>Safe</p><p class='comparison-val'>{s_c} → {s_p}</p>", unsafe_allow_html=True)
            with c2: st.markdown(f"<p class='comparison-label'>Target</p><p class='comparison-val'>{t_c} → {t_p}</p>", unsafe_allow_html=True)
            with c3: st.markdown(f"<p class='comparison-label'>Dream</p><p class='comparison-val'>{d_c} → {d_p}</p>", unsafe_allow_html=True)
            st.divider()

    st.subheader("📥 Secure Authorization")
    c_name = st.text_input("Counsellor Name")
    c_code = st.text_input("Access Pin", type="password")
    if st.button("Generate Strategy Comparison PDF"):
        if c_code == "304":
            pdf = generate_comparison_pdf(st.session_state, tuned_score, c_name)
            st.download_button("Download Report", data=pdf, file_name=f"{st.session_state.name}_Report.pdf")
        else: st.error("Invalid Code.")
