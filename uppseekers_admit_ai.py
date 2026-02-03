import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

# ─────────────────────────────────────────────
# 1. PREMIUM UI/UX STYLING
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", page_icon="Uppseekers Logo.png", layout="centered")

def apply_custom_styles():
    st.markdown("""
        <style>
        .main { background-color: #fcfcfc; }
        .stButton>button { 
            width: 100%; border-radius: 10px; height: 3.5em; 
            background-color: #004aad; color: white; font-weight: bold; border: none;
            transition: 0.3s;
        }
        .stButton>button:hover { background-color: #003580; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .card { 
            background-color: white; padding: 25px; border-radius: 15px; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #f0f0f0; margin-bottom: 25px;
        }
        h1, h2, h3 { color: #004aad; font-family: 'Inter', sans-serif; }
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA ENGINE (FIXED CACHING)
# ─────────────────────────────────────────────
@st.cache_resource  # Changed from cache_data to fix serialization error
def load_resources():
    try:
        # Load Questions Data
        q_xls = pd.ExcelFile("University Readiness_new.xlsx")
        q_idx = q_xls.parse(q_xls.sheet_names[0])
        q_map = dict(zip(q_idx.iloc[:,0], q_idx.iloc[:,1]))
        
        # Load Benchmarking Data
        b_xls = pd.ExcelFile("Benchmarking_USA.xlsx")
        b_idx = b_xls.parse(b_xls.sheet_names[0])
        b_map = dict(zip(b_idx.iloc[:,0], b_idx.iloc[:,1]))
        
        return q_xls, q_map, b_xls, b_map
    except Exception as e:
        st.error(f"System Error: Required data files missing. ({e})")
        st.stop()

# ─────────────────────────────────────────────
# 3. STRATEGIC PDF GENERATOR (9-LIST LOGIC)
# ─────────────────────────────────────────────
def generate_strategic_report(state, counsellor_name):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T', parent=styles['Title'], textColor=colors.HexColor("#004aad"), fontSize=22)
    sec_style = ParagraphStyle('Sec', parent=styles['Heading2'], textColor=colors.HexColor("#333333"), spaceBefore=15)
    
    elements = []

    # Logo
    try:
        logo = Image("Uppseekers Logo.png", width=150, height=45)
        logo.hAlign = 'LEFT'
        elements.append(logo)
        elements.append(Spacer(1, 20))
    except: pass

    elements.append(Paragraph(f"Admit AI Strategic Profile Report", title_style))
    elements.append(Paragraph(f"<b>Student:</b> {state.name} | <b>Class:</b> {state.s_class}", styles['Normal']))
    elements.append(Paragraph(f"<b>Target Course:</b> {state.course} | <b>Counsellor:</b> {counsellor_name}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Profile Summary
    elements.append(Paragraph(f"Overall Profile Strength Score: {round(state.total_score, 1)}", sec_style))
    elements.append(Spacer(1, 15))

    # SECTION 1: Question-wise Gap Analysis
    elements.append(Paragraph("1. Improvement Scope Analysis", styles['Heading3']))
    q_data = [["Assessment Domain", "Score", "Ideal", "Gap Analysis"]]
    for i, (q_text, ans, s) in enumerate(state.responses):
        ideal = state.q_bench.get(f"Q{i+1}", 0)
        gap = round(ideal - s, 1)
        scope = f"+{gap} points needed" if gap > 0 else "Competitive Level ✅"
        q_data.append([Paragraph(q_text, styles['Normal']), str(s), str(round(ideal, 1)), Paragraph(scope, styles['Normal'])])
    
    qt = Table(q_data, colWidths=[200, 50, 50, 140])
    qt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#004aad")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(qt)
    elements.append(PageBreak())

    # SECTION 2: 9-LIST CURATION (3x3 Matrix)
    elements.append(Paragraph("2. Strategic University Curation (9 Lists)", sec_style))
    
    def add_list_table(df, title, color):
        if not df.empty:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            u_data = [["University", "Target Score", "Match Gap"]]
            for _, row in df.sort_values("Score Gap %", ascending=False).head(5).iterrows():
                u_data.append([row["University"], str(round(row["Total Benchmark Score"], 1)), f"{round(row['Score Gap %'], 1)}%"])
            ut = Table(u_data, colWidths=[310, 80, 70])
            ut.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
            elements.append(ut)
            elements.append(Spacer(1, 12))
        else:
            elements.append(Paragraph(f"<i>No data available for {title} in current benchmarks.</i>", styles['Italic']))
            elements.append(Spacer(1, 10))

    for country in state.countries:
        elements.append(Paragraph(f"Target Region: {country}", styles['Heading3']))
        # Filtering logic
        c_df = state.bench_df[state.bench_df["Country"] == country] if "Country" in state.bench_df.columns else state.bench_df
        
        # Continuous Bucket Logic to prevent empty lists
        safe = c_df[c_df["Score Gap %"] >= -2]
        target = c_df[(c_df["Score Gap %"] < -2) & (c_df["Score Gap %"] >= -15)]
        dream = c_df[c_df["Score Gap %"] < -15]

        add_list_table(safe, f"Safe - {country}", colors.darkgreen)
        add_list_table(target, f"Target - {country}", colors.orange)
        add_list_table(dream, f"Dream - {country}", colors.red)
        elements.append(Spacer(1, 10))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. STREAMLIT APP FLOW
# ─────────────────────────────────────────────
apply_custom_styles()
q_xls, q_map, b_xls, b_map = load_resources()

if 'page' not in st.session_state: st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        s_class = st.selectbox("Current Class", ["9", "10", "11", "12"])
        country_list = ["USA", "UK", "Canada", "Singapore", "Australia", "Europe"]
        pref_countries = st.multiselect("Preferred Countries (Max 3)", country_list, max_selections=3)
        course = st.selectbox("Interested Course", list(q_map.keys()))
        if st.button("Start Analysis"):
            if name and pref_countries:
                st.session_state.update({"name": name, "s_class": s_class, "course": course, "countries": pref_countries, "page": 'questions'})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'questions':
    q_df = q_xls.parse(q_map[st.session_state.course])
    total_score, responses = 0, []
    st.markdown(f"### Assessment: **{st.session_state.course}**")
    
    for idx, row in q_df.iterrows():
        st.markdown(f"**Q{int(row['question_id'])}. {row['question_text']}**")
        opts = ["None / Not Applicable"]
        v_map = {"None / Not Applicable": 0}
        for c in 'ABCDE':
            text = row.get(f'option_{c}')
            if pd.notna(text):
                label = f"{c}) {str(text).strip()}"
                opts.append(label); v_map[label] = row[f'score_{c}']
        
        sel = st.selectbox("Select Answer", opts, key=f"q{idx}")
        total_score += v_map[sel]
        responses.append((row['question_text'], sel, v_map[sel]))
        st.divider()

    if st.button("Analyze My Profile"):
        bench = b_xls.parse(b_map[st.session_state.course])
        top3 = bench.sort_values("Total Benchmark Score", ascending=False).head(3)
        q_bench = {f"Q{i}": top3[f"Q{i}"].mean() for i in range(1, 11) if f"Q{i}" in bench.columns}
        bench["Score Gap %"] = ((total_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100
        st.session_state.update({"total_score": total_score, "responses": responses, "bench_df": bench, "q_bench": q_bench, "page": 'unlock'})
        st.rerun()

elif st.session_state.page == 'unlock':
    st.title("🛡️ Authorization")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c_name = st.text_input("Counsellor Name")
        c_code = st.text_input("Access Pin", type="password")
        if st.button("Download 9-List Strategy Report"):
            if c_code == "304":
                pdf = generate_strategic_report(st.session_state, c_name)
                st.download_button("📥 Get PDF Report", data=pdf, file_name=f"{st.session_state.name}_AdmitAI.pdf", mime="application/pdf")
            else: st.error("Invalid Pin.")
        st.markdown('</div>', unsafe_allow_html=True)
