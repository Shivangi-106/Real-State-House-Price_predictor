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

# ------------------ PAGE CONFIG ------------------ #
st.set_page_config(
    page_title="Real Estate Price Prediction",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ------------------ GOOGLE SHEETS SETUP ------------------ #
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]

creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

data_sheet = client.open("RealEstateData").worksheet("housing_data")
data_copy_sheet = client.open("RealEstateData").worksheet("data_copy")

# ------------------ CONSTANTS ------------------ #
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
MODEL_COLUMNS_FILE = "model_columns.json"

# ------------------ DATA LOADER ------------------ #
@st.cache_data(ttl=60)
def get_data_from_sheet(_sheet):
    df = pd.DataFrame(_sheet.get_all_records())
    for col in COLUMNS + ['MEDV']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

housing_df = get_data_from_sheet(data_sheet)
data_copy_df = get_data_from_sheet(data_copy_sheet)

# ------------------ MODEL TRAINING ------------------ #
def train_and_save_model(df):
    df = df.dropna(subset=['MEDV'])

    # Keep only columns present in the sheet
    valid_cols = [c for c in COLUMNS if c in df.columns]

    # Convert all columns to numeric
    X = df[valid_cols].apply(pd.to_numeric, errors='coerce')

    # Drop columns with all NaNs
    X = X.dropna(axis=1, how='all')
    valid_cols = X.columns.tolist()  # update valid columns

    y = df['MEDV'].apply(pd.to_numeric, errors='coerce')

    # Drop rows where target is NaN
    X = X.loc[y.notna()]
    y = y.loc[y.notna()]

    # Train pipeline
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('model', RandomForestRegressor(n_estimators=200, random_state=42))
    ])
    pipeline.fit(X, y)

    # Save model and columns
    dump(pipeline, MODEL_FILE)
    with open(MODEL_COLUMNS_FILE, "w") as f:
        json.dump(valid_cols, f)

    return pipeline

# Load existing model or train a new one
if os.path.exists(MODEL_FILE) and os.path.exists(MODEL_COLUMNS_FILE):
    model = load(MODEL_FILE)
    trained_cols = json.load(open(MODEL_COLUMNS_FILE))
else:
    model = train_and_save_model(housing_df)
    trained_cols = json.load(open(MODEL_COLUMNS_FILE))

# ------------------ UI ------------------ #
st.title("🏠 Real Estate Price Prediction")
st.write("Enter property details below. Fill at least **11 out of 13** fields.")

# ------------------ FORM ------------------ #
with st.form("prediction_form"):
    user_input = {}
    for col in COLUMNS:
        user_input[col] = st.number_input(
            label=col,
            value=None,
            step=0.01,
            format="%.2f"
        )
    submit = st.form_submit_button("Predict")

# ------------------ PREDICTION ------------------ #
if submit:
    filled = {}
    empty = 0

    for col in COLUMNS:
        val = user_input[col]
        if val is None:
            filled[col] = np.nan
            empty += 1
        else:
            # Original scaling/int logic
            if col in ['CRIM','ZN','INDUS','NOX','LSTAT','TAX']:
                filled[col] = float(val) / 100
            elif col == 'CHAS':
                filled[col] = int(val)
            else:
                filled[col] = float(val)

    if empty > 2:
        st.error("❌ Please fill at least 11 out of 13 fields.")
    else:
        input_df = pd.DataFrame([filled])

        # ------------------ ALIGN INPUT WITH TRAINED MODEL ------------------ #
        input_filled = input_df.reindex(columns=trained_cols)
        input_filled = input_filled.fillna(housing_df[trained_cols].mean())

        prediction = model.predict(input_filled)[0]
        st.success(f"💵 Predicted house price: $ {prediction * 1000:,.0f}")

        # ------------------ SAVE TO GOOGLE SHEET ------------------ #
        input_df['MEDV'] = round(float(prediction), 1)
        row = input_df.iloc[0].tolist()
        clean_row = ["" if pd.isna(x) else float(x) for x in row]
        data_copy_sheet.append_rows([clean_row], value_input_option="USER_ENTERED")

        # ------------------ RETRAIN CHECK ------------------ #
        updated = pd.DataFrame(data_copy_sheet.get_all_records())
        updated_cols = [c for c in COLUMNS if c in updated.columns] + ['MEDV']
        updated[updated_cols] = updated[updated_cols].apply(pd.to_numeric, errors='coerce')

        if len(updated) - len(housing_df) >= 10:
            model = train_and_save_model(updated.dropna(subset=['MEDV']))
            data_sheet.clear()
            data_sheet.append_rows(
                [updated.columns.tolist()] + updated.fillna("").values.tolist(),
                value_input_option="USER_ENTERED"
            )
