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
    "CRIM", "ZN", "INDUS", "CHAS", "NOX", "RM", "AGE",
    "DIS", "RAD", "TAX", "PTRATIO", "B", "LSTAT"
]

MODEL_FILE = "model.joblib"


# ================== DATA LOADER (NO CACHE ❗) ================== #
def load_sheet(sheet):
    df = pd.DataFrame(sheet.get_all_records())
    for col in COLUMNS + ["MEDV"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


housing_df = load_sheet(data_sheet)
data_copy_df = load_sheet(data_copy_sheet)


# ================== MODEL ================== #
def train_and_save_model(df):
    df = df.dropna(subset=["MEDV"])

    X = df[COLUMNS]
    y = df["MEDV"]

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("rf", RandomForestRegressor(
            n_estimators=200,
            random_state=42
        ))
    ])

    model.fit(X, y)
    dump(model, MODEL_FILE)
    return model


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
        user_input[col] = st.number_input(
            label=col,
            value=None,
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

        if val is None:
            processed[col] = np.nan
            empty_count += 1
        else:
            if col in ["CRIM", "ZN", "INDUS", "NOX", "LSTAT", "TAX"]:
                processed[col] = val / 100
            elif col == "CHAS":
                processed[col] = int(val)
            else:
                processed[col] = val

    if empty_count > 2:
        st.error("❌ Please fill at least 11 out of 13 fields.")
    else:
        input_df = pd.DataFrame([processed])
        input_df = input_df.fillna(housing_df[COLUMNS].mean())

        prediction = model.predict(input_df)[0]

        st.success(f"💵 Predicted house price: $ {prediction * 1000:,.0f}")

        # ------------------ SAVE TO SHEET ------------------ #
        save_df = pd.DataFrame([processed])
        save_df["MEDV"] = round(float(prediction), 1)

        row = [
            "" if pd.isna(x) else float(x)
            for x in save_df.iloc[0].tolist()
        ]

        data_copy_sheet.append_rows(
            [row],
            value_input_option="USER_ENTERED"
        )

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
