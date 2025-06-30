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

# ------------------ GOOGLE SHEETS SETUP ------------------ #
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]

creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
#creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Sheet names
data_sheet = client.open("RealEstateData").worksheet("housing_data")
data_copy_sheet = client.open("RealEstateData").worksheet("data_copy")

# Column names
COLUMNS = ['CRIM', 'ZN', 'INDUS', 'CHAS', 'NOX', 'RM', 'AGE',
           'DIS', 'RAD', 'TAX', 'PTRATIO', 'B', 'LSTAT']

MODEL_FILE = "model.joblib"

# ------------------ CACHING DATA ------------------ #
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
    df_clean = df.dropna(subset=['MEDV'])
    X = df_clean[COLUMNS]
    y = df_clean['MEDV']
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('model', RandomForestRegressor())
    ])
    pipeline.fit(X, y)
    dump(pipeline, MODEL_FILE)
    return pipeline

if os.path.exists(MODEL_FILE):
    model = load(MODEL_FILE)
else:
    model = train_and_save_model(housing_df)

# ------------------ UI ------------------ #
st.title("\U0001F3E0 Real Estate Price Prediction")

st.markdown("""
Enter the property details below. Please follow the format guidelines:

- **CRIM**: Crime in % (e.g., `2` for 2%)
- **ZN**: Residential zone in % (e.g., `25`)
- **INDUS**: Industry area in % (e.g., `15`)
- **CHAS**: 0 = No river bound, 1 = River bound
- **NOX**: Nitric oxide concentration in % (e.g., `0.5`)
- **RM**: Number of rooms (e.g., `3`, `6.5`)
- **AGE**: Age of house (e.g., `50`)
- **DIS**: Distance to jobs in km (e.g., `4.2`)
- **RAD**: Highway access in km (e.g., `3`)
- **TAX**: Tax in % per $1000 (e.g., `18`)
- **PTRATIO**: Pupil-teacher ratio (e.g., `15.5`)
- **B**: Black population index (as-is)
- **LSTAT**: Lower status population % (e.g., `5.3`)
""")

user_input = {}
empty_count = 0

for col in COLUMNS:
    val = st.text_input(f"{col}:", key=col)
    if val.strip() == '':
        empty_count += 1
    user_input[col] = val.strip()

if st.button("Predict"):
    if empty_count > 2:
        st.error("\u274C Please fill at least 11 out of 13 fields.")
    else:
        try:
            processed_input = {}
            for col in COLUMNS:
                val = user_input[col]
                if val == '':
                    processed_input[col] = np.nan
                else:
                    num = float(val)
                    if col in ['CRIM', 'ZN', 'INDUS', 'NOX', 'LSTAT', 'TAX']:
                        processed_input[col] = num / 100
                    elif col == 'CHAS':
                        processed_input[col] = int(num)
                    else:
                        processed_input[col] = num

            input_df = pd.DataFrame([processed_input])
            input_filled = input_df.fillna(housing_df[COLUMNS].mean())
            prediction = model.predict(input_filled)[0]
            st.success(f"\U0001F4B5 Predicted house price: $ {prediction * 1000:,.0f}")

            # Save prediction
            input_df['MEDV'] = round(float(prediction), 1)

            # Append new row to Google Sheets
            new_row = input_df.iloc[0].tolist()
            clean_row = ["" if pd.isna(x) else float(x) if isinstance(x, (int, float, np.number)) else x for x in new_row]
            data_copy_sheet.append_rows([clean_row], value_input_option="USER_ENTERED")

            # Check for retrain
            updated_data_copy = pd.DataFrame(data_copy_sheet.get_all_records())
            for col in COLUMNS + ['MEDV']:
                if col in updated_data_copy.columns:
                    updated_data_copy[col] = pd.to_numeric(updated_data_copy[col], errors='coerce')

            if len(updated_data_copy) - len(housing_df) >= 10:
                valid_rows = updated_data_copy.dropna(subset=['MEDV'])
                model = train_and_save_model(valid_rows)
                data_sheet.clear()
                header = valid_rows.columns.tolist()
                rows = valid_rows.apply(lambda row: ["" if pd.isna(x) else float(x) if isinstance(x, (int, float, np.number)) else x for x in row.tolist()], axis=1).tolist()
                data_sheet.append_rows([header] + rows, value_input_option="USER_ENTERED")

        except Exception as e:
            st.error(f"\u26A0\uFE0F Error: {str(e)}")
