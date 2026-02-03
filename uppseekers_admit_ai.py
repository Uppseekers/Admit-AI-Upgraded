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
        .delta-plus { color: #28a745; font-weight: bold; font-size: 1.2em; }
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
    elements.append(Paragraph(f"<b>Current Profile Score:</b> {round(state.current_total, 1)}", styles['Normal']))
    elements.append(Paragraph(f"<b>Planned Strategic Score:</b> {round(tuned_score, 1)}", styles['Normal']))
    elements.append(Paragraph(f"<b>Counsellor:</b> {counsellor_name}", styles['Normal']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Strategic Impact Analysis", styles['Heading2']))
    elements.append(Paragraph(f"The proposed strategic adjustments lead to a score increase of {round(tuned_score - state.current_total, 1)} points. This shift reclassifies several 'Dream' universities into 'Target' or 'Safe' categories.", styles['Normal']))
    elements.append(Spacer(1, 15))

    # Using Tuned Score for the Final Roadmap
    tuned_bench = state.bench_raw.copy()
    tuned_bench["Score Gap %"] = ((tuned_score - tuned_bench["Total Benchmark Score"]) / tuned_bench["Total Benchmark Score"]) * 100

    for country in state.countries:
        elements.append(Paragraph(f"Regional Strategy: {country}", styles['Heading2']))
        c_df = tuned_bench[tuned_bench["Country"] == country] if "Country" in tuned_bench.columns else tuned_bench
        
        for title, df_cat, color in [("Safe", c_df[c_df["Score Gap %"] >= -3], colors.darkgreen), 
                                     ("Target", c_df[(c_df["Score Gap %"] < -3) & (c_df["Score Gap %"] >= -15)], colors.orange), 
                                     ("Dream", c_df[c_df["Score Gap %"] < -15], colors.red)]:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            if not df_cat.empty:
                data = [["University", "Score Req.", "Gap After Tuning"]]
                for _, r in df_cat.sort_values("Score Gap %", ascending=False).head(5).iterrows():
                    data.append([r["University"], str(round(r["Total Benchmark Score"], 1)), f"{round(r['Score Gap %'], 1)}%"])
                t = Table(data, colWidths=[300, 80, 70])
                t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
                elements.append(t)
            else: elements.append(Paragraph("No current matches.", styles['Italic']))
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
        pref_countries = st.multiselect("Select Target Countries (Select 3)", country_list, max_selections=3)
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
        st.header(f"Assessment: {st.session_state.course}")
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
            sel = st.selectbox("Current Level", opts, key=f"q{idx}")
            current_score += v_map[sel]
            current_responses.append((row['question_text'], sel, v_map[sel], row['question_id']))
        
        if st.button("Finalize & Compare Profiles"):
            bench_raw = b_xls.parse(b_map[st.session_state.course])
            st.session_state.update({"current_total": current_score, "current_responses": current_responses, "bench_raw": bench_raw, "page": 'tuner'})
            st.rerun()

    with col_right:
        st.markdown(f"<div class='score-box'><h3>Current Score</h3><h1>{round(current_score, 1)}</h1></div>", unsafe_allow_html=True)
        
        st.info("The profile is measured against Global Benchmark Standards across 10 critical domains.")

elif st.session_state.page == 'tuner':
    st.title("⚖️ Comparative Profile Tuner")
    st.markdown("##### Side-by-side comparison of the **Current Profile** vs. the **Counsellor’s Strategic Plan**.")
    
    col_tune, col_comp = st.columns([0.5, 0.5])
    q_df = q_xls.parse(q_map[st.session_state.course])
    
    with col_tune:
        st.subheader("🛠️ Strategic Tuning")
        tuned_score = 0
        tuned_data = []
        for i, (q_text, orig_sel, orig_val, q_id) in enumerate(st.session_state.current_responses):
            row = q_df[q_df['question_id'] == q_id].iloc[0]
            opts = ["None"]
            v_map = {"None": 0}
            for c in 'ABCDE':
                if pd.notna(row.get(f'option_{c}')):
                    label = f"{c}) {str(row[f'option_{c}']).strip()}"
                    opts.append(label); v_map[label] = row[f'score_{c}']
            
            # Tuner UI
            st.markdown(f"**{q_text}**")
            st.caption(f"Current: {orig_sel}")
            tuned_sel = st.selectbox(f"Plan Improvement", opts, index=opts.index(orig_sel), key=f"t{q_id}")
            tuned_score += v_map[tuned_sel]
            tuned_data.append((q_text, tuned_sel, v_map[tuned_sel]))

    with col_comp:
        st.subheader("📈 Impact Dashboard")
        diff = tuned_score - st.session_state.current_total
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Current", round(st.session_state.current_total, 1))
        c2.metric("Planned", round(tuned_score, 1))
        c3.metric("Improvement", f"+{round(diff, 1)}", delta_color="normal")

        st.divider()
        
        # Calculate Both Benchmarks for Comparison
        curr_bench = st.session_state.bench_raw.copy()
        curr_bench["Gap %"] = ((st.session_state.current_total - curr_bench["Total Benchmark Score"]) / curr_bench["Total Benchmark Score"]) * 100
        
        plan_bench = st.session_state.bench_raw.copy()
        plan_bench["Gap %"] = ((tuned_score - plan_bench["Total Benchmark Score"]) / plan_bench["Total Benchmark Score"]) * 100

        for country in st.session_state.countries:
            st.markdown(f"#### 📍 {country} Strategy")
            cb = curr_bench[curr_bench["Country"] == country] if "Country" in curr_bench.columns else curr_bench
            pb = plan_bench[plan_bench["Country"] == country] if "Country" in plan_bench.columns else plan_bench
            
            # Compare Counts
            s_curr, s_plan = len(cb[cb["Gap %"] >= -3]), len(pb[pb["Gap %"] >= -3])
            t_curr, t_plan = len(cb[(cb["Gap %"] < -3) & (cb["Gap %"] >= -15)]), len(pb[(pb["Gap %"] < -3) & (pb["Gap %"] >= -15)])
            
            sc1, sc2 = st.columns(2)
            sc1.write(f"**Safe Universities:** {s_curr} → **{s_plan}**")
            sc2.write(f"**Target Universities:** {t_curr} → **{t_plan}**")
            
            # Show specific list of newly unlocked colleges
            new_unis = pb[(pb["Gap %"] >= -3) & (~pb["University"].isin(cb[cb["Gap %"] >= -3]["University"]))]["University"].tolist()
            if new_unis:
                st.success(f"Unlocked Safe: {', '.join(new_unis[:3])}...")
            st.divider()

    st.subheader("📥 Secure Authorization")
    c_name = st.text_input("Counsellor Name")
    c_code = st.text_input("Access Code", type="password")
    if st.button("Generate & Download Comparison PDF"):
        if c_code == "304" and c_name:
            pdf = generate_comparison_pdf(st.session_state, tuned_score, c_name)
            st.download_button("Download Comparative Report", data=pdf, file_name=f"{st.session_state.name}_Comparison.pdf")
        else: st.error("Invalid Code.")
