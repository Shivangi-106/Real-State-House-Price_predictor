import streamlit as st
import pandas as pd
import numpy as np
import json
import os

from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from joblib import dump, load

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ================== PAGE CONFIG ================== #
st.set_page_config(
    page_title="Real Estate Price Prediction",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ================== GOOGLE SHEETS AUTH ================== #
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]

creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)

data_sheet = client.open("RealEstateData").worksheet("housing_data")
data_copy_sheet = client.open("RealEstateData").worksheet("data_copy")

# ================== CONSTANTS ================== #
COLUMNS = [
    "Crime rate in the town",
    "Percentage of land for large residential plots(higher values indicate premium housing areas)",
    "Share of land used for industrial purposes",
    "Is area near the Charles River (1 = yes, 0 = no)", 
    "Level of air pollution in the area",
    "Average number of rooms per house", 
    "Percentage of houses built before 1940",
    "Distance from major employment centers", 
    "Accessibility to highways", 
    "Property tax rate in the town", 
    "Student-to-teacher ratio in schools of area", 
    "Numeric value related to the town’s population", 
    "Percentage of lower-income population"
]

MODEL_FILE = "model.joblib"

# ================== DATA LOADER ================== #
def load_sheet(sheet):
    df = pd.DataFrame(sheet.get_all_records())
    # Ensure all COLUMNS exist
    for col in COLUMNS + ["MEDV"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

housing_df = load_sheet(data_sheet)
data_copy_df = load_sheet(data_copy_sheet)

# ================== MODEL ================== #
def train_and_save_model(df):
    df = df.dropna(subset=["MEDV"])
    # Only use columns present in df
    valid_cols = [c for c in COLUMNS if c in df.columns]
    X = df[valid_cols]
    y = df["MEDV"]

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("rf", RandomForestRegressor(n_estimators=200, random_state=42))
    ])
    model.fit(X, y)
    dump(model, MODEL_FILE)
    return model

# Load or train model
if os.path.exists(MODEL_FILE):
    model = load(MODEL_FILE)
else:
    model = train_and_save_model(housing_df)

# ================== UI ================== #
st.title("🏠 Real Estate Price Prediction")
st.write("Enter property details below. Fill at least **11 out of 13** fields.")

# ================== FORM ================== #
with st.form("prediction_form"):
    user_input = {}

    for col in COLUMNS:
        # All inputs as float to avoid mixed types
        user_input[col] = st.number_input(
            label=col,
            value=0.0,
            step=0.01,
            format="%.2f"
        )

    submitted = st.form_submit_button("Predict")

# ================== PREDICTION ================== #
if submitted:
    processed = {}
    empty_count = 0

    for col in COLUMNS:
        val = user_input[col]
        if val is None or val == 0.0:
            processed[col] = np.nan
            empty_count += 1
        else:
            processed[col] = float(val)

    if empty_count > 2:
        st.error("❌ Please fill at least 11 out of 13 fields.")
    else:
        # Use only columns present in housing_df to avoid KeyError
        valid_cols = [c for c in COLUMNS if c in housing_df.columns]
        input_df = pd.DataFrame([processed])[valid_cols]

        # Fill missing values with mean
        means = housing_df[valid_cols].mean()
        input_df = input_df.fillna(means)

        prediction = model.predict(input_df)[0]
        st.success(f"💵 Predicted house price: $ {prediction * 1000:,.0f}")

        # ------------------ SAVE TO SHEET ------------------ #
        save_df = pd.DataFrame([processed])
        save_df["MEDV"] = round(float(prediction), 1)
        row = ["" if pd.isna(x) else float(x) for x in save_df.iloc[0].tolist()]
        data_copy_sheet.append_rows([row], value_input_option="USER_ENTERED")

        # ------------------ RETRAIN CHECK ------------------ #
        updated_df = load_sheet(data_copy_sheet)
        if len(updated_df) - len(housing_df) >= 10:
            model = train_and_save_model(updated_df)
            data_sheet.clear()
            data_sheet.append_rows(
                [updated_df.columns.tolist()] +
                updated_df.fillna("").values.tolist(),
                value_input_option="USER_ENTERED"
            )
