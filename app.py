import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import contextlib
from openai import OpenAI

client = OpenAI(api_key="")

st.set_page_config(page_title="AI Data Copilot", layout="wide")
st.title("AI Data Copilot — Interactive Dashboard Edition")

def run_code_for_dashboard(code, df):
    local_env = {
        "df": df,
        "pd": pd,
        "px": px,
        "go": go,
    }

    output_buffer = io.StringIO()

    with contextlib.redirect_stdout(output_buffer):
        try:
            exec(code, {}, local_env)
        except Exception as e:
            return {"error": str(e), "figure": None, "code": code}

    fig = None

    for v in local_env.values():
        if isinstance(v, go.Figure):
            fig = v
            break

    return {
        "output": output_buffer.getvalue(),
        "figure": fig,
        "code": code
    }

def ask_ai(messages, df):
    schema = str(df.dtypes.to_dict())
    sample = df.head(5).to_dict(orient="records")

    system_prompt = f"""
You are a Data Copilot.
Your ONLY job is to return VALID JSON. NOTHING ELSE.

STRICT RULES:
- Output MUST be ONLY valid JSON.
- NO natural language outside JSON.
- NO explanations, no greetings, no commentary.
- JSON must contain exactly these fields:
    {{"type": "chart", "code": "<python>", "description": "<text>"}}
- The `code` MUST:
    - contain ONLY Python (no markdown)
    - define a variable named `fig`
    - use Plotly Express ONLY (import px)
- NEVER wrap code in backticks.
- NEVER prefix JSON with text.

If you cannot produce the chart, return:
    {{"type": "error", "description": "<reason>"}}

Data Schema:
{schema}

Sample Rows:
{sample}
"""

    result = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "system", "content": system_prompt}] + messages,
        temperature=0
    )

    import json
    return json.loads(result.choices[0].message.content)

def generate_dashboard(df):
    st.write("### AI Advanced Insights")
    with st.spinner("Analyzing dataset for trends, anomalies, and patterns..."):
        insights = generate_insights(df)
    st.write(insights)
    st.subheader("Compact Interactive Dashboard")

    numeric_cols = df.select_dtypes(include=['float', 'int']).columns

    col1, col2 = st.columns(2)

    with col1:
        st.write("### Data Summary")
        st.dataframe(df.describe(include='all'), use_container_width=True)

    with col2:
        if len(numeric_cols) > 1:
            st.write("### Correlation Heatmap")
            fig = px.imshow(df[numeric_cols].corr(), text_auto=True, color_continuous_scale="RdBu")
            st.plotly_chart(fig, use_container_width=True)

    st.write("### Distributions")
    num_cols = list(numeric_cols[:4])

    if len(num_cols) == 0:
        return

    for i in range(0, len(num_cols), 2):
        c1, c2 = st.columns(2)

        with c1:
            if i < len(num_cols):
                fig1 = px.histogram(df, x=num_cols[i], nbins=30, marginal="box", color_discrete_sequence=["#4e79a7"])
                st.plotly_chart(fig1, use_container_width=True)

        with c2:
            if i + 1 < len(num_cols):
                fig2 = px.histogram(df, x=num_cols[i+1], nbins=30, marginal="box", color_discrete_sequence=["#59a14f"])
                st.plotly_chart(fig2, use_container_width=True)

if "df" not in st.session_state:
    st.session_state.df = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_code" not in st.session_state:
    st.session_state.last_code = None

uploaded_file = st.file_uploader("Upload a CSV, Excel, or JSON file", type=["csv", "xlsx", "json"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        st.session_state.df = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(".xlsx"):
        st.session_state.df = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith(".json"):
        st.session_state.df = pd.read_json(uploaded_file)

def generate_insights(df):
    prompt = f"""
You are a Senior Data Analyst Copilot.
Analyze this dataset deeply and return ADVANCED INSIGHTS.

Your analysis **must** include:

1. **Top Key Insights (bullet points)**
2. **Trends & Patterns**
3. **Anomalies / Outliers**
4. **Correlations & Drivers**
5. **Segmentation Insights** (if applicable)
6. **Potential Business Recommendations**
7. **Data Quality Issues** (missing values, skew, imbalance)

Must be returned as **clean markdown**, no JSON.

Use the sample rows and schema to infer meaningful insights:

Sample rows:
{df.head(5).to_dict(orient='records')}

Schema:
{df.dtypes.to_dict()}

Be concise but insightful.
Provide maximum value.
"""

    result = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return result.choices[0].message.content
    prompt = f"""
Analyze this dataset and describe:
- important trends
- anomalies or outliers
- correlations
- key drivers of variation
- anything a business user should know

Return a clear, human-readable explanation. Avoid code.

Sample rows:
{df.head(5).to_dict(orient='records')}

Schema:
{df.dtypes.to_dict()}
"""

    result = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return result.choices[0].message.content

if st.session_state.df is not None:
    df = st.session_state.df

    generate_dashboard(df)

    st.write("---")
    st.write("### Ask a question about the data:")

    user_query = st.text_input("e.g., 'Show total sales by region'")

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})

        ai_result = ask_ai(st.session_state.messages, df)

        if ai_result["type"] == "chart":
            run_result = run_code_for_dashboard(ai_result["code"], df)

            if "error" in run_result:
                st.error(f"Error running AI code: {run_result['error']}")
            else:
                if run_result["figure"]:
                    st.plotly_chart(run_result["figure"], use_container_width=True)

                st.write(ai_result["description"])
                st.session_state.last_code = ai_result["code"]

    st.write("---")
    if st.checkbox("Show Code for Last Query"):
        if st.session_state.last_code:
            st.code(st.session_state.last_code)
        else:
            st.info("No code generated yet.")
