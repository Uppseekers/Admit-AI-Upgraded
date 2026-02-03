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
        .score-box { background-color: #e8f0fe; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #004aad; margin-top: 10px; }
        .tuner-card { background-color: #fff4e6; padding: 20px; border-radius: 12px; border-left: 5px solid #ff922b; margin-top: 20px; }
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
        st.error(f"Error loading system files: {e}")
        st.stop()

# ─────────────────────────────────────────────
# 3. PDF GENERATOR (9-LIST STRATEGY)
# ─────────────────────────────────────────────
def generate_strategic_report(state, counsellor_name):
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

    elements.append(Paragraph(f"Admit AI Strategic Report: {state.name}", styles['Title']))
    elements.append(Paragraph(f"<b>Course:</b> {state.course} | <b>Total Score:</b> {round(state.total_score, 1)}", styles['Normal']))
    elements.append(Paragraph(f"<b>Counsellor:</b> {counsellor_name}", styles['Normal']))
    elements.append(Spacer(1, 20))

    for country in state.countries:
        elements.append(Paragraph(f"Strategic Curation for {country}", styles['Heading2']))
        c_df = state.bench_df[state.bench_df["Country"] == country] if "Country" in state.bench_df.columns else state.bench_df
        
        safe = c_df[c_df["Score Gap %"] >= -3]
        target = c_df[(c_df["Score Gap %"] < -3) & (c_df["Score Gap %"] >= -15)]
        dream = c_df[c_df["Score Gap %"] < -15]

        def add_list(df, title, color):
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            if not df.empty:
                data = [["University", "Target Score", "Gap %"]]
                for _, row in df.sort_values("Score Gap %", ascending=False).head(5).iterrows():
                    data.append([row["University"], str(round(row["Total Benchmark Score"], 1)), f"{round(row['Score Gap %'], 1)}%"])
                t = Table(data, colWidths=[300, 80, 70])
                t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
                elements.append(t)
            else:
                elements.append(Paragraph("<i>No current matches in this category.</i>", styles['Italic']))
            elements.append(Spacer(1, 12))

        add_list(safe, f"Safe Options - {country}", colors.darkgreen)
        add_list(target, f"Target Options - {country}", colors.orange)
        add_list(dream, f"Dream Options - {country}", colors.red)
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

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        country_list = ["USA", "UK", "Canada", "Singapore", "Australia", "Europe"]
        pref_countries = st.multiselect("Preferred Countries (Max 3)", country_list, max_selections=3)
        course = st.selectbox("Interested Course", list(q_map.keys()))
        if st.button("Start Analysis"):
            if name and pref_countries:
                st.session_state.update({"name": name, "course": course, "countries": pref_countries, "page": 'questions'})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'questions':
    q_df = q_xls.parse(q_map[st.session_state.course])
    live_score = 0
    responses = []
    
    st.markdown(f"### Assessment: **{st.session_state.course}**")
    
    for idx, row in q_df.iterrows():
        st.markdown(f"**Q{int(row['question_id'])}. {row['question_text']}**")
        opts = ["None"]
        v_map = {"None": 0}
        for c in 'ABCDE':
            text = row.get(f'option_{c}')
            if pd.notna(text):
                label = f"{c}) {str(text).strip()}"
                opts.append(label); v_map[label] = row[f'score_{c}']
        
        sel = st.selectbox("Answer", opts, key=f"q{idx}")
        current_val = v_map[sel]
        live_score += current_val
        responses.append((row['question_text'], sel, current_val, row['question_id']))
        st.divider()

    st.markdown(f"""<div class='score-box'><h3>Live Profile Score: {round(live_score, 1)}</h3></div>""", unsafe_allow_html=True)

    if st.button("Submit & Proceed to Detailed Report"):
        bench = b_xls.parse(b_map[st.session_state.course])
        st.session_state.update({"total_score": live_score, "responses": responses, "bench_df_raw": bench, "page": 'detailed_report'})
        st.rerun()

elif st.session_state.page == 'detailed_report':
    st.title("📊 Detailed Profile Analysis & Tuner")
    
    # --- PAGE 3: TUNER (Real-Time Improvement Simulator) ---
    st.markdown("### 🔧 Strategic Growth Tuner")
    st.info("Change options below to see how the student's eligibility improves in real-time.")
    
    tuner_score = 0
    tuned_responses = []
    q_df = q_xls.parse(q_map[st.session_state.course])

    with st.expander("Adjust Profile Parameters", expanded=True):
        for i, (q_text, orig_sel, orig_val, q_id) in enumerate(st.session_state.responses):
            # Find the original row for options
            row = q_df[q_df['question_id'] == q_id].iloc[0]
            opts = ["None"]
            v_map = {"None": 0}
            for c in 'ABCDE':
                text = row.get(f'option_{c}')
                if pd.notna(text):
                    label = f"{c}) {str(text).strip()}"
                    opts.append(label); v_map[label] = row[f'score_{c}']
            
            # Pre-select the original answer
            new_sel = st.selectbox(f"Tune: {q_text}", opts, index=opts.index(orig_sel), key=f"tuner_{q_id}")
            tuner_score += v_map[new_sel]
            tuned_responses.append((q_text, new_sel, v_map[new_sel]))

    # Calculate Tuned Benchmarks
    tuned_bench = st.session_state.bench_df_raw.copy()
    tuned_bench["Score Gap %"] = ((tuner_score - tuned_bench["Total Benchmark Score"]) / tuned_bench["Total Benchmark Score"]) * 100
    
    # Display Tuned Results
    st.markdown(f"""<div class='score-box' style='background-color: #fff4e6; border-color: #ff922b;'>
                <h3>Tuned Profile Score: {round(tuner_score, 1)}</h3>
                <p>(Original Score: {round(st.session_state.total_score, 1)})</p></div>""", unsafe_allow_html=True)

    # Real-time Curation View
    st.subheader("Simulated Eligibility")
    cols = st.columns(len(st.session_state.countries))
    for i, country in enumerate(st.session_state.countries):
        with cols[i]:
            st.markdown(f"**{country} Matches**")
            c_df = tuned_bench[tuned_bench["Country"] == country] if "Country" in tuned_bench.columns else tuned_bench
            safe_count = len(c_df[c_df["Score Gap %"] >= -3])
            target_count = len(c_df[(c_df["Score Gap %"] < -3) & (c_df["Score Gap %"] >= -15)])
            st.metric("Safe Unis", safe_count)
            st.metric("Target Unis", target_count)

    st.divider()
    
    # --- PAGE 4: AUTHORIZATION ---
    st.subheader("🛡️ Final Authorization")
    c_name = st.text_input("Counsellor Name")
    c_code = st.text_input("Access Pin (304)", type="password")
    
    if st.button("Generate Strategy Report"):
        if c_code == "304" and c_name:
            # We use the ORIGINAL score for the official report, 
            # but you can swap 'total_score' for 'tuner_score' if you want the tuned version.
            final_state = st.session_state
            final_state.bench_df = tuned_bench # Using tuned bench for report
            final_state.total_score = tuner_score
            
            pdf = generate_strategic_report(final_state, c_name)
            st.download_button("📥 Get Official PDF Report", data=pdf, file_name=f"{st.session_state.name}_Report.pdf")
        else:
            st.error("Invalid Pin.")
