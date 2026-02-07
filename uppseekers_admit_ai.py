import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

QUESTION_COLUMNS = [f"Q{i}" for i in range(1, 11)]

# Country calibration: multiplier >1 means the factor is more important in that market.
COUNTRY_WEIGHT_PROFILES = {
    "USA": {"Q1": 1.10, "Q5": 1.15, "Q8": 1.10, "Q9": 1.10, "Q10": 1.05},
    "UK": {"Q1": 1.35, "Q2": 1.10, "Q3": 1.05, "Q5": 0.75, "Q8": 0.70, "Q9": 0.75, "Q10": 0.75},
    "Canada": {"Q1": 1.20, "Q5": 0.95, "Q8": 1.00, "Q9": 1.05, "Q10": 1.05},
    "Singapore": {"Q1": 1.30, "Q2": 1.15, "Q3": 1.05, "Q5": 0.80, "Q8": 0.85, "Q9": 0.90, "Q10": 0.90},
    "Australia": {"Q1": 1.20, "Q5": 0.90, "Q8": 0.95, "Q9": 1.00, "Q10": 1.00},
    "Europe": {"Q1": 1.25, "Q2": 1.10, "Q3": 1.05, "Q5": 0.90, "Q8": 0.95, "Q9": 0.95, "Q10": 0.95}
}

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
# 2. DATA LOADING
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


def get_country_question_weights(country):
    weights = {q_col: 1.0 for q_col in QUESTION_COLUMNS}
    weights.update(COUNTRY_WEIGHT_PROFILES.get(country, {}))
    return weights


def calculate_weighted_student_score(responses, q_df, country):
    """Returns country-calibrated profile score on a 0-100 scale."""
    weights = get_country_question_weights(country)
    response_map = {int(q_id): score for _, _, score, q_id in responses}
    weighted_earned, weighted_max = 0.0, 0.0

    for i in range(1, 11):
        q_col = f"Q{i}"
        weight = weights[q_col]
        row = q_df[q_df["question_id"] == i]
        if row.empty:
            continue
        max_score = max([row.iloc[0].get(f"score_{opt}", 0) for opt in "ABCDE" if pd.notna(row.iloc[0].get(f"score_{opt}"))], default=0)
        earned = response_map.get(i, 0)
        weighted_earned += earned * weight
        weighted_max += max_score * weight

    if weighted_max == 0:
        return 0.0
    return (weighted_earned / weighted_max) * 100


def apply_country_benchmark_weighting(bench_df, student_total, country):
    """Apply country-specific weighting to both benchmark rows and student score."""
    weighted_df = bench_df.copy()
    weights = get_country_question_weights(country)

    weighted_df["Weighted Benchmark Score"] = 0.0
    for q_col in QUESTION_COLUMNS:
        if q_col in weighted_df.columns:
            weighted_df["Weighted Benchmark Score"] += weighted_df[q_col] * weights[q_col]

    benchmark_total = weighted_df[QUESTION_COLUMNS].fillna(0).sum(axis=1).mean() if set(QUESTION_COLUMNS).issubset(weighted_df.columns) else weighted_df["Total Benchmark Score"].mean()
    weighted_total = weighted_df["Weighted Benchmark Score"].mean() if not weighted_df.empty else student_total
    student_weighted_total = student_total * (weighted_total / benchmark_total) if benchmark_total else student_total

    weighted_df["Gap %"] = ((student_weighted_total - weighted_df["Weighted Benchmark Score"]) / weighted_df["Weighted Benchmark Score"]) * 100
    weighted_df["Total Benchmark Score"] = weighted_df["Weighted Benchmark Score"]
    return weighted_df, student_weighted_total

# ─────────────────────────────────────────────
# 3. PDF GENERATOR (STRATEGIC SORTING)
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

    elements.append(Paragraph("Strategic University Roadmap (9-List Strategy)", styles['Heading2']))
    
    for country in state.countries:
        elements.append(Paragraph(f"Regional Focus: {country}", styles['Heading3']))
        c_df = tuned_bench[tuned_bench["Country"].str.strip().str.lower() == country.strip().lower()] if "Country" in tuned_bench.columns else tuned_bench
        
        # DEFINING CATEGORIES WITH SORTING
        # Safe to Target: Highest Benchmark to Lowest
        safe_df = c_df[c_df["Gap %"] >= -3].sort_values("Total Benchmark Score", ascending=False)
        
        # Needs Strengthening: Lowest Benchmark to Highest
        needs_df = c_df[(c_df["Gap %"] < -3) & (c_df["Gap %"] >= -15)].sort_values("Total Benchmark Score", ascending=True)
        
        # Significant Gaps: Lowest Benchmark to Highest
        gaps_df = c_df[c_df["Gap %"] < -15].sort_values("Total Benchmark Score", ascending=True)

        buckets = [
            ("Safe to Target", safe_df, colors.darkgreen),
            ("Needs Strengthening", needs_df, colors.orange),
            ("Significant Gaps", gaps_df, colors.red)
        ]

        for title, df_cat, color in buckets:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            if not df_cat.empty:
                data = [["University", "Target Score", "Gap %"]]
                for _, r in df_cat.head(10).iterrows():
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
        pref_countries = st.multiselect("Select Target Countries", country_list, max_selections=3)
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
            bench_raw = pd.read_excel("Benchmarking_USA (3) (2).xlsx", sheet_name=b_sheet)
            st.session_state.update({"current_total": current_score, "current_responses": current_responses, "bench_raw": bench_raw, "page": 'tuner'})
            st.rerun()

    with col_right:
        st.markdown(f"<div class='score-box'><h3>Current Score</h3><h1>{round(current_score, 1)}</h1></div>", unsafe_allow_html=True)
        st.markdown("#### 🌍 Country-Calibrated Score Preview")
        for country in st.session_state.countries:
            calibrated = calculate_weighted_student_score(current_responses, q_df, country)
            st.metric(f"{country} Fit Score", round(calibrated, 1))

        st.info("Profiles are benchmarked across 10 domains, then calibrated by country-specific admission behavior.")

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
        
        m1, m2 = st.columns(2)
        m1.metric("Current Raw Score", round(st.session_state.current_total, 1))
        m2.metric("Strategic Raw Score", round(tuned_score, 1), delta=f"+{round(tuned_score - st.session_state.current_total, 1)}")

        st.divider()
        weighted_plan_frames = []

        for country in st.session_state.countries:
            country_bench = st.session_state.bench_raw[st.session_state.bench_raw["Country"].str.strip().str.lower() == country.strip().lower()] if "Country" in st.session_state.bench_raw.columns else st.session_state.bench_raw
            curr_country, curr_weighted = apply_country_benchmark_weighting(country_bench, st.session_state.current_total, country)
            plan_country, plan_weighted = apply_country_benchmark_weighting(country_bench, tuned_score, country)
            weighted_plan_frames.append(plan_country)

            st.markdown(f"#### 🚩 {country} University Counts")
            x1, x2 = st.columns(2)
            x1.metric(f"{country} Current Fit Score", round(curr_weighted, 1))
            x2.metric(f"{country} Strategic Fit Score", round(plan_weighted, 1), delta=f"+{round(plan_weighted - curr_weighted, 1)}")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"<p class='comparison-label'>Safe to Target</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='comparison-val'>{len(curr_country[curr_country['Gap %'] >= -3])} → {len(plan_country[plan_country['Gap %'] >= -3])}</p>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<p class='comparison-label'>Needs Strengthening</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='comparison-val'>{len(curr_country[(curr_country['Gap %'] < -3) & (curr_country['Gap %'] >= -15)])} → {len(plan_country[(plan_country['Gap %'] < -3) & (plan_country['Gap %'] >= -15)])}</p>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<p class='comparison-label'>Significant Gaps</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='comparison-val'>{len(curr_country[curr_country['Gap %'] < -15])} → {len(plan_country[plan_country['Gap %'] < -15])}</p>", unsafe_allow_html=True)
            st.divider()

        plan_b = pd.concat(weighted_plan_frames, ignore_index=True) if weighted_plan_frames else st.session_state.bench_raw.copy()

    st.subheader("📥 Secure Report Authorization")
    c_name = st.text_input("Counsellor Name")
    c_code = st.text_input("Access Pin", type="password")
    if st.button("Download Comparison PDF"):
        if c_code == "304":
            pdf = generate_comparison_pdf(st.session_state, tuned_score, c_name, plan_b)
            st.download_button("Download Comparative Report", data=pdf, file_name=f"{st.session_state.name}_Report.pdf")
