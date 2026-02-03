import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# STYLING & UI
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", layout="centered")

def apply_styles():
    st.markdown("""
        <style>
        .main { background-color: #fcfcfc; }
        .stButton>button { background-color: #004aad; color: white; border-radius: 8px; font-weight: bold; }
        .card { background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PDF ENGINE (Generates 9 curated lists)
# ─────────────────────────────────────────────
def generate_curated_pdf(name, course, score, responses, bench_df, countries, counsellor):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Report Header
    elements.append(Paragraph(f"Global Admit AI Analysis: {name}", styles['Title']))
    elements.append(Paragraph(f"Target Program: {course} | Profile Score: {round(score, 1)}", styles['Normal']))
    elements.append(Paragraph(f"Consultant: {counsellor}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Curation Logic: 3 Countries x 3 Categories = 9 Lists
    for country in countries:
        elements.append(Paragraph(f"Strategic List: {country}", styles['Heading2']))
        
        # Filter data for specific country
        c_df = bench_df[bench_df["Country"] == country] if "Country" in bench_df.columns else bench_df
        
        # Gap-based bucketing
        # Safe: Match or slight gap
        # Target: 5-15% gap
        # Dream: 15%+ gap
        buckets = [
            ("🟢 Safe (Match)", c_df[c_df["Score Gap %"] >= -3], colors.darkgreen),
            ("🟡 Target (Competitive)", c_df[(c_df["Score Gap %"] < -3) & (c_df["Score Gap %"] >= -15)], colors.orange),
            ("🔴 Dream (Aspirational)", c_df[c_df["Score Gap %"] < -15], colors.red)
        ]

        for title, df_bucket, color in buckets:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            if not df_bucket.empty:
                data = [["University", "Score Req.", "Your Gap"]]
                for _, row in df_bucket.sort_values("Score Gap %", ascending=False).head(5).iterrows():
                    data.append([row["University"], str(round(row["Total Benchmark Score"], 1)), f"{round(row['Score Gap %'], 1)}%"])
                
                t = Table(data, colWidths=[280, 80, 80])
                t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
                elements.append(t)
            else:
                elements.append(Paragraph("No current matches in this category for this region.", styles['Italic']))
            elements.append(Spacer(1, 15))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# MAIN APP INTERFACE
# ─────────────────────────────────────────────
apply_styles()
if 'page' not in st.session_state: st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("Uppseekers Admit AI")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Full Student Name")
        countries = st.multiselect("Select Target Countries (Select 3)", ["USA", "UK", "Canada", "Singapore", "Australia", "Europe"], max_selections=3)
        course = st.selectbox("Intended Major", ["CS", "Data Science", "Business", "Finance", "Biology"])
        if st.button("Proceed to Assessment"):
            if name and len(countries) > 0:
                st.session_state.update({"name": name, "countries": countries, "course": course, "page": 'test'})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'test':
    st.header(f"Profile Audit: {st.session_state.course}")
    # (Implementation of 10-question logic goes here, similar to previous steps)
    # Once scores are calculated...
    if st.button("Analyze My Profile"):
        # Logic to calculate score and gap % based on CSV files
        # ...
        st.session_state.page = 'report'
        st.rerun()

elif st.session_state.page == 'report':
    st.title("Report Ready")
    c_name = st.text_input("Enter Counsellor Name to Unlock")
    c_code = st.text_input("Enter Access Pin", type="password")
    
    if st.button("Download 9-List Strategy Report"):
        if c_code == "304":
            # Call PDF Generator
            # ...
            st.success("Report generated.")
