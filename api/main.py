from fastapi import FastAPI, UploadFile
import joblib
import pandas as pd
import os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(BASE_DIR, "models", "xgboost_pipeline.pkl")

pipeline = joblib.load(MODEL_PATH)

def assign_risk_level(prob):

    if prob >= 0.9:
        return "Critical"

    elif prob >= 0.7:
        return "High"

    elif prob >= 0.4:
        return "Medium"

    else:
        return "Low"

@app.get("/")

def home():

    return {
        "message":
        "Fraud Detection API Running"
    }

@app.post("/predict")

async def predict_fraud(file: UploadFile):

    data = pd.read_csv(file.file)

    fraud_prob = pipeline.predict_proba(data)[:, 1]

    data["Fraud_Probability"] = fraud_prob

    data["Predicted_Fraud"] = (data["Fraud_Probability"] >= 0.3).astype(int)

    data["Risk_Level"] = data["Fraud_Probability"].apply(assign_risk_level)

    results = data[["Fraud_Probability", "Predicted_Fraud", "Risk_Level"]]

    return results.to_dict(orient="records")

@app.get("/health")

def health_check():

    return {"status": "healthy"}