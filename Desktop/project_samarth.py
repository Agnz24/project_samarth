import streamlit as st
import pandas as pd
import re

# ------------------------------------------------------
# Load Data Safely with automatic column detection
# ------------------------------------------------------
@st.cache_data
def load_data():
    crop_df = pd.read_csv("crop_production_example.csv")
    rainfall_df = pd.read_csv("rainfall_data_example.csv")

    # Lowercase and strip all column names
    crop_df.columns = crop_df.columns.str.lower().str.strip()
    rainfall_df.columns = rainfall_df.columns.str.lower().str.strip()

    # Automatically detect relevant columns
    def detect_column(df, keywords):
        for col in df.columns:
            for kw in keywords:
                if kw in col:
                    return col
        return None

    crop_state_col = detect_column(crop_df, ['state', 'region'])
    crop_year_col = detect_column(crop_df, ['year'])
    crop_crop_col = detect_column(crop_df, ['crop', 'crops'])
    crop_prod_col = detect_column(crop_df, ['production', 'prod'])
    crop_area_col = detect_column(crop_df, ['area', 'hectares'])
    
    rain_state_col = detect_column(rainfall_df, ['state', 'region'])
    rain_year_col = detect_column(rainfall_df, ['year'])
    rain_rain_col = detect_column(rainfall_df, ['rainfall', 'rain'])

    # Normalize values
    for col in [crop_state_col, crop_crop_col]:
        if col:
            crop_df[col] = crop_df[col].astype(str).str.strip().str.lower()
    if crop_year_col:
        crop_df[crop_year_col] = pd.to_numeric(crop_df[crop_year_col], errors='coerce').fillna(0).astype(int)
    for col in [crop_prod_col, crop_area_col]:
        if col:
            crop_df[col] = pd.to_numeric(crop_df[col], errors='coerce').fillna(0)

    if rain_state_col:
        rainfall_df[rain_state_col] = rainfall_df[rain_state_col].astype(str).str.strip().str.lower()
    if rain_year_col:
        rainfall_df[rain_year_col] = pd.to_numeric(rainfall_df[rain_year_col], errors='coerce').fillna(0).astype(int)
    if rain_rain_col:
        rainfall_df[rain_rain_col] = pd.to_numeric(rainfall_df[rain_rain_col], errors='coerce').fillna(0)

    # Save detected column names in dicts for later use
    crop_cols = {'state': crop_state_col, 'year': crop_year_col, 'crop': crop_crop_col,
                 'production': crop_prod_col, 'area': crop_area_col}
    rain_cols = {'state': rain_state_col, 'year': rain_year_col, 'rainfall': rain_rain_col}

    return crop_df, rainfall_df, crop_cols, rain_cols

crop_df, rainfall_df, crop_cols, rain_cols = load_data()

# ------------------------------------------------------
# Utility Functions
# ------------------------------------------------------
def normalize_text(text):
    if isinstance(text, str):
        return text.strip().lower()
    return str(text).strip().lower()

def extract_years(question):
    years = re.findall(r'\b(20\d{2})\b', question)
    return [int(y) for y in years]

def extract_top_n(question):
    match = re.search(r'top (\d+)', question)
    if match:
        return int(match.group(1))
    return None

# ------------------------------------------------------
# Main Question Answering Function
# ------------------------------------------------------
def answer_question(question):
    try:
        if not question or str(question).strip() == "":
            return "Please ask a question."

        q_lower = normalize_text(question)

        # List of crops and states
        crops = crop_df[crop_cols['crop']].unique().tolist()
        states = crop_df[crop_cols['state']].unique().tolist()

        # Detect mentioned crops and states in question
        mentioned_crops = [c for c in crops if c in q_lower]
        mentioned_states = [s for s in states if s in q_lower]
        if not mentioned_states:
            mentioned_states = states  # fallback to all states

        years = extract_years(q_lower)
        top_n = extract_top_n(q_lower)

        responses = []

        # -----------------------
        # Rainfall query
        # -----------------------
        if "rainfall" in q_lower:
            for state in mentioned_states:
                df = rainfall_df[rainfall_df[rain_cols['state']] == state]
                if years:
                    df = df[df[rain_cols['year']].isin(years)]
                if df.empty:
                    responses.append(f"No rainfall data found for {state.title()}.")
                    continue
                avg_rain = df[rain_cols['rainfall']].mean()
                responses.append(f"Average rainfall in {state.title()} for selected year(s) is {avg_rain:.2f} mm.")
            return " ".join(responses)

        # -----------------------
        # Crop metrics query
        # -----------------------
        if mentioned_crops:
            for crop in mentioned_crops:
                df_crop = crop_df[crop_df[crop_cols['crop']] == crop]
                df_crop = df_crop[df_crop[crop_cols['state']].isin(mentioned_states)]
                if years:
                    df_crop = df_crop[df_crop[crop_cols['year']].isin(years)]
                if df_crop.empty:
                    responses.append(f"No data found for {crop.title()}.")
                    continue
                avg_prod = df_crop[crop_cols['production']].mean() if crop_cols['production'] else 0
                avg_area = df_crop[crop_cols['area']].mean() if crop_cols['area'] else 0
                avg_yield = (avg_prod / avg_area) if avg_area != 0 else 0

                if "production" in q_lower:
                    responses.append(f"Average production of {crop.title()} is {avg_prod:.2f} tons.")
                elif "area" in q_lower:
                    responses.append(f"Average cultivation area of {crop.title()} is {avg_area:.2f} ha.")
                elif "yield" in q_lower:
                    responses.append(f"Average yield of {crop.title()} is {avg_yield:.2f} t/ha.")
                else:
                    responses.append(
                        f"For {crop.title()}, average production is {avg_prod:.2f} tons, "
                        f"area {avg_area:.2f} ha, yield {avg_yield:.2f} t/ha."
                    )
            return " ".join(responses)

        # -----------------------
        # Top-N crops query
        # -----------------------
        if top_n:
            for state in mentioned_states:
                df_state = crop_df[crop_df[crop_cols['state']] == state]
                if years:
                    df_state = df_state[df_state[crop_cols['year']].isin(years)]
                if df_state.empty:
                    responses.append(f"No crop data found for {state.title()} for selected year(s).")
                    continue
                top_crops = df_state.groupby(crop_cols['crop'])[crop_cols['production']].sum().sort_values(ascending=False).head(top_n)
                top_list = [f"{c.title()} ({p:.2f} tons)" for c, p in top_crops.items()]
                responses.append(f"Top {top_n} crops in {state.title()} for selected year(s): " + ", ".join(top_list))
            return " ".join(responses)

        # -----------------------
        # Compare crops across states
        # -----------------------
        compare_match = re.findall(r'compare\s+(\w+)\s+and\s+(\w+)', q_lower)
        if compare_match:
            c1, c2 = compare_match[0]
            c1, c2 = normalize_text(c1), normalize_text(c2)
            if c1 in crops and c2 in crops:
                df1 = crop_df[crop_df[crop_cols['crop']] == c1]
                df2 = crop_df[crop_df[crop_cols['crop']] == c2]
                if years:
                    df1 = df1[df1[crop_cols['year']].isin(years)]
                    df2 = df2[df2[crop_cols['year']].isin(years)]
                avg1 = df1[crop_cols['production']].mean()
                avg2 = df2[crop_cols['production']].mean()
                diff = abs(avg1 - avg2)
                responses.append(f"{c1.title()} has an average production of {avg1:.2f} tons, "
                                 f"{c2.title()} has {avg2:.2f} tons. Difference: {diff:.2f} tons.")
                return " ".join(responses)

        return "I'm not sure about that. Try asking about rainfall, crop yield, production, area, top crops, or comparisons."

    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ------------------------------------------------------
# Streamlit Interface
# ------------------------------------------------------
st.set_page_config(page_title="Project Samarth", page_icon="🌾", layout="centered")
st.title("🌾 Project Samarth — Smart Crop & Rainfall Assistant")

st.markdown("""
Ask me anything about Indian crops or rainfall patterns!  
Try questions like:
- *"What is the average rainfall in Kerala 2018?"*  
- *"What is the yield of rice in Maharashtra  2019"*  
- *"Top 2 crops in Kerala 2020"*  
- *"Compare the average annual rainfall in Assam and Bihar for the last 2 years."*
""")

question = st.text_input("💬 Type your question below:")
if st.button("Get Answer"):
    with st.spinner("Analyzing your data..."):
        st.success(answer_question(question))

# ------------------------------------------------------
# Expanders for Raw Data
# ------------------------------------------------------
with st.expander("📈 View Rainfall Data"):
    st.dataframe(rainfall_df.head(20))

with st.expander("🌿 View Crop Production Data"):
    st.dataframe(crop_df.head(20))
