import streamlit as st
import pandas as pd
import os

# ─────────────────────────────────────────────
# 1. APP CONFIG & UI STYLING
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", page_icon="Uppseekers Logo.png", layout="wide")

def apply_styles():
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #004aad; color: white; font-weight: bold; border: none; }
        .card { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #f0f0f0; margin-bottom: 20px; }
        .score-box { background-color: #e8f0fe; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #004aad; position: sticky; top: 50px; z-index: 99; }
        .uni-card { padding: 10px; border-radius: 8px; margin-bottom: 5px; color: white; font-weight: bold; font-size: 0.9em; }
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
# 3. APP FLOW
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
        course = st.selectbox("Interested Course", list(q_map.keys()))
        if st.button("Start Live Analysis"):
            if name and len(pref_countries) > 0:
                st.session_state.update({"name": name, "course": course, "countries": pref_countries, "page": 'live_engine'})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'live_engine':
    col_left, col_right = st.columns([0.6, 0.4])

    with col_left:
        st.header(f"Assessment: {st.session_state.course}")
        q_df = q_xls.parse(q_map[st.session_state.course])
        
        live_score = 0
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
            
            sel = st.selectbox("Choose current status", opts, key=f"q{idx}")
            live_score += v_map[sel]
            responses.append((row['question_text'], sel, v_map[sel]))
        
        st.divider()
        if st.button("Finalize & Save Assessment"):
            st.success("Assessment Saved! You can now review the final strategy below.")

    with col_right:
        st.markdown(f"""<div class='score-box'>
            <p style='margin:0; font-size:1.2em;'>Live Profile Score</p>
            <h1 style='margin:0; font-size:3em;'>{round(live_score, 1)}</h1>
        </div>""", unsafe_allow_html=True)

        st.header("🎯 Live University Curation")
        st.caption("Updated in real-time based on your answers")

        # Load benchmarking data for live filtering
        bench = b_xls.parse(b_map[st.session_state.course])
        bench["Score Gap %"] = ((live_score - bench["Total Benchmark Score"]) / bench["Total Benchmark Score"]) * 100

        for country in st.session_state.countries:
            st.subheader(f"🚩 {country}")
            c_df = bench[bench["Country"] == country] if "Country" in bench.columns else bench
            
            # Ranges: Safe (>= -3), Target (-3 to -15), Dream (< -15)
            safe = c_df[c_df["Score Gap %"] >= -3].sort_values("Score Gap %", ascending=False).head(3)
            target = c_df[(c_df["Score Gap %"] < -3) & (c_df["Score Gap %"] >= -15)].sort_values("Score Gap %", ascending=False).head(3)
            dream = c_df[c_df["Score Gap %"] < -15].sort_values("Score Gap %", ascending=False).head(3)

            if not safe.empty:
                st.markdown("**🟢 Safe**")
                for _, r in safe.iterrows():
                    st.markdown(f"<div class='uni-card' style='background-color:#28a745;'>{r['University']} ({round(r['Score Gap %'],1)}%)</div>", unsafe_allow_html=True)
            
            if not target.empty:
                st.markdown("**🟡 Target**")
                for _, r in target.iterrows():
                    st.markdown(f"<div class='uni-card' style='background-color:#ffc107; color:#333;'>{r['University']} ({round(r['Score Gap %'],1)}%)</div>", unsafe_allow_html=True)

            if not dream.empty:
                st.markdown("**🔴 Dream**")
                for _, r in dream.iterrows():
                    st.markdown(f"<div class='uni-card' style='background-color:#dc3545;'>{r['University']} ({round(r['Score Gap %'],1)}%)</div>", unsafe_allow_html=True)
            st.divider()

    # --- Strategic Framework Disclosure ---
    st.header("🌍 Global Admissions Framework")
    st.write("Universities evaluate your profile across 10 critical domains. Improving your 'Live Profile Score' directly impacts your placement in the categories above.")

    

    st.markdown("""
    1. **Academics (Q1):** The foundation of your application.
    2. **Rigor (Q2):** Difficulty of your high school subjects.
    3. **Testing (Q3):** SAT/ACT and Olympiad performance.
    4. **Competitions (Q4):** National and International rankings.
    5. **Projects (Q5):** Tangible evidence of your skills.
    6. **Leadership (Q6):** Ability to influence and scale impact.
    7. **Internships (Q7):** Real-world professional exposure.
    8. **Social Impact (Q8):** Service and community problem solving.
    9. **Communication (Q9):** Public speaking and personal branding.
    10. **Curiosity (Q10):** Independent learning and certifications.
    """)
