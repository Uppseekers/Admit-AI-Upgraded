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
st.set_page_config(page_title="Uppseekers Admit AI", page_icon="Uppseekers Logo.png", layout="centered")

def apply_styles():
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #004aad; color: white; font-weight: bold; border: none; }
        .card { background-color: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #f0f0f0; margin-bottom: 25px; }
        .score-box { background-color: #e8f0fe; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #004aad; margin-top: 20px; margin-bottom: 20px; }
        h1, h2, h3 { color: #004aad; }
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA LOADING (USING CACHE RESOURCE)
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
        st.error(f"Error loading system files: {e}")
        st.stop()

# ─────────────────────────────────────────────
# 3. STRATEGIC 9-LIST PDF GENERATOR
# ─────────────────────────────────────────────
def generate_strategic_report(state, counsellor_name):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    # Robust Logo Handling
    logo_path = "Uppseekers Logo.png"
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=140, height=42)
            logo.hAlign = 'LEFT'
            elements.append(logo)
            elements.append(Spacer(1, 15))
        except: pass

    elements.append(Paragraph(f"Admit AI Strategic Report: {state.name}", styles['Title']))
    elements.append(Paragraph(f"<b>Target Program:</b> {state.course} | <b>Profile Score:</b> {round(state.total_score, 1)}", styles['Normal']))
    elements.append(Paragraph(f"<b>Consultant:</b> {counsellor_name}", styles['Normal']))
    elements.append(Spacer(1, 25))

    # SECTION: Strategic Lists (3 Countries x 3 Categories)
    for country in state.countries:
        elements.append(Paragraph(f"Regional Strategy: {country}", styles['Heading2']))
        
        # Filter for Country
        c_df = state.bench_df[state.bench_df["Country"] == country] if "Country" in state.bench_df.columns else state.bench_df
        
        # Probability Buckets
        safe = c_df[c_df["Score Gap %"] >= -3]
        target = c_df[(c_df["Score Gap %"] < -3) & (c_df["Score Gap %"] >= -15)]
        dream = c_df[c_df["Score Gap %"] < -15]

        def add_bucket(df, title, color):
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            if not df.empty:
                data = [["University", "Score Req.", "Match Gap"]]
                for _, row in df.sort_values("Score Gap %", ascending=False).head(5).iterrows():
                    data.append([row["University"], str(round(row["Total Benchmark Score"], 1)), f"{round(row['Score Gap %'], 1)}%"])
                t = Table(data, colWidths=[300, 80, 70])
                t.setStyle(TableStyle([
                    ('BACKGROUND',(0,0),(-1,0), color),
                    ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke),
                    ('GRID',(0,0),(-1,-1),0.5,colors.black)
                ]))
                elements.append(t)
            else:
                elements.append(Paragraph("<i>No specific matches found in this category for this region.</i>", styles['Italic']))
            elements.append(Spacer(1, 12))

        add_bucket(safe, f"Safe Options - {country}", colors.darkgreen)
        add_bucket(target, f"Target Options - {country}", colors.orange)
        add_bucket(dream, f"Dream Options - {country}", colors.red)
        elements.append(Spacer(1, 15))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. STREAMLIT APP FLOW
# ─────────────────────────────────────────────
apply_styles()
q_xls, q_map, b_xls, b_map = load_resources()

if 'page' not in st.session_state: st.session_state.page = 'intro'

# PAGE 1: START
if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Full Student Name")
        country_list = ["USA", "UK", "Canada", "Singapore", "Australia", "Europe"]
        pref_countries = st.multiselect("Preferred Target Countries (Select 3)", country_list, max_selections=3)
        course = st.selectbox("Intended Major", list(q_map.keys()))
        if st.button("Start Profile Analysis"):
            if name and pref_countries:
                st.session_state.update({"name": name, "course": course, "countries": pref_countries, "page": 'questions'})
                st.rerun()
            else: st.warning("Please fill in name and select 3 countries.")
        st.markdown('</div>', unsafe_allow_html=True)

# PAGE 2: LIVE ASSESSMENT
elif st.session_state.page == 'questions':
    q_df = q_xls.parse(q_map[st.session_state.course])
    live_score = 0
    responses = []
    
    st.markdown(f"### Assessment: **{st.session_state.course}**")
    
    for idx, row in q_df.iterrows():
        st.markdown(f"**Q{int(row['question_id'])}. {row['question_text']}**")
        opts = ["None / No Participation"]
        v_map = {"None / No Participation": 0}
        for c in 'ABCDE':
            text = row.get(f'option_{c}')
            if pd.notna(text):
                label = f"{c}) {str(text).strip()}"
                opts.append(label); v_map[label] = row[f'score_{c}']
        
        sel = st.selectbox("Current Status", opts, key=f"q{idx}")
        current_val = v_map[sel]
        live_score += current_val
        responses.append((row['question_text'], sel, current_val))
        st.divider()

    # REAL-TIME SCORE DISPLAY
    st.markdown(f"""<div class='score-box'><h2>Current Profile Score: {round(live_score, 1)}</h2></div>""", unsafe_allow_html=True)

    if st.button("Analyze & Finalize"):
        bench = b_xls.parse(b_map[st.session_state.course])
        # Calculate Gap %
        bench["Score Gap %"] = ((live_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
        
        # Prepare for Report
        top3 = bench.sort_values("Total Benchmark Score", ascending=False).head(3)
        q_bench = {f"Q{i}": top3[f"Q{i}"].mean() for i in range(1, 11) if f"Q{i}" in bench.columns}
        
        st.session_state.update({"total_score": live_score, "responses": responses, "bench_df": bench, "q_bench": q_bench, "page": 'unlock'})
        st.rerun()

# PAGE 3: AUTHORIZATION
elif st.session_state.page == 'unlock':
    st.title("🛡️ Authorization")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c_name = st.text_input("Consultant Name")
        c_code = st.text_input("Security PIN", type="password")
        if st.button("Generate 9-List Strategy Report"):
            if c_code == "304" and c_name:
                pdf = generate_strategic_report(st.session_state, c_name)
                st.success("Strategy Report Unlocked!")
                st.download_button("📥 Download PDF Report", data=pdf, file_name=f"{st.session_state.name}_Report.pdf", mime="application/pdf")
            else: st.error("Access Denied: Invalid Authorization.")
        st.markdown('</div>', unsafe_allow_html=True)
