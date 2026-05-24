import streamlit as st
import pandas as pd
import joblib
import shap
import requests
import plotly.express as px
import matplotlib.pyplot as plt
import os

st.set_page_config(
    page_title="AI Fraud Intelligence System",
    page_icon="🛡️",
    layout="wide"
)

@st.cache_resource
def load_pipeline():

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    MODEL_PATH = os.path.join(BASE_DIR, "models", "xgboost_pipeline.pkl")

    return joblib.load(MODEL_PATH)

pipeline = load_pipeline()

preprocessor = pipeline.named_steps["preprocessing"]

xgb_model = pipeline.named_steps["model"]

explainer = shap.TreeExplainer(xgb_model)

feature_names = (preprocessor.get_feature_names_out())

st.sidebar.title("Fraud Intelligence Dashboard")

st.sidebar.info("Upload transaction data to detect fraudulent activity using XGBoost AI models.")

threshold = st.sidebar.slider(
    "Fraud Threshold",
    min_value=0.0,
    max_value=1.0,
    value=0.3,
    step=0.05
)

st.markdown(
    """
    <h1 style='text-align:center; color:#ff4b4b;'>
    🛡️ AI Fraud Intelligence System
    </h1>
    """,
    unsafe_allow_html=True
)

# st.success("Fraud Detection System Operational")

def color_risk_level(val):

    if val == "Critical":
        return (
            "background-color: #ff4b4b;"
            "color: white;"
            "font-weight: bold"
        )

    elif val == "High":
        return (
            "background-color: orange;"
            "color: black;"
            "font-weight: bold"
        )

    elif val == "Medium":
        return (
            "background-color: yellow;"
            "color: black;"
            "font-weight: bold"
        )

    else:
        return (
            "background-color: green;"
            "color: white;"
            "font-weight: bold"
        )

uploaded_file = st.file_uploader("Upload Transaction CSV", type=["csv"])

if uploaded_file is not None:

    with st.spinner("Analyzing transactions..."):

        data = pd.read_csv(uploaded_file)

        uploaded_file.seek(0)

        files = {

            "file": (uploaded_file.name, uploaded_file, "text/csv")
        }

        response = requests.post("http://api:8000/predict", files=files)

        if response.status_code != 200:

            st.error("FastAPI prediction failed.")

            st.stop()

        results = response.json()

        results_df = pd.DataFrame(results)

        data["Fraud_Probability"] = (results_df["Fraud_Probability"])

        data["Predicted_Fraud"] = (results_df["Predicted_Fraud"])

        data["Risk_Level"] = (results_df["Risk_Level"])

        data.to_csv(
            "prediction_logs.csv",
            mode="a",
            index=False,
            header=False
        )

    total_transactions = len(data)

    fraud_alerts = data["Predicted_Fraud"].sum()

    avg_risk = data["Fraud_Probability"].mean()

    critical_risk = (data["Risk_Level"] == "Critical").sum()

    st.info(f"Processed {total_transactions} transactions. Flagged {fraud_alerts} suspicious activities.")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Transactions", total_transactions)

    col2.metric("Fraud Alerts", fraud_alerts)

    col3.metric("Average Fraud Risk", f"{avg_risk:.2f}")

    col4.metric("Critical Risk", critical_risk)


    tab1, tab2, tab3 = st.tabs(["Overview", "Transactions", "Explainability"])


    with tab1:

        st.subheader("Risk Distribution")

        risk_counts = (data["Risk_Level"].value_counts().reset_index())

        risk_counts.columns = ["Risk_Level", "Count"]

        fig_pie = px.pie(
            risk_counts,
            names="Risk_Level",
            values="Count",
            title="Risk Distribution"
        )

        st.plotly_chart(fig_pie,  use_container_width=True)

        fig_hist = px.histogram(
            data,
            x="Fraud_Probability",
            nbins=30,
            title="Fraud Probability Distribution"
        )

        st.plotly_chart(fig_hist, use_container_width=True)

        st.subheader("Feature Importance")

        feature_names = (preprocessor.get_feature_names_out())

        feature_importance = pd.DataFrame({
            "Feature": feature_names,
            "Importance":
            xgb_model.feature_importances_
        })

        feature_importance = (
            feature_importance.sort_values(by="Importance", ascending=True).tail(15))

        fig_importance = px.bar(
            feature_importance,
            x="Importance",
            y="Feature",
            orientation="h",
            color="Importance",
            title="Top Important Features"
        )

        fig_importance.update_layout(
            yaxis_title="Feature",
            xaxis_title="Importance",
            height=500
        )

        st.plotly_chart(fig_importance,use_container_width=True)

    with tab2:

        st.subheader("Top Suspicious Transactions")

        top_risky = data.sort_values(by="Fraud_Probability", ascending=False).head(20)

        styled_df = top_risky.style.map(
            color_risk_level,
            subset=["Risk_Level"]
        )

    st.dataframe(
        styled_df,
        use_container_width=True
    )

    with tab3:

        st.subheader("Fraud Explanation")

        transformed_data = (preprocessor.transform(data))

        selected_index = st.selectbox("Select Transaction", data.index)

        selected_row = (transformed_data[selected_index])

        shap_values = (explainer.shap_values(selected_row))

        selected_dense = (selected_row.toarray()[0])

        shap_plot = shap.Explanation(
            values=shap_values[0],
            base_values=(explainer.expected_value),
            data=selected_dense,
            feature_names=feature_names
        )

        plt.figure()

        shap.plots.waterfall(shap_plot, show=False)

        fig = plt.gcf()

        st.pyplot(fig)

        plt.close()

    csv = data.to_csv(index=False)

    st.download_button(
        label="Download Predictions",
        data=csv,
        file_name="fraud_predictions.csv",
        mime="text/csv"
    )