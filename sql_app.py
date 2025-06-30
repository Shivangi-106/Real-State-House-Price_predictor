'''

import streamlit as st
import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from joblib import dump, load
import mysql.connector

# ------------------ DB CONFIG ------------------
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),         # 🟡 Use Render’s environment variables
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

MODEL_FILE = "model.joblib"

COLUMNS = ['CRIM', 'ZN', 'INDUS', 'CHAS', 'NOX', 'RM', 'AGE',
           'DIS', 'RAD', 'TAX', 'PTRATIO', 'B', 'LSTAT']

# ------------------ DB FUNCTIONS ------------------
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def fetch_data(table):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()
    return df

def insert_input_to_db(data_dict, table='data_copy'):
    conn = get_connection()
    cursor = conn.cursor()
    cols = ', '.join(data_dict.keys())
    vals = ', '.join(['%s'] * len(data_dict))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({vals})"
    cursor.execute(sql, tuple(data_dict.values()))
    conn.commit()
    cursor.close()
    conn.close()

def move_data_to_main():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO housing_data (CRIM, ZN, INDUS, CHAS, NOX, RM, AGE, DIS, RAD, TAX, PTRATIO, B, LSTAT, MEDV)
        SELECT CRIM, ZN, INDUS, CHAS, NOX, RM, AGE, DIS, RAD, TAX, PTRATIO, B, LSTAT, MEDV FROM data_copy
    """)
    cursor.execute("DELETE FROM data_copy")
    conn.commit()
    cursor.close()
    conn.close()

# ------------------ MODEL ------------------
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

# ------------------ LOAD MODEL ------------------
try:
    model = load(MODEL_FILE)
except:
    df_init = fetch_data('housing_data')
    model = train_and_save_model(df_init)

# ------------------ STREAMLIT UI ------------------
st.title("🏠 Real Estate Price Prediction")

st.markdown("""
Enter property details below. Follow the format carefully:

- **CRIM**: Crime in % (e.g., `2` for 2%)
- **ZN**: Residential zone in % (e.g., `25`)
- **INDUS**: Industry area in % (e.g., `15`)
- **CHAS**: 0 = No river bound, 1 = River bound
- **NOX**: Nitric oxide in % (e.g., `0.5`)
- **RM**: Number of rooms (e.g., `6.5`)
- **AGE**: Age of house (e.g., `50`)
- **DIS**: Distance to jobs in km (e.g., `4.2`)
- **RAD**: Highway access (e.g., `3`)
- **TAX**: Tax per $1000 (e.g., `18`)
- **PTRATIO**: Pupil-teacher ratio (e.g., `15.5`)
- **B**: Black population index
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
        st.error("❌ Please fill at least 11 out of 13 fields.")
    else:
        try:
            processed = {}
            for col in COLUMNS:
                val = user_input[col]
                if val == '':
                    processed[col] = np.nan
                else:
                    num = float(val)
                    if col in ['CRIM', 'ZN', 'INDUS', 'NOX', 'LSTAT', 'TAX']:
                        processed[col] = num / 100
                    elif col == 'CHAS':
                        processed[col] = int(num)
                    else:
                        processed[col] = num

            input_df = pd.DataFrame([processed])
            filled_input = input_df.fillna(fetch_data('housing_data')[COLUMNS].mean())
            prediction = model.predict(filled_input)[0]
            st.success(f"💵 Predicted house price: ${prediction * 1000:,.0f}")

            input_df['MEDV'] = round(prediction, 1)
            insert_input_to_db(input_df.iloc[0].to_dict(), table='data_copy')

            # Retrain model after every 10 entries
            copy_data = fetch_data('data_copy')
            if len(copy_data) >= 10:
                model = train_and_save_model(copy_data)
                move_data_to_main()

        except Exception as e:
            st.error(f"⚠️ Error: {e}")

'''